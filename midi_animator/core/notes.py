"""Note naming. MIDI 60 = C4 (scientific pitch notation)."""

SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
# Brazilian / Latin solfège
SOLFEGE_SHARPS = ["Dó", "Dó#", "Ré", "Ré#", "Mi", "Fá", "Fá#", "Sol", "Sol#", "Lá", "Lá#", "Si"]
SOLFEGE_FLATS = ["Dó", "Réb", "Ré", "Mib", "Mi", "Fá", "Solb", "Sol", "Láb", "Lá", "Sib", "Si"]


def note_name(pitch, flats=False, solfege=False, octave=True):
    table = (SOLFEGE_FLATS if flats else SOLFEGE_SHARPS) if solfege else (FLATS if flats else SHARPS)
    name = table[pitch % 12]
    return f"{name}{pitch // 12 - 1}" if octave else name


def parse_note_name(text):
    """'C#4', 'Db4', 'Bb3' -> MIDI number. Raises ValueError."""
    t = text.strip()
    for i in range(len(t), 0, -1):
        head, tail = t[:i], t[i:]
        for table in (SHARPS, FLATS):
            if head in table and tail.lstrip("-").isdigit():
                return table.index(head) + (int(tail) + 1) * 12
    raise ValueError(f"Not a note name: {text!r}")
