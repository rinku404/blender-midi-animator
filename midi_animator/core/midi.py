"""Standard MIDI File parser (format 0/1, PPQ and SMPTE timing, tempo maps, running status).

Times are in seconds. Controller streams are keyed by (track, channel, kind, number), where
kind is "CC" (number = controller), "AT" (channel aftertouch) or "PAT" (poly aftertouch).
"""

import bisect
import struct
from collections import defaultdict


class MidiNote:
    __slots__ = ("track", "track_name", "channel", "pitch", "velocity", "start", "end")

    def __init__(self, track, track_name, channel, pitch, velocity, start, end):
        self.track = track
        self.track_name = track_name
        self.channel = channel      # 0-15
        self.pitch = pitch
        self.velocity = velocity
        self.start = start          # seconds
        self.end = end              # seconds

    @property
    def duration(self):
        return max(0.0, self.end - self.start)


class MidiData:
    """Parsed file. controllers: {(track, channel, kind, number): [(sec, value), ...]}
    where kind is "CC" (number = controller), "AT" (channel aftertouch) or "PAT" (poly aftertouch)."""

    def __init__(self, notes, tracks, controllers):
        self.notes = notes
        self.tracks = tracks
        self.controllers = controllers
        ends = [n.end for n in notes] + [ev[-1][0] for ev in controllers.values() if ev]
        self.length = max(ends, default=0.0)

    # -- queries -----------------------------------------------------------
    def notes_for(self, track=-1, channel=0):
        """Notes of one performer. track -1 = any; channel 1-16, 0 = any."""
        return [n for n in self.notes if matches(n.track, n.channel, track, channel)]

    def controller_events(self, kind, number=0, track=-1, channel=0):
        """All (sec, value) events of one controller for the performer, merged and sorted."""
        ev = []
        for (t, ch, k, num), values in self.controllers.items():
            if k == kind and num == number and matches(t, ch, track, channel):
                ev.extend(values)
        ev.sort(key=lambda e: e[0])
        return ev

    def has_controller(self, kind, number=0, track=-1, channel=0, min_events=4):
        return len(self.controller_events(kind, number, track, channel)) >= min_events

    def controllers_summary(self, track=-1, channel=0):
        """[(kind, number, event_count)] for the performer, most events first."""
        counts = defaultdict(int)
        for (t, ch, k, num), values in self.controllers.items():
            if matches(t, ch, track, channel):
                counts[(k, num)] += len(values)
        return sorted(((k, n, c) for (k, n), c in counts.items()), key=lambda x: -x[2])


def matches(note_track, note_channel, track, channel):
    """note_channel is 0-15; channel filter is 1-16 (0 = any); track filter -1 = any."""
    return (track < 0 or note_track == track) and (channel <= 0 or note_channel == channel - 1)


def monophonic(notes):
    """Copy of the notes sorted by start where each note ends no later than the next starts
    (a wind player can only sound one note). Simultaneous starts keep the highest pitch."""
    ordered = sorted(notes, key=lambda n: (n.start, -n.pitch))
    out = []
    for n in ordered:
        if out and abs(out[-1].start - n.start) < 1e-6:
            continue
        out.append(MidiNote(n.track, n.track_name, n.channel, n.pitch, n.velocity, n.start, n.end))
    for a, b in zip(out, out[1:]):
        if a.end > b.start:
            a.end = b.start
    return out


def controller_label(kind, number=0):
    return {"CC": f"CC{number}", "AT": "Channel aftertouch", "PAT": "Poly aftertouch"}.get(kind, kind)


def _read_vlq(data, pos):
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not b & 0x80:
            return value, pos


def parse_midi(path):
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] != b"MThd":
        raise ValueError("Not a Standard MIDI File (missing MThd header)")
    hlen = struct.unpack(">I", data[4:8])[0]
    _fmt, ntracks, division = struct.unpack(">HHh", data[8:14])
    pos = 8 + hlen

    raw_tracks = []      # per track: list of (tick, kind, channel, a, b)
    tempo_events = []    # (tick, microseconds per quarter)
    track_names = []

    for t in range(ntracks):
        while pos + 8 <= len(data) and data[pos:pos + 4] != b"MTrk":
            pos += 8 + struct.unpack(">I", data[pos + 4:pos + 8])[0]
        if pos + 8 > len(data):
            break
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        pos += 8
        end = min(pos + length, len(data))
        tick = 0
        status = 0
        events = []
        name = f"Track {t}"

        while pos < end:
            delta, pos = _read_vlq(data, pos)
            tick += delta
            b = data[pos]
            if b & 0x80:
                pos += 1
                if b < 0xF0:
                    status = b
            else:
                b = status  # running status

            if b == 0xFF:
                mtype = data[pos]
                mlen, pos = _read_vlq(data, pos + 1)
                payload = data[pos:pos + mlen]
                pos += mlen
                if mtype == 0x51 and mlen == 3:
                    tempo_events.append((tick, int.from_bytes(payload, "big")))
                elif mtype == 0x03:
                    name = payload.decode("latin-1", "replace").strip() or name
                elif mtype == 0x2F:
                    break
            elif b in (0xF0, 0xF7):
                slen, pos = _read_vlq(data, pos)
                pos += slen
            else:
                kind = b & 0xF0
                ch = b & 0x0F
                if kind in (0xC0, 0xD0):
                    d1 = data[pos]
                    pos += 1
                    if kind == 0xD0:
                        events.append((tick, "AT", ch, 0, d1))
                elif kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    d1, d2 = data[pos], data[pos + 1]
                    pos += 2
                    if kind == 0x90 and d2 > 0:
                        events.append((tick, "on", ch, d1, d2))
                    elif kind == 0x80 or kind == 0x90:
                        events.append((tick, "off", ch, d1, 0))
                    elif kind == 0xB0:
                        events.append((tick, "CC", ch, d1, d2))
                    elif kind == 0xA0:
                        events.append((tick, "PAT", ch, 0, d2))
                else:
                    raise ValueError(f"Bad MIDI status byte 0x{b:02X} in track {t}")
        pos = end
        raw_tracks.append(events)
        track_names.append(name)

    # Tick -> seconds
    if division < 0:  # SMPTE
        fps = -(division >> 8)
        fps = 29.97 if fps == 29 else fps
        tpf = division & 0xFF

        def to_sec(tk):
            return tk / (fps * tpf)
    else:
        ppq = division
        tempo_events.sort(key=lambda e: e[0])
        seg_ticks, segs = [], []
        cur_tick, cur_sec, cur_tempo = 0, 0.0, 500000
        seg_ticks.append(0)
        segs.append((0, 0.0, 500000))
        for tk, tempo in tempo_events:
            cur_sec += (tk - cur_tick) * cur_tempo / (ppq * 1e6)
            cur_tick, cur_tempo = tk, tempo
            if seg_ticks[-1] == tk:
                segs[-1] = (tk, cur_sec, tempo)
            else:
                seg_ticks.append(tk)
                segs.append((tk, cur_sec, tempo))

        def to_sec(tk):
            s_tick, s_sec, tempo = segs[bisect.bisect_right(seg_ticks, tk) - 1]
            return s_sec + (tk - s_tick) * tempo / (ppq * 1e6)

    notes = []
    controllers = defaultdict(list)
    for ti, events in enumerate(raw_tracks):
        open_notes = defaultdict(list)
        for tick, kind, ch, a, b in events:
            if kind == "on":
                open_notes[(ch, a)].append((tick, b))
            elif kind == "off":
                if open_notes[(ch, a)]:
                    on_tick, on_vel = open_notes[(ch, a)].pop(0)
                    notes.append(MidiNote(ti, track_names[ti], ch, a, on_vel,
                                          to_sec(on_tick), to_sec(tick)))
            else:
                number = a if kind == "CC" else 0
                controllers[(ti, ch, kind, number)].append((to_sec(tick), b))
        for (ch, pitch), pending in open_notes.items():
            for on_tick, on_vel in pending:
                s = to_sec(on_tick)
                notes.append(MidiNote(ti, track_names[ti], ch, pitch, on_vel, s, s + 0.1))

    notes.sort(key=lambda n: (n.start, n.track, n.pitch))
    return MidiData(notes, track_names, dict(controllers))
