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


CJ_BONES = [("spine upper_013", None), ("arm left shoulder 2_039", "spine upper_013"),
            ("arm left elbow_040", "arm left shoulder 2_039"), ("arm left wrist_041", "arm left elbow_040"),
            ("arm left finger 2a_042", "arm left wrist_041"), ("arm left finger 2b_043", "arm left finger 2a_042"),
            ("arm left finger 2c_044", "arm left finger 2b_043"),
            ("arm left finger 1a_045", "arm left wrist_041"), ("arm left finger 1b_046", "arm left finger 1a_045"),
            ("arm left finger 1c_047", "arm left finger 1b_046"),
            ("arm right wrist_051", None),
            ("arm right finger 2a_052", "arm right wrist_051"), ("arm right finger 2b_053", "arm right finger 2a_052"),
            ("arm right finger 2c_054", "arm right finger 2b_053"),
            ("arm right finger 1a_055", "arm right wrist_051"), ("arm right finger 1b_056", "arm right finger 1a_055"),
            ("arm right finger 1c_057", "arm right finger 1b_056")]


def test_detect_numbered_fingers_cj():
    """CJ's original rig (midi_trial_before_fingers.blend, Object_3): two numbered fingers per hand."""
    c = R.detect_finger_chains(CJ_BONES)
    assert c[("L", "index")] == ["arm left finger 1a_045", "arm left finger 1b_046", "arm left finger 1c_047"]
    assert c[("L", "middle")] == ["arm left finger 2a_042", "arm left finger 2b_043", "arm left finger 2c_044"]
    assert c[("R", "index")][0] == "arm right finger 1a_055" and c[("R", "middle")][-1] == "arm right finger 2c_054"
    assert set(c) == {("L", "index"), ("L", "middle"), ("R", "index"), ("R", "middle")}
    # the wrists are the hands (step 7a, P2); finger bones never are
    assert R.guess_hold_bones(CJ_BONES)[1:] == ("arm left wrist_041", "arm right wrist_051")


def test_guess_hold_bones_cj_wrists_and_upper_chest():
    """CJ's FBX rig: hands named wrist, a spine lower/middle/upper chain; the strap is the upper
    chest, where the neck and the arms branch, not the lowest spine bone (step 6, P2)."""
    bones = [("root hips_00", None), ("pelvis_02", "root hips_00"), ("spine lower_011", "root hips_00"),
             ("spine middle_012", "spine lower_011"), ("spine upper_013", "spine middle_012"),
             ("head neck lower_014", "spine upper_013"), ("head neck upper_015", "head neck lower_014"),
             ("arm left shoulder 1_038", "spine upper_013"), ("arm left shoulder 2_039", "arm left shoulder 1_038"),
             ("arm left elbow_040", "arm left shoulder 2_039"), ("arm left wrist_041", "arm left elbow_040"),
             ("arm right shoulder 1_048", "spine upper_013"), ("arm right shoulder 2_049", "arm right shoulder 1_048"),
             ("arm right elbow_050", "arm right shoulder 2_049"), ("arm right wrist_051", "arm right elbow_050"),
             ("f_index.01.L", "arm left wrist_041"), ("thumb.01.R", "arm right wrist_051")]
    assert R.guess_hold_bones(bones) == ("spine upper_013", "arm left wrist_041", "arm right wrist_051")
    # a plain numbered chain with nothing branching: the highest spine bone
    plain = [("Spine_01", None), ("Spine_02", "Spine_01"), ("Spine_03", "Spine_02")]
    assert R.guess_hold_bones(plain)[0] == "Spine_03"
    # a chain whose last spine bones are the neck and head: the one the arms hang from
    with_neck = plain + [("Spine_04", "Spine_03"), ("Spine_05", "Spine_04"), ("L_Clavicle", "Spine_03"),
                         ("R_Clavicle", "Spine_03"), ("L_Hand", None), ("R_Hand", None)]
    assert R.guess_hold_bones(with_neck) == ("Spine_03", "L_Hand", "R_Hand")


def test_assign_slots_two_finger_hand_shares_and_tilts():
    a = R.assign_slots(P.get("MONO_WIND").slots, CJ_BONES)
    assert set(a.chains) == {"L1", "L2", "R1", "R2"}
    assert a.shares == {"L3": "L2", "L4": "L2", "R3": "R2", "R4": "R2"}
    assert a.tilt_hands == {"LT": "arm left wrist_041"}
    # the clarinet has the same slots, so the same proposal
    b = R.assign_slots(P.get("CLARINET_BB").slots, CJ_BONES)
    assert (b.chains, b.shares, b.tilt_hands) == (a.chains, a.shares, a.tilt_hands)


def test_assign_slots_three_four_and_five_numbered_fingers():
    def hand(n, side="left"):
        bones = [(f"{side} hand", None)]
        for k in range(1, n + 1):
            names = [f"{side} finger {k}{j}" for j in "abc"]
            bones += list(zip(names, [f"{side} hand"] + names[:-1]))
        return bones

    three = R.assign_slots(P.get("MONO_WIND").slots, hand(3))
    assert set(three.chains) == {"L1", "L2", "L3"} and three.shares == {"L4": "L3"}
    assert three.tilt_hands == {"LT": "left hand"}
    four = R.assign_slots(P.get("MONO_WIND").slots, hand(4))
    assert set(four.chains) == {"L1", "L2", "L3", "L4"} and four.shares == {} and four.tilt_hands == {"LT": "left hand"}
    five = R.assign_slots(P.get("MONO_WIND").slots, hand(5))
    assert set(five.chains) == {"LT", "L1", "L2", "L3", "L4"} and five.shares == {} and five.tilt_hands == {}
    assert five.chains["LT"] == ["left finger 1a", "left finger 1b", "left finger 1c"]
    # a named hand missing one finger: it shares with the finger before it; nothing found, nothing proposed
    named = [("hand.L", None)] + chain("f_index.0{}.L", "hand.L") + chain("f_middle.0{}.L", "hand.L") \
        + chain("f_pinky.0{}.L", "hand.L") + chain("thumb.0{}.L", "hand.L")
    a = R.assign_slots(P.get("MONO_WIND").slots, named)
    assert a.shares == {"L3": "L2"} and a.tilt_hands == {}
    empty = R.assign_slots(P.get("MONO_WIND").slots, [("root", None), ("arm", "root")])
    assert (empty.chains, empty.shares, empty.tilt_hands) == ({}, {}, {})
    # numbered names don't hijack a side that has named fingers
    mixed = named + [("left finger 1a", "hand.L"), ("left finger 1b", "left finger 1a")]
    assert set(R.assign_slots(P.get("MONO_WIND").slots, mixed).chains) == {"LT", "L1", "L2", "L4"}


def test_tilt_rotation():
    import math
    assert R.tilt_rotation("X", 3.0) == (0, math.radians(3.0))
    assert R.tilt_rotation("-X", 3.0) == (0, -math.radians(3.0))
    assert R.tilt_rotation("Z", -2.0) == (2, -math.radians(2.0))
    assert R.tilt_rotation("-Z", 2.0) == (2, -math.radians(2.0))
    try:
        R.tilt_rotation("Y", 1.0)
        raise AssertionError("Y is not a bend axis")
    except ValueError:
        pass


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


# -- bend axis ----------------------------------------------------------------

def _curled(angle_deg, axis):
    """Child frame after the parent (along +Y, X = +X, Z = +Z) turned by angle around a local axis."""
    import math
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "X":      # Y turns toward Z
        return (1, 0, 0), (0, c, s), (0, -s, c)
    return (c, s, 0), (-s, c, 0), (0, 0, 1)        # around Z: Y turns toward -X


def test_joint_curl_sign_matches_rotation():
    cx, cy, cz = _curled(10, "X")
    x, z = R.joint_curl((0, 1, 0), cx, cy, cz)
    assert x > 0.15 and abs(z) < 1e-9          # positive rotation around X bends it this way
    cx, cy, cz = _curled(-10, "X")
    assert R.joint_curl((0, 1, 0), cx, cy, cz)[0] < -0.15
    cx, cy, cz = _curled(8, "Z")
    x, z = R.joint_curl((0, 1, 0), cx, cy, cz)
    assert z > 0.1 and abs(x) < 1e-9


def test_detect_bend_axis():
    # Rigify human metarig (measured in Blender 5.2): the joints inside the fingers curl around +X
    rigify = [(0.155, -0.007), (0.226, -0.067), (0.312, -0.147), (0.033, -0.082), (0.087, 0.033)]
    assert R.detect_bend_axis(rigify) == "X"
    assert R.detect_bend_axis([(-x, z) for x, z in rigify]) == "-X"
    assert R.detect_bend_axis([(0.01, 0.2), (0.0, 0.1)]) == "Z"
    assert R.detect_bend_axis([(0.01, -0.2)]) == "-Z"
    assert R.detect_bend_axis([(0.001, 0.0), (0.0, -0.001)]) is None    # straight fingers
    assert R.detect_bend_axis([]) is None


def test_ik_joint_settings():
    import math
    hinge = R.ik_joint_settings("X", keep_twist=True)
    assert hinge["lock_ik_y"] and hinge["lock_ik_z"] and not hinge["lock_ik_x"]
    assert hinge["use_ik_limit_x"] and hinge["ik_min_x"] == 0.0 and hinge["ik_max_x"] > math.radians(90)
    root = R.ik_joint_settings("X", keep_twist=True, root=True)
    assert not root["lock_ik_z"] and root["use_ik_limit_z"]          # knuckle may spread
    assert abs(root["ik_max_z"] - math.radians(R.ROOT_SPREAD_DEG)) < 1e-9
    neg = R.ik_joint_settings("-Z", keep_twist=False)
    assert neg["lock_ik_x"] and not neg["lock_ik_y"] and not neg["lock_ik_z"]
    assert neg["ik_max_z"] == 0.0 and neg["ik_min_z"] < -math.radians(90)
    assert R.locked_axes("X") == ["y", "z"]
    assert R.locked_axes("X", keep_twist=False, root=True) == []
    try:
        R.ik_joint_settings("Y")
        raise AssertionError("Y is the bone's own axis, not a bend axis")
    except ValueError:
        pass


def test_knuckle_swing_and_thumb_turn():
    import math
    # Knuckle swing widens the root's sideways limit (along the instrument); hinges are unchanged
    root = R.ik_joint_settings("X", root=True, swing_deg=15.0)
    assert abs(root["ik_max_z"] - math.radians(40.0)) < 1e-9 and abs(root["ik_min_z"] + math.radians(40.0)) < 1e-9
    assert root["lock_ik_y"] and not root["use_ik_limit_y"]            # Keep Twist still locks the twist
    hinge = R.ik_joint_settings("X", root=False, swing_deg=15.0, turn_deg=30.0)
    assert hinge["lock_ik_z"] and hinge["lock_ik_y"]                    # swing and turn are root-only
    assert R.ik_joint_settings("-Z", root=True, swing_deg=-5.0)["ik_max_x"] == R.ik_joint_settings("-Z", root=True)["ik_max_x"]
    # Thumb turn: the base joint may twist about its own length, limited, with Keep Twist on
    thumb = R.ik_joint_settings("X", keep_twist=True, root=True, turn_deg=30.0)
    assert not thumb["lock_ik_y"] and thumb["use_ik_limit_y"]
    assert abs(thumb["ik_max_y"] - math.radians(30.0)) < 1e-9 and abs(thumb["ik_min_y"] + math.radians(30.0)) < 1e-9
    assert R.locked_axes("X", root=True, turn_deg=30.0) == []
    assert R.locked_axes("X", root=True) == ["y"]
    assert R.ik_joint_settings("X", root=True, turn_deg=0.0)["lock_ik_y"]
    free = R.ik_joint_settings("X", keep_twist=False, root=True, turn_deg=30.0)
    assert not free["lock_ik_y"] and not free["use_ik_limit_y"]        # Keep Twist off: twist stays free


def test_knuckle_lift():
    import math
    lift = math.radians(25.0)
    up = R.ik_joint_settings("X", root=True, lift_deg=25.0)
    assert abs(up["ik_min_x"] + lift) < 1e-9 and abs(up["ik_max_x"] - math.radians(R.MAX_BEND_DEG)) < 1e-9
    neg = R.ik_joint_settings("-Z", root=True, lift_deg=25.0)             # negative curl: backwards is +
    assert abs(neg["ik_max_z"] - lift) < 1e-9 and neg["ik_min_z"] < -math.radians(90)
    down = R.ik_joint_settings("X", root=True)                             # Down poses: no lift
    assert down["ik_min_x"] == 0.0
    hinge = R.ik_joint_settings("X", root=False, lift_deg=25.0)            # hinges never bend backwards
    assert hinge["ik_min_x"] == 0.0
    assert R.ik_joint_settings("-X", root=True, lift_deg=-5.0)["ik_max_x"] == 0.0


def test_tube_axis():
    # Markers down a tube along -Z, left hand (rank 0..3) above the right (rank 4..7)
    pts = [(i, (0.01 * (i % 2), 0.0, 1.0 - 0.03 * i)) for i in range(8)]
    u = R.tube_axis(pts)
    assert u[2] > 0.99, u                       # points up the tube, toward the mouthpiece
    pts = [(i, (0.0, 0.0, 0.5 + 0.03 * i)) for i in range(4)]
    assert R.tube_axis(pts)[2] < -0.99          # rank grows upward here, so "up the tube" is -Z
    assert R.tube_axis([(0, (0, 0, 0))]) is None
    assert R.tube_axis([(0, (1, 1, 1)), (1, (1, 1, 1))]) is None


def test_miss_advice():
    up, out = (0.0, 0.0, 1.0), (0.0, -1.0, 0.0)
    assert R.miss_advice((0.0, 0.0, 0.0), up, out) == ""
    s = R.miss_advice((0.001, 0.0, 0.019), up, out)
    assert s.startswith("move the hand 19 mm up the tube"), s
    assert "down the tube" in R.miss_advice((0.0, 0.0, -0.012), up, out)
    s = R.miss_advice((0.0, -0.012, 0.001), up, out)        # target 12 mm further out than the tip: tip inside the key
    assert "12 mm too deep" in s and "12 mm away from the keys" in s, s
    s = R.miss_advice((0.0, 0.012, 0.0), up, out)            # target deeper in than the tip: the tip falls short
    assert "12 mm too far out" in s and "12 mm toward the keys" in s, s
    s = R.miss_advice((0.010, 0.004, 0.004), up, out)        # round the tube
    assert s.startswith("move the hand 11 mm toward the key, round the tube"), s
    assert "toward the key" in R.miss_advice((0.01, 0.0, 0.0))       # no frame at all


def test_overlay_colorspace_exact_views():
    assert H.overlay_colorspace("Standard") == ("sRGB", True, "")
    assert H.overlay_colorspace("ACES 2.0") == ("ACES 2.0 sRGB", True, "")


def test_overlay_colorspace_toned_cases():
    space, exact, why = H.overlay_colorspace("AgX")
    assert (space, exact) == ("AgX Base sRGB", False) and "AgX" in why
    space, exact, why = H.overlay_colorspace("Filmic", look="Medium Contrast")
    assert (space, exact) == ("Filmic sRGB", False) and "look" in why
    assert H.overlay_colorspace("Standard", exposure=1.0)[1] is False
    assert H.overlay_colorspace("Standard", curves=True)[2] == "curves"
    assert H.overlay_colorspace("False Color")[:2] == ("sRGB", False)
    assert H.overlay_colorspace("Standard", display="Display P3")[:2] == ("sRGB", False)
