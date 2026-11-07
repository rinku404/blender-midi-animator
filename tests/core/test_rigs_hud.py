from midi_animator.core import hud as H
from midi_animator.core import profiles as P
from midi_animator.core import rigs as R


def chain(prefix_fmt, parent, n=3):
    bones, p = [], parent
    for i in range(1, n + 1):
        name = prefix_fmt.format(i)
        bones.append((name, p))
        p = name
    return bones


def test_detect_rigify():
    bones = [("hand.L", None), ("hand.R", None)]
    for f in ("index", "middle", "ring", "pinky"):
        bones += chain(f"f_{f}.0{{}}.L", "hand.L") + chain(f"f_{f}.0{{}}.R", "hand.R")
        bones += [(f"f_{f}.01_master.L", "hand.L"), (f"ORG-f_{f}.01.L", "hand.L")]
    bones += chain("thumb.0{}.L", "hand.L")
    found = R.chains_for_slots(P.get("MONO_WIND").slots, bones)
    assert found["L1"] == ["f_index.01.L", "f_index.02.L", "f_index.03.L"]
    assert found["R4"] == ["f_pinky.01.R", "f_pinky.02.R", "f_pinky.03.R"]
    assert found["LT"][0] == "thumb.01.L"


def test_detect_mixamo_and_vroid():
    bones = [("mixamorig:LeftHand", None)] + chain("mixamorig:LeftHandIndex{}", "mixamorig:LeftHand", 4)
    bones += [("J_Bip_R_Hand", None)] + chain("J_Bip_R_Little{}", "J_Bip_R_Hand")
    bones += [("J_Bip_R_Little3_end", "J_Bip_R_Little3")]
    c = R.detect_finger_chains(bones)
    assert c[("L", "index")] == [f"mixamorig:LeftHandIndex{i}" for i in range(1, 5)]
    assert c[("R", "pinky")] == ["J_Bip_R_Little1", "J_Bip_R_Little2", "J_Bip_R_Little3"]


def test_fit_pitch_range():
    assert H.fit_pitch_range([60, 62]) == (55, 66)
    lo, hi = H.fit_pitch_range([58, 89])
    assert (lo, hi) == (57, 90)


def test_hud_states():
    notes = [(0.0, 1.0, 62), (1.0, 2.0, 64), (5.0, 6.0, 66)]
    style = H.HudStyle(width=1000, height=200, lookahead=3.0, pitch_lo=60, pitch_hi=70)
    prims = H.layout(notes, 1.5, style, lambda p: f"N{p}")
    bars = {p.role: p for p in prims if isinstance(p, H.Rect) and p.role in ("upcoming", "active", "played")}
    assert set(bars) == {"played", "active"}            # 66 is 3.5 s away: beyond look-ahead
    hit = 1000 * style.hit_x
    assert bars["active"].x < hit < bars["active"].x + bars["active"].w
    fill = next(p for p in prims if isinstance(p, H.Rect) and p.role == "active_fill")
    assert abs(fill.x + fill.w - hit) < 1e-6           # filled up to the hit line
    now = [p for p in prims if isinstance(p, H.Text) and p.role == "now"]
    assert now and now[0].text == "N64"
    timer = next(p for p in prims if isinstance(p, H.Text) and p.role == "timer")
    assert timer.text == "0.5s"
    # higher pitch is drawn higher
    assert bars["active"].y > bars["played"].y


def test_hud_upcoming_only_before_start():
    style = H.HudStyle(width=1000, height=200, pitch_lo=60, pitch_hi=70)
    prims = H.layout([(2.0, 3.0, 62)], 0.0, style, str)
    roles = [p.role for p in prims if isinstance(p, H.Rect)]
    assert "upcoming" in roles and "active" not in roles
    assert not [p for p in prims if isinstance(p, H.Text) and p.role == "now"]


def _names(*n):
    return [(x, None) for x in n]


def test_guess_hold_bones_rigify():
    bones = _names("spine", "spine.001", "spine.002", "spine.003", "spine.004", "DEF-hand.L", "hand_fk.L",
                   "hand_ik.L", "hand_fk.R", "hand_ik.R", "hand_tweak.L", "f_index.01.L", "ORG-spine.003")
    assert R.guess_hold_bones(bones) == ("spine.003", "hand_fk.L", "hand_fk.R")


def test_guess_hold_bones_mixamo():
    bones = _names("mixamorig:Hips", "mixamorig:Spine", "mixamorig:Spine1", "mixamorig:Spine2",
                   "mixamorig:LeftHand", "mixamorig:RightHand", "mixamorig:LeftHandIndex1",
                   "mixamorig:RightHandThumb2")
    assert R.guess_hold_bones(bones) == ("mixamorig:Spine2", "mixamorig:LeftHand", "mixamorig:RightHand")


def test_guess_hold_bones_vroid_and_biped():
    vroid = _names("J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_UpperChest", "J_Bip_L_Hand", "J_Bip_R_Hand",
                   "J_Bip_L_Index1")
    assert R.guess_hold_bones(vroid) == ("J_Bip_C_UpperChest", "J_Bip_L_Hand", "J_Bip_R_Hand")
    biped = _names("Bip01_Spine", "Bip01_Spine1", "Bip01_Spine2", "Bip01_L_Hand", "Bip01_R_Hand", "Bip01_L_Finger1")
    assert R.guess_hold_bones(biped) == ("Bip01_Spine2", "Bip01_L_Hand", "Bip01_R_Hand")


def test_guess_hold_bones_simple_and_empty():
    simple = _names("spine", "chest", "hand.L", "hand.R", "forearm.L", "thumb.L")
    assert R.guess_hold_bones(simple) == ("chest", "hand.L", "hand.R")
    assert R.guess_hold_bones(_names("root", "arm")) == ("", "", "")
