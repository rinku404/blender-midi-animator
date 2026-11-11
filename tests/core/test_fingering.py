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
    assert min(SAX.chart) == n("Bb3") and max(SAX.chart) == n("F#6") == 90
    # every key used by the chart belongs to that finger
    for combo in SAX.chart.values():
        for slot, key in combo.items():
            assert key in SAX.slot(slot).keys


def test_sax_chart_full_range():
    # every written pitch Bb3 .. F#6 is mapped, and nothing outside it
    assert sorted(SAX.chart) == list(range(58, 91))
    for pitch, combo in SAX.chart.items():
        for slot, key in combo.items():
            assert SAX.slot(slot) is not None, (pitch, slot)
            assert key in SAX.slot(slot).keys, (pitch, slot, key)
        # the octave key is pressed from written D5 (74) up, never below
        assert (combo.get("LT") == "Octave") == (pitch >= 74), pitch


def test_sax_chart_palm_and_side_keys():
    assert SAX.chart[n("D6")] == {"LT": "Octave", "L1": "PalmD"}
    assert SAX.chart[n("D#6")] == {"LT": "Octave", "L1": "PalmEb"}
    assert SAX.chart[n("E6")] == {"LT": "Octave", "L1": "PalmEb", "R1": "SideE"}
    assert SAX.chart[n("F6")] == {"LT": "Octave", "L1": "PalmF", "R1": "SideE"}
    assert SAX.chart[n("F#6")] == {"LT": "Octave", "L1": "PalmF", "R1": "HighF#"}
    # low C# is the left pinky's C# key alone (the mechanism closes the low C pad)
    assert SAX.chart[n("C#4")] == {**SAX.chart[n("D4")], "L4": "LowC#"}
    # new keys go after the home key, so homes and existing markers don't change
    assert SAX.slot("R1").keys[0] == "F"


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


# -- shared bone chains (step 11) ---------------------------------------------

def chain_state_at(keys, frame):
    """(slot, state) in effect at a frame of a merged chain timeline."""
    cur = None
    for f, sl, st in keys:
        if f <= frame + 1e-6:
            cur = (sl, st)
    return cur


def merged(notes, mapping, groups, **params):
    tl = F.build_timeline(notes, mapping, SLOTS, HOMES, F.TimingParams(use_rest=False, **params))
    return tl, F.merge_shared(tl.keys, groups)


def test_merge_passes_unshared_slots_through():
    tl, m = merged([(10, 20, n("G4"))], chart_mapping(), {"L2": ["L2", "L3", "L4"]})
    assert m["L1"] == [(f, "L1", st) for f, st in tl.keys["L1"]]
    assert set(m) == set(SLOTS) - {"L3", "L4"}
    # groups with slots that have no timeline are ignored; a HAND pseudo slot passes through too
    keys = dict(tl.keys, **{F.HAND: [(8, ("up", None))]})
    m2 = F.merge_shared(keys, {"L2": ["L2", "L3", "L4"], "R2": ["R2", "R9"]})
    assert m2[F.HAND] == [(8, F.HAND, ("up", None))]
    assert m2["R2"] == [(f, "R2", st) for f, st in keys["R2"]]


def test_merge_agreeing_slots_follow_the_first_listed():
    # G4 presses L1 L2 L3: L2 and L3 agree (both down), the chain goes to L2's marker (listed first)
    tl, m = merged([(10, 20, n("G4"))], chart_mapping(), {"L2": ["L2", "L3", "L4"]})
    assert m["L2"] == [(f, "L2", st) for f, st in tl.keys["L2"]]
    assert chain_state_at(m["L2"], 15) == ("L2", ("down", "A"))


def test_merge_pressing_wins_over_lifting():
    # Custom map: note 1 presses L2 (A), note 2 presses L3 (G) only. The chain is on A, lifts with
    # L2 (lift lead), then drops onto G exactly at the second onset.
    mp = {60: F.NoteMap({"L2": "A"}), 62: F.NoteMap({"L3": "G"}), 64: F.NoteMap({})}
    tl, m = merged([(10, 20, 60), (20, 30, 62), (30, 40, 64)], mp, {"L2": ["L2", "L3", "L4"]},
                   transition=2, lift_lead=1)
    keys = m["L2"]
    assert (10, "L2", ("down", "A")) in keys
    assert (20, "L3", ("down", "G")) in keys
    assert chain_state_at(keys, 15) == ("L2", ("down", "A"))
    assert chain_state_at(keys, 25) == ("L3", ("down", "G"))
    # L3 arrives at 20 over 2 frames: its hold key at 18 is kept, so the move starts there
    assert chain_state_at(keys, 18)[1][0] != "down" or chain_state_at(keys, 18)[0] == "L2"
    assert all(f1 < f2 for (f1, _, _), (f2, _, _) in zip(keys, keys[1:]))
    # after both lift (the open note), the chain hovers over the key it left last (G, from L3)
    assert chain_state_at(keys, 35) == ("L3", ("up", "G"))


def test_merge_higher_priority_slot_keeps_the_chain_mid_note():
    # L2 holds A for the whole phrase; L3 presses G in the middle: L2 is listed first, so the chain
    # stays on A and L3's press adds no key at all
    mp = {60: F.NoteMap({"L2": "A"}), 62: F.NoteMap({"L2": "A", "L3": "G"})}
    tl, m = merged([(10, 20, 60), (20, 30, 62), (30, 40, 60)], mp, {"L2": ["L2", "L3", "L4"]})
    keys = m["L2"]
    assert all(sl == "L2" for _, sl, _ in keys)
    assert chain_state_at(keys, 25) == ("L2", ("down", "A"))
    assert [f for f, _, _ in keys] == [f for f, _ in tl.keys["L2"]]
    # the other way round, L3 listed first wins the shared frames
    m3 = F.merge_shared(tl.keys, {"L2": ["L3", "L2", "L4"]})
    assert chain_state_at(m3["L2"], 25) == ("L3", ("down", "G"))
    assert chain_state_at(m3["L2"], 15) == ("L2", ("down", "A"))


def test_merge_rest_and_override_are_unanimous():
    mp = {60: F.NoteMap({"L2": "A"}), 62: F.NoteMap(pose="Trill")}
    tl = F.build_timeline([(10, 20, 60), (60, 70, 62)], mp, SLOTS, HOMES,
                          F.TimingParams(use_rest=True, rest_gap=12))
    keys = F.merge_shared(tl.keys, {"L2": ["L2", "L3", "L4"]})["L2"]
    assert chain_state_at(keys, 8)[1] == F.REST          # the first key: Rest until the hand moves
    assert chain_state_at(keys, 40)[1] == F.REST
    assert chain_state_at(keys, 65)[1] == ("pose", "Trill")
    assert chain_state_at(keys, 80)[1] == F.REST


def test_combination_label():
    assert F.combination_label(SAX.chart[n("D5")], SAX.slots) == "LT L1 L2 L3 | R1 R2 R3"
    assert F.combination_label(SAX.chart[n("C4")], SAX.slots).endswith("R4:LowC")
    assert F.combination_label({}, SAX.slots) == "open"
