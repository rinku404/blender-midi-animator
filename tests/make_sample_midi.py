"""Write the example MIDI files used by the tests and the guide.

  python tests/make_sample_midi.py
"""
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "examples")
PPQ = 480


def vlq(n):
    b = [n & 0x7F]
    n >>= 7
    while n:
        b.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(b))


def track(events):
    events.sort(key=lambda e: e[0])
    out, last = b"", 0
    for t, b in events:
        out += vlq(t - last) + b
        last = t
    out += vlq(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(out)) + out


def write(path, tracks):
    data = b"MThd" + struct.pack(">IHHH", 6, 1, len(tracks), PPQ) + b"".join(track(t) for t in tracks)
    with open(path, "wb") as f:
        f.write(data)


def aerophone():
    """Monophonic wind phrase at 100 BPM on channel 1 with CC2 breath, like an Aerophone recording:
    legato phrase over the middle octave, an octave-key phrase, a >0.5 s rest, low notes, a palm key."""
    tempo = [(0, b"\xff\x03\x05Tempo"), (0, b"\xff\x51\x03" + (600000).to_bytes(3, "big"))]
    ev = [(0, b"\xff\x03\x09Aerophone")]
    q = PPQ
    phrase1 = [(62, 1), (64, 1), (66, 1), (67, 1), (69, 1), (71, 1), (73, 1), (74, 2)]  # D4..D5
    phrase2 = [(76, 1), (79, 1), (81, 2)]                                                 # E5 G5 A5 (octave key)
    phrase3 = [(60, 1), (58, 1), (86, 2)]                                                 # low C4, low Bb3, palm D6
    t = 0
    for phrase in (phrase1, phrase2, phrase3):
        start = t
        for pitch, beats in phrase:
            dur = beats * q
            ev.append((t, bytes([0x90, pitch, 90])))
            ev.append((t + dur, bytes([0x80, pitch, 0])))
            t += dur
        # breath: swell up and down across the phrase, sent every 1/32 note
        length = t - start
        step = q // 8
        for k in range(0, length + step, step):
            x = k / length
            v = int(20 + 100 * (1 - abs(2 * x - 1) ** 2)) if x <= 1 else 0
            ev.append((start + k, bytes([0xB0, 2, max(0, min(127, v))])))
        ev.append((t + step, bytes([0xB0, 2, 0])))
        t += 2 * q  # 1.2 s rest at 100 BPM
    write(os.path.join(OUT, "aerophone_sample.mid"), [tempo, ev])


def drums_piano():
    t0 = [(0, b"\xff\x03\x05Tempo"), (0, b"\xff\x51\x03" + (500000).to_bytes(3, "big")),
          (PPQ * 8, b"\xff\x51\x03" + (600000).to_bytes(3, "big"))]
    drums = [(0, b"\xff\x03\x05Drums")]
    for beat in range(16):
        t = beat * PPQ
        p = 36 if beat % 2 == 0 else 38
        drums += [(t, bytes([0x99, p, 100 if p == 36 else 80])), (t + 120, bytes([0x89, p, 0]))]
        drums += [(t, bytes([0x99, 42, 60])), (t + 60, bytes([0x99, 42, 0]))]
    piano = [(0, b"\xff\x03\x05Piano")]
    for i, p in enumerate([60, 64, 67, 72]):
        piano += [(i * PPQ * 2, bytes([0x90, p, 90])), (i * PPQ * 2 + PPQ * 2 - 10, bytes([0x80, p, 0]))]
    write(os.path.join(OUT, "drums_piano_sample.mid"), [t0, drums, piano])


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    aerophone()
    drums_piano()
    print("wrote", os.listdir(OUT))
