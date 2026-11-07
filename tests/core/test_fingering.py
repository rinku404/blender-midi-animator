from midi_animator.core import fingering as F
from midi_animator.core import profiles as P
from midi_animator.core.notes import parse_note_name as n

SAX = P.get("MONO_WIND")
SLOTS = [s.id for s in SAX.slots]
HOMES = {s.id: s.keys[0] for s in SAX.slots}


def chart_mapping():
    return {p: F.NoteMap(dict(c)) for p, c in SAX.chart.items()}


def state_at(keys, frame):
    """State in effect at a frame (last key at or before it)."""
    st = None
    for f, s in keys:
        if f <= frame + 1e-6:
            st = s
    return st


def test_sax_chart_basics():
    assert set(SAX.chart[n("D4")]) == {"L1", "L2", "L3", "R1", "R2", "R3"}
    assert SAX.chart[n("C#5")] == {}
    assert SAX.chart[n("D5")] == {**SAX.chart[n("D4")], "LT": "Octave"}
    assert SAX.chart[n("Bb3")]["L4"] == "LowBb"
    assert min(SAX.chart) == n("Bb3") and max(SAX.chart) == n("F6")
    # every key used by the chart belongs to that finger
    for combo in SAX.chart.values():
        for slot, key in combo.items():
            assert key in SAX.slot(slot).keys


def test_only_changed_fingers_move():
    notes = [(10, 20, n("G4")), (20, 30, n("A4"))]      # G -> A: only L3 lifts
    tl = F.build_timeline(notes, chart_mapping(), SLOTS, HOMES, F.TimingParams(use_rest=False))
    assert state_at(tl.keys["L3"], 20) == ("up", "G")
    assert state_at(tl.keys["L1"], 20) == ("down", "B")
    # L1 keys only around the first note, none at the G -> A change
    assert all(f < 15 for f, _ in tl.keys["L1"])


def test_lift_lead_and_arrival_at_onset():
    notes = [(10, 20, n("D4")), (20, 30, n("C#5"))]
    p = F.TimingParams(transition=2, lift_lead=1, use_rest=False)
    tl = F.build_timeline(notes, chart_mapping(), SLOTS, HOMES, p)
    # pressing at the first note arrives exactly at onset
    assert (10, ("down", "B")) in tl.keys["L1"]
    # lifting for the open C# leaves 1 frame early: arrives at 19, starts moving at 17
    assert (19, ("up", "B")) in tl.keys["L1"]
    assert (17, ("down", "B")) in tl.keys["L1"]


def test_relax_on_long_rest_and_hold_on_short_rest():
    m = chart_mapping()
    p = F.TimingParams(transition=2, lift_lead=1, rest_gap=12, use_rest=True)
    short = F.build_timeline([(10, 20, n("G4")), (25, 30, n("G4"))], m, SLOTS, HOMES, p)
    assert state_at(short.keys["L1"], 23) == ("down", "B")
    long = F.build_timeline([(10, 20, n("G4")), (50, 60, n("G4"))], m, SLOTS, HOMES, p)
    assert state_at(long.keys["L1"], 30) == F.REST
    assert state_at(long.keys["L1"], 50) == ("down", "B")
    assert long.keys["L1"][-1] == (62, F.REST)


def test_fast_notes_never_go_backwards():
    notes = [(i * 0.5, i * 0.5 + 0.5, n("G4") if i % 2 else n("A4")) for i in range(20)]
    tl = F.build_timeline(notes, chart_mapping(), SLOTS, HOMES, F.TimingParams(transition=3))
    for keys in tl.keys.values():
        frames = [f for f, _ in keys]
        assert frames == sorted(frames) and len(set(frames)) == len(frames)


def test_missing_and_override_pose():
    m = {n("G4"): F.NoteMap(pose="Trill")}
    notes = [(10, 20, n("G4")), (20, 30, n("A4"))]
    tl = F.build_timeline(notes, m, SLOTS + [F.HAND], HOMES, F.TimingParams(use_rest=False))
    assert tl.missing == [n("A4")]
    assert tl.notes_used == 1
    assert state_at(tl.keys["L1"], 15) == ("pose", "Trill")
    assert state_at(tl.keys[F.HAND], 15) == ("pose", "Trill")


def test_up_hovers_over_last_pressed_key():
    m = chart_mapping()
    notes = [(10, 20, n("B3")), (20, 30, n("D4"))]   # L4 presses LowB, then lifts
    tl = F.build_timeline(notes, m, SLOTS, HOMES, F.TimingParams(use_rest=False))
    assert state_at(tl.keys["L4"], 25) == ("up", "LowB")


def test_unchanging_finger_still_keyed():
    notes = [(10, 20, n("G4")), (20, 30, n("A4"))]      # R4 never presses
    tl = F.build_timeline(notes, chart_mapping(), SLOTS, HOMES, F.TimingParams(use_rest=False))
    assert tl.keys["R4"] == [(8, ("up", "LowEb"))]


def test_combination_label():
    assert F.combination_label(SAX.chart[n("D5")], SAX.slots) == "LT L1 L2 L3 | R1 R2 R3"
    assert F.combination_label(SAX.chart[n("C4")], SAX.slots).endswith("R4:LowC")
    assert F.combination_label({}, SAX.slots) == "open"
