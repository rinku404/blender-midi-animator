import os
import struct

import pytest

from conftest import EXAMPLES
from midi_animator.core import midi as M
from midi_animator.core.notes import note_name, parse_note_name


def test_note_names():
    assert note_name(60) == "C4"
    assert note_name(61, flats=True) == "Db4"
    assert note_name(62, solfege=True) == "Ré4"
    assert note_name(70, flats=True, solfege=True, octave=False) == "Sib"
    assert parse_note_name("Bb3") == 58
    assert parse_note_name("C#5") == 73
    with pytest.raises(ValueError):
        parse_note_name("H2")


def test_aerophone_sample():
    m = M.parse_midi(os.path.join(EXAMPLES, "aerophone_sample.mid"))
    assert len(m.notes) == 14
    assert [note_name(n.pitch) for n in m.notes[:3]] == ["D4", "E4", "F#4"]
    # 100 BPM: one beat = 0.6 s
    assert m.notes[1].start == pytest.approx(0.6)
    assert m.has_controller("CC", 2)
    assert not m.has_controller("CC", 11)
    assert m.controllers_summary()[0][:2] == ("CC", 2)


def _write(path, events, ppq=480, tempo=None):
    """Tiny single-track SMF writer for edge cases. events: [(tick, bytes)]."""
    def vlq(n):
        b = [n & 0x7F]
        n >>= 7
        while n:
            b.append((n & 0x7F) | 0x80)
            n >>= 7
        return bytes(reversed(b))
    body, last = b"", 0
    if tempo:
        body += vlq(0) + b"\xff\x51\x03" + tempo.to_bytes(3, "big")
    for t, b in sorted(events, key=lambda e: e[0]):
        body += vlq(t - last) + b
        last = t
    body += vlq(0) + b"\xff\x2f\x00"
    data = (b"MThd" + struct.pack(">IHHH", 6, 0, 1, ppq)
            + b"MTrk" + struct.pack(">I", len(body)) + body)
    path.write_bytes(data)


def test_running_status_and_note_on_zero(tmp_path):
    p = tmp_path / "rs.mid"
    # 0x90 then running status; velocity 0 note-on = note-off
    _write(p, [(0, b"\x90\x3c\x40"), (480, b"\x3c\x00"), (480, b"\x3e\x50"), (960, b"\x3e\x00")])
    m = M.parse_midi(str(p))
    assert [(n.pitch, round(n.start, 3), round(n.end, 3)) for n in m.notes] == [(60, 0.0, 0.5), (62, 0.5, 1.0)]


def test_tempo_change(tmp_path):
    p = tmp_path / "tempo.mid"
    _write(p, [(0, b"\x90\x3c\x40"), (480, b"\x80\x3c\x00"),
               (480, b"\xff\x51\x03" + (1000000).to_bytes(3, "big")),
               (480, b"\x90\x3e\x40"), (960, b"\x80\x3e\x00")], tempo=500000)
    m = M.parse_midi(str(p))
    assert m.notes[1].start == pytest.approx(0.5)
    assert m.notes[1].end == pytest.approx(1.5)   # 1 beat at 60 BPM


def test_not_midi(tmp_path):
    p = tmp_path / "x.mid"
    p.write_bytes(b"hello")
    with pytest.raises(ValueError):
        M.parse_midi(str(p))


def test_monophonic_trims_overlaps():
    a = M.MidiNote(0, "", 0, 60, 90, 0.0, 1.0)
    b = M.MidiNote(0, "", 0, 62, 90, 0.5, 1.5)
    c = M.MidiNote(0, "", 0, 55, 90, 0.5, 1.5)   # same start as b, lower: dropped
    mono = M.monophonic([b, a, c])
    assert [(n.pitch, n.end) for n in mono] == [(60, 0.5), (62, 1.5)]
    assert a.end == 1.0   # originals untouched


def test_performer_filter():
    n0 = M.MidiNote(0, "", 0, 60, 90, 0.0, 1.0)
    n1 = M.MidiNote(1, "", 3, 62, 90, 0.0, 1.0)
    m = M.MidiData([n0, n1], ["a", "b"], {(1, 3, "CC", 2): [(0.0, 10), (0.1, 20)]})
    assert m.notes_for(track=1) == [n1]
    assert m.notes_for(channel=4) == [n1]
    assert m.notes_for(channel=1) == [n0]
    assert m.controller_events("CC", 2, track=0) == []
    assert len(m.controller_events("CC", 2, channel=4)) == 2
