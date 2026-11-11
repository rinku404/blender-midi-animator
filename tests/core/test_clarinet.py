from midi_animator.core import fingering as F
from midi_animator.core import profiles as P
from midi_animator.core.notes import parse_note_name as n

CLAR = P.get("CLARINET_BB")
SAX = P.get("MONO_WIND")
CHART = CLAR.chart
SLOTS = [s.id for s in CLAR.slots]
HOMES = {s.id: s.keys[0] for s in CLAR.slots}

# Woodwind Fingering Guide, "Basic" Boehm fingerings (wfg.woodwind.org/clarinet), written pitch.
SOURCE = {
    52: "T 123E|123", 53: "T 123|123F", 54: "T 123F#|123", 55: "T 123|123",
    56: "T 123|123G#", 57: "T 123|12-", 58: "T 123|1--", 59: "T 123|-2-",
    60: "T 123|---", 61: "T 123C#|---", 62: "T 12-|---", 63: "T 12-|4---",
    64: "T 1--|---", 65: "T ---|---", 66: "1--|---", 67: "---|---",
    68: "G#---|---", 69: "A---|---", 70: "R A---|---",
    71: "RT 123E|123", 72: "RT 123|123F", 73: "RT 123F#|123", 74: "RT 123|123",
    75: "RT 123|123G#", 76: "RT 123|12-", 77: "RT 123|1--", 78: "RT 123|-2-",
    79: "RT 123|---", 80: "RT 123C#|---", 81: "RT 12-|---", 82: "RT 12-|4---",
    83: "RT 1--|---", 84: "RT ---|---",
}


def parse_source(text):
    """Turn a table entry like 'RT 123F#|123' into {slot: key}."""
    combo = {}
    left, right = text.split("|")
    head, _, left = left.rpartition(" ")
    if head == "RT":
        combo["LT"] = "Register"
    elif head == "T":
        combo["LT"] = "Hole"
    elif head == "R":
        combo["LT"] = "RegOnly"
    else:
        assert head == "", text
    if left.startswith("G#"):
        combo["L1"], left = "G#", left[2:]
    elif left.startswith("A"):
        combo["L1"], left = "A", left[1:]
    for slot, ch in zip(("L1", "L2", "L3"), left[:3]):
        if ch != "-":
            assert slot not in combo, text         # a throat key and its hole never together
            combo[slot] = "Hole"
    pinky = left[3:]
    if pinky:
        combo["L4"] = {"E": "E/B", "F#": "F#/C#", "C#": "C#/G#"}[pinky]
    if right.startswith("4"):
        combo["R1"], right = "Eb/Bb", right[1:]
    for slot, ch in zip(("R1", "R2", "R3"), right[:3]):
        if ch != "-":
            assert slot not in combo, text
            combo[slot] = "Hole"
    pinky = right[3:]
    if pinky:
        combo["R4"] = {"F": "F/C", "G#": "Ab/Eb"}[pinky]
    return combo


def test_registry():
    assert P.get("CLARINET_BB").id == "CLARINET_BB"
    assert P.get("MONO_WIND").id == "MONO_WIND"
    assert CLAR.default_transpose == 2 and SAX.default_transpose == 0
    assert CLAR.monophonic
    assert [s.id for s in CLAR.slots] == [s.id for s in SAX.slots]


def test_full_range_and_keys_exist():
    assert sorted(CHART) == list(range(52, 85))        # written E3 .. C6
    for pitch, combo in CHART.items():
        for slot, key in combo.items():
            assert CLAR.slot(slot) is not None, (pitch, slot)
            assert key in CLAR.slot(slot).keys, (pitch, slot, key)


def test_register_key_placement():
    for p, combo in CHART.items():
        lt = combo.get("LT")
        assert (lt == "Register") == (71 <= p <= 84), p
        assert (lt == "RegOnly") == (p == 70), p
        assert (lt == "Hole") == (52 <= p <= 65), p
        if 66 <= p <= 69:
            assert "LT" not in combo, p


def test_clarion_rule():
    for p in range(71, 85):
        assert CHART[p] == {**CHART[p - 19], "LT": "Register"}, p


def test_throat_tones_and_break():
    assert CHART[n("F#4")] == {"L1": "Hole"}
    assert CHART[n("G4")] == {}
    assert CHART[n("G#4")] == {"L1": "G#"}
    assert CHART[n("A4")] == {"L1": "A"}
    assert CHART[n("A#4")] == {"LT": "RegOnly", "L1": "A"}
    holes = {s: "Hole" for s in ("L1", "L2", "L3", "R1", "R2", "R3")}
    assert CHART[n("B4")] == {**holes, "LT": "Register", "L4": "E/B"}
    assert CHART[n("E3")] == {**holes, "LT": "Hole", "L4": "E/B"}


def test_matches_source_table():
    assert sorted(SOURCE) == list(range(52, 85))
    for pitch, text in SOURCE.items():
        assert parse_source(text) == CHART[pitch], (pitch, text, CHART[pitch])


def test_users_take_is_in_chart():
    # zelda_recorded_v1_b.mid (plan step 6), written pitches with Transpose +2: E3 .. A5
    written_take = {52, 55, 56, 57, 59, 62, 63, 64, 65, 66, 67, 68, 69, 71, 72, 73, 74, 76, 78, 80, 81}
    for p in written_take:
        assert p in CHART, p


def test_combination_label():
    assert F.combination_label(CHART[n("B4")], CLAR.slots) == "LT:Register L1 L2 L3 L4 | R1 R2 R3"
    assert F.combination_label(CHART[n("G4")], CLAR.slots) == "open"


def tl(notes):
    mapping = {p: F.NoteMap(dict(c)) for p, c in CHART.items()}
    return F.build_timeline(notes, mapping, SLOTS, HOMES, F.TimingParams(use_rest=False))


def state_at(keys, frame):
    st = None
    for f, s in keys:
        if f <= frame + 1e-6:
            st = s
    return st


def test_g4_to_a4_moves_only_l1():
    t = tl([(10, 20, n("G4")), (20, 30, n("A4"))])
    assert t.missing == []
    assert state_at(t.keys["L1"], 25) == ("down", "A")
    for slot in SLOTS:
        if slot != "L1":
            assert state_at(t.keys[slot], 25) == state_at(t.keys[slot], 15), slot


def test_break_crossing():
    t = tl([(10, 20, n("A4")), (20, 30, n("B4"))])
    assert state_at(t.keys["LT"], 25) == ("down", "Register")
    assert state_at(t.keys["L1"], 25) == ("down", "Hole")
    assert state_at(t.keys["L4"], 25) == ("down", "E/B")
    assert state_at(t.keys["R4"], 25)[0] == "up"
