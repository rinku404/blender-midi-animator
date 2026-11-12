"""End-to-end test inside Blender:

    blender -b --factory-startup --python tests/test_in_blender.py

Builds a small rig with Rigify-style finger names (fingers curled a little downwards at rest),
an instrument with key markers and a face with a CheekPuff shape key; then Detect Fingers ->
Autoassign -> Fill From Chart -> blow effects -> Bake, and checks the result. Then it switches
to the B-flat clarinet profile and runs markers -> Autoassign -> Fill -> Bake again. Finally it
builds a two-finger hand (CJ-style numbered bones, no thumb) and checks shared finger slots and
the thumb tilt (step 11), and a CJ-style rig with off-joint arm tails to check that Lock moves
nothing, that Guess Bones finds wrists and the upper chest, and the instrument's front (step 7a).
Breathing (step 7b) is checked on the first rig (with the hold locked) and on CJ-style rigs with
upright and with sideways spine bones: the right axes, no head or arm growth, hands on target.
"""
import math
import os
import sys
import traceback

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import midi_animator  # noqa: E402
from midi_animator.blender import actions, autoassign, bake, breathing, rig, state  # noqa: E402
from midi_animator.core.notes import parse_note_name  # noqa: E402

MID = os.path.join(ROOT, "examples", "aerophone_sample.mid")
CURL = math.radians(8)        # rest curl per joint (downwards): the test rig's bend axis is -X
FINGERS = [("thumb", "L", -0.06), ("f_index", "L", -0.02), ("f_middle", "L", 0.0), ("f_ring", "L", 0.02),
           ("f_pinky", "L", 0.04), ("f_index", "R", -0.02), ("f_middle", "R", 0.0), ("f_ring", "R", 0.02),
           ("f_pinky", "R", 0.04)]
# A two-finger hand like CJ's original rig: numbered fingers, joints a/b/c, no thumb
FINGERS2 = [("1", "L", -0.02), ("2", "L", 0.02), ("1", "R", -0.02), ("2", "R", 0.02)]


def rigify_name(name, i, side):
    return f"{name}.0{i}.{side}"


def cj_name(name, i, side):
    return f"arm {'left' if side == 'L' else 'right'} finger {name}{'abc'[i - 1]}_0{40 + 3 * int(name) + i}"


def build_scene(fingers=FINGERS, bone_name=rigify_name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    arm_data = bpy.data.armatures.new("Rig")
    arm = bpy.data.objects.new("Rig", arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    spine = eb.new("spine")
    spine.head, spine.tail = (0, 0, 0), (0, 0, 1)
    chest = eb.new("chest")
    chest.head, chest.tail, chest.parent = (0, 0, 1), (0, 0, 1.4), spine
    for side, x in (("L", 0.3), ("R", -0.3)):
        upper = eb.new(f"upper_arm.{side}")
        upper.head, upper.tail, upper.parent = (x * 0.6, 0.0, 1.4), (x, -0.25, 1.3), chest
        fore = eb.new(f"forearm.{side}")
        fore.head, fore.tail, fore.parent = (x, -0.25, 1.3), (x, 0, 1.3), upper
        fore.use_connect = True
        hand = eb.new(f"hand.{side}")
        hand.head, hand.tail, hand.parent = (x, 0, 1.3), (x, 0.1, 1.3), fore
        hand.use_connect = True
        for name, s, z in fingers:
            if s != side:
                continue
            parent, head = hand, Vector((x, 0.1, 1.3 + z))
            for i in range(1, 4):
                b = eb.new(bone_name(name, i, side))
                a = CURL * (i - 1)
                b.head, b.tail = head, head + Vector((0, math.cos(a), -math.sin(a))) * 0.03
                b.roll = 0.0
                b.parent = parent
                b.use_connect = i > 1
                parent, head = b, b.tail.copy()
    bpy.ops.object.mode_set(mode="OBJECT")

    # Idle action that must survive as a base layer
    arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions.new("Idle")
    arm.pose.bones["hand.L"].location.y = 0.05
    arm.pose.bones["hand.L"].keyframe_insert("location", index=1, frame=1)

    sax = bpy.data.objects.new("Sax", None)
    scene.collection.objects.link(sax)

    bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 1.7))
    face = bpy.context.active_object
    face.name = "Face"
    face.shape_key_add(name="Basis")
    face.shape_key_add(name="CheekPuff")
    face.parent = arm
    bpy.context.view_layer.objects.active = arm
    return scene, arm, sax, face


def place_markers(s, arm):
    """One marker per key, below each fingertip, where the finger reaches it (and the hover point
    above it) by curling. Keys of one finger lie side by side, the later ones a little to the
    side, so the knuckle has to spread."""
    prof = state.profile(s)
    ctx = bpy.context
    ctx.view_layer.update()
    bones, tilt = rig.finger_bones(s), rig.tilt_slots(s)
    users = {sl: group for group in rig.share_groups(s).values() for sl in group}
    for slot in prof.slots:
        if slot.id in tilt or slot.id not in bones:
            continue
        chain = bones[slot.id]
        tip = arm.matrix_world @ arm.pose.bones[chain[-1]].tail
        dx = 0.004 * users[slot.id].index(slot.id)     # slots sharing a chain: keys side by side
        for k, key in enumerate(slot.keys):
            ctx.scene.cursor.location = tip + Vector((0.003 * k + dx, -0.02, -0.03))
            ctx.scene.cursor.rotation_euler = (0, 0, 0)
            rig.add_marker(ctx, s, slot.id, key)


def tip_world(arm, bone):
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[bone].tail


def joint_angles(q):
    """(bend around X, twist around Y, side turn) in degrees for a bone-space rotation: the
    bone's direction (local Y) after q, in its rest frame, plus the swing-twist twist."""
    d = q @ Vector((0, 1, 0))
    bend = math.degrees(math.atan2(d.z, d.y))
    side = math.degrees(math.asin(max(-1.0, min(1.0, d.x))))
    twist = math.degrees(2 * math.atan2(q.y, q.w))
    twist = (twist + 180) % 360 - 180
    return bend, twist, side


def bend_checks(s, arm, markers, slots=None, keep_twist=True):
    """Every generated pose: joints turn only around the bend axis (-X here) and only to curl;
    the knuckle may also spread; every pose still puts the tip on its target (Down: the key,
    Up: the hover point). Returns (max against-the-axis bend in degrees, max turn on a locked
    axis in degrees, max tip-to-target distance)."""
    bones = rig.finger_bones(s)
    against = locked = worst_tip = 0.0
    sign = -1.0 if s.bend_axis.startswith("-") else 1.0
    for slot in state.profile(s).slots:
        if slots and slot.id not in slots:
            continue
        chain = bones[slot.id]
        for key in slot.keys:
            for down in (True, False):
                name = autoassign.pose_name(slot.id, key, down)
                if name not in bpy.data.actions:
                    continue
                bpy.ops.midianim.apply_pose(action=name)
                bpy.context.view_layer.update()
                for i, b in enumerate(chain):
                    q = arm.pose.bones[b].rotation_quaternion.copy()
                    bend, twist, side = joint_angles(q)
                    against = max(against, -sign * bend)
                    e = q.to_euler("XYZ")         # hinge joints: only X may be non-zero
                    if i == 0 and slot.finger == "thumb":      # the thumb's base may turn by Thumb Turn
                        twist = max(0.0, abs(twist) - s.thumb_turn - 0.5)
                    turns = [twist] if keep_twist else []
                    if i > 0:
                        turns += [side, math.degrees(e.z)] + ([math.degrees(e.y)] if keep_twist else [])
                    locked = max([locked] + [abs(v) for v in turns])
                mw = markers[(slot.id, key)].matrix_world
                target = mw.translation if down else mw.translation + mw.to_3x3().col[2].normalized() * s.hover
                worst_tip = max(worst_tip, (tip_world(arm, chain[-1]) - target).length)
    return against, locked, worst_tip


def _tip_if_posed(arm, chain, eulers):
    """Where the chain's tip would be with these XYZ eulers (radians) per bone; the pose is put back."""
    pb = arm.pose.bones
    saved = [pb[b].rotation_quaternion.copy() for b in chain]
    for b, e in zip(chain, eulers):
        pb[b].rotation_quaternion = Euler(e, "XYZ").to_quaternion()
    tip = tip_world(arm, chain[-1]).copy()
    for b, q in zip(chain, saved):
        pb[b].rotation_quaternion = q
    bpy.context.view_layer.update()
    return tip


def reach_checks(s, arm, markers):
    """Step 7c: a key beside the index's hole (along the instrument) that only the Knuckle Swing
    reaches, and a key the thumb only reaches by turning its base about its length (Thumb Turn).
    Each is missed with the new freedom off, reached with the defaults, and the miss is written
    on the pose with advice."""
    bones = rig.finger_bones(s)
    r = math.radians
    cases = (
        # index: nearly straight, knuckle swung 38 deg sideways (past the 25 deg spread)
        ("L1", "PalmF", [(r(-5), 0, r(38)), (r(-15), 0, 0), (r(-15), 0, 0)], "knuckle_swing"),
        # thumb: base turned 28 deg about its own length, curled hard
        ("LT", "Octave", [(r(-20), r(28), 0), (r(-90), 0, 0), (r(-90), 0, 0)], "thumb_turn"),
    )
    for slot, key, eulers, prop in cases:
        m = markers[(slot, key)]
        old = m.matrix_world.copy()
        m.matrix_world = Matrix.Translation(_tip_if_posed(arm, bones[slot], eulers)) @ old.to_3x3().to_4x4()
        bpy.context.view_layer.update()
        name = autoassign.pose_name(slot, key, True)
        default = getattr(s, prop)
        setattr(s, prop, 0.0)
        _, _, problems, _ = autoassign.autoassign(bpy.context, s, slot)
        off = bpy.data.actions[name].get(autoassign.MISS_PROP)
        advice = bpy.data.actions[name].get(autoassign.ADVICE_PROP, "")
        setattr(s, prop, default)
        _, _, problems_on, _ = autoassign.autoassign(bpy.context, s, slot)
        bpy.ops.midianim.apply_pose(action=name)
        on = (tip_world(arm, bones[slot][-1]) - m.matrix_world.translation).length
        print(f"reach {slot} {key}: {prop}=0 misses by {off} mm ({advice}); "
              f"{prop}={default:.0f} reaches it within {on * 1000:.2f} mm")
        assert off and off > 3.0 and advice.startswith(("move the hand", "the fingertip")), (off, advice)
        assert problems and problems[0].startswith(state.profile(s).slots[[x.id for x in state.profile(s).slots].index(slot)].label)
        assert on < 0.003 and bpy.data.actions[name].get(autoassign.MISS_PROP) is None, on
        m.matrix_world = old
        bpy.context.view_layer.update()
        autoassign.autoassign(bpy.context, s, slot)
    # Keep Twist still holds everywhere else: only the thumb's base turned, within Thumb Turn
    assert max(bend_checks(s, arm, markers)[:2]) < 1.0


def hold_checks(scene, s, arm, sax, markers):
    """Hold the Instrument: lock, follow, idempotent, unlock, and no breathing scale on the sax."""
    pb = arm.pose.bones
    bpy.context.view_layer.update()
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    assert (s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r) == ("chest", "hand.L", "hand.R"),         (s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r)
    scene.frame_set(1)
    bpy.context.view_layer.update()

    def world(bone):
        return arm.matrix_world @ pb[bone].head

    hand_before, elbow_before = world("hand.L").copy(), world("forearm.L").copy()
    sax_before = sax.matrix_world.translation.copy()
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    bpy.context.view_layer.update()
    con = sax.constraints["MIDI Hold Strap"]
    assert con.subtarget == "chest" and sax.parent is None
    assert (sax.matrix_world.translation - sax_before).length < 1e-4, "sax moved on lock"
    assert (world("hand.L") - hand_before).length < 1e-3, "hand moved on lock"
    assert (world("forearm.L") - elbow_before).length < 1e-2, "elbow drifted on lock"
    assert markers[("L1", "B")].parent == sax

    # Bend the chest: the sax follows, and the hands stay on their targets
    pb["chest"].rotation_mode = "XYZ"
    pb["chest"].rotation_euler.x = math.radians(20)
    bpy.context.view_layer.update()
    tgt = bpy.data.objects["MIDI Hold L"]
    assert (sax.matrix_world.translation - sax_before).length > 0.01, "sax did not follow the chest"
    assert (world("hand.L") - tgt.matrix_world.translation).length < 1e-3
    pb["chest"].rotation_euler.x = 0
    bpy.context.view_layer.update()

    # Autoassign still puts the fingertip on its key with the hold locked
    s.force_autoassign = True
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
    s.force_autoassign = False
    bpy.ops.midianim.apply_pose(action="F.L1.B.Down")
    d = (tip_world(arm, "f_index.03.L") - markers[("L1", "B")].matrix_world.translation).length
    print(f"tip distance with hold locked: {d:.4f}")
    assert d < 0.004, d
    bpy.ops.midianim.apply_pose(action="F.L1.B.Up")



def hold_breath_checks(scene, s, arm, sax):
    """After a bake with Breathing and the hold locked."""
    pb = arm.pose.bones
    # Breathing never scales the instrument (a bone-parented child would)
    probe = bpy.data.objects.new("probe", None)
    scene.collection.objects.link(probe)
    probe.parent, probe.parent_type, probe.parent_bone = arm, "BONE", "chest"
    worst, probe_scale, gap = 0.0, 1.0, 0.0
    tgt = bpy.data.objects["MIDI Hold L"]
    for f in range(1, int(1 + 6 * 24), 3):
        scene.frame_set(f)
        gap = max(gap, (arm.matrix_world @ pb["hand.L"].head - tgt.matrix_world.translation).length)
        worst = max(worst, max(abs(v - 1.0) for v in sax.matrix_world.to_scale()))
        probe_scale = max(probe_scale, probe.matrix_world.to_scale().x)
    chest_scale = max(pb["chest"].scale.z, 1.0)
    print(f"max sax scale error {worst:.2e}; chest scale up to {chest_scale:.3f}; bone-parented probe {probe_scale:.3f}")
    assert chest_scale > 1.005, "Breathing did not scale the bone, so this test proves nothing"
    assert probe_scale > 1.005, "bone parenting should scale (the reason for Child Of)"
    assert worst < 1e-4, worst
    print(f"max hand-to-target gap while breathing: {gap * 1000:.3f} mm")
    assert gap < 0.001, gap         # the upper arms don't inherit the chest's scale while locked
    assert arm.data.bones["upper_arm.L"].inherit_scale == "NONE"
    bpy.data.objects.remove(probe)

    # Unlock keeps the arms from inheriting the ribcage's swell while Breathing is on
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    for side in "LR":
        assert arm.data.bones[f"upper_arm.{side}"].inherit_scale == "NONE"
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}

    # Idempotent re-lock; unlock cleans up
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    n_con = sum(1 for b in pb for c in b.constraints if c.name.startswith("MIDI Hold"))
    assert n_con == 4, n_con
    assert sum(1 for c in sax.constraints if c.name == "MIDI Hold Strap") == 1
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    assert not any(c.name.startswith("MIDI Hold") for b in pb for c in b.constraints)
    assert "MIDI Hold L" not in bpy.data.objects and "MIDI Hold R" not in bpy.data.objects
    for side in "LR":
        b = arm.data.bones[f"upper_arm.{side}"]
        assert "midianim_inherit_scale" not in b
        assert b.inherit_scale == "NONE", "Breathing is on: the arm keeps ignoring the ribcage's scale"
    assert bpy.ops.midianim.breathing_remove() == {"FINISHED"}
    for side in "LR":
        b = arm.data.bones[f"upper_arm.{side}"]
        assert b.inherit_scale == "FULL" and "midianim_breath_inherit" not in b, "inherit scale not restored"
    assert bpy.ops.midianim.breathing_add() == {"FINISHED"}       # on again for the rest of the test
    # Missing bones give a clean error, not a traceback
    s.hold_hand_r = "nope"
    try:
        bpy.ops.midianim.lock_hands()
        raise AssertionError("lock with a missing bone should fail")
    except RuntimeError as e:
        assert "not found" in str(e), e
    s.hold_hand_r = "hand.R"


def clarinet_checks(scene, s, arm):
    """Switch to the B-flat clarinet profile and run the same pipeline on it."""
    assert s.transpose == 0 and s.profile == "MONO_WIND", (s.transpose, s.profile)

    # 0. Switching keeps each finger slot as it is (same slot ids), only the labels follow.
    # The probe stands for any per-finger setting: rebuilding the list would drop it.
    def finger(slot):
        return next(f for f in s.fingers if f.slot == slot)

    finger("L2").up_pose = bpy.data.actions["F.L2.A.Up"]
    finger("L2")["midianim_probe"] = 1
    bones_before = rig.finger_bones(s)
    s.profile = "CLARINET_BB"
    assert s.get("profile") == 1, s.get("profile")          # the number saved in the scene
    assert finger("LT").label == "L Thumb (register)", finger("LT").label
    s.profile = "MONO_WIND"
    assert s.get("profile") == 0, s.get("profile")
    assert finger("LT").label == "L Thumb (octave)", finger("LT").label
    assert rig.finger_bones(s) == bones_before
    assert finger("L2").up_pose == bpy.data.actions["F.L2.A.Up"]
    assert finger("L2").get("midianim_probe") == 1, "finger slots were rebuilt on switching"
    del finger("L2")["midianim_probe"]
    finger("L2").up_pose = None

    # 1. Default Transpose follows the instrument unless the user changed it
    s.profile = "CLARINET_BB"
    assert s.transpose == 2, s.transpose
    s.profile = "MONO_WIND"
    assert s.transpose == 0, s.transpose
    s.transpose = 5
    s.profile = "CLARINET_BB"
    assert s.transpose == 5, s.transpose
    s.profile = "MONO_WIND"
    assert s.transpose == 5, s.transpose
    s.transpose = 0
    s.profile = "CLARINET_BB"
    assert s.transpose == 2, s.transpose

    # 2. Finger slots follow the profile and keep their bones
    assert s.fingers[0].label == "L Thumb (register)", s.fingers[0].label
    bones = rig.finger_bones(s)
    assert bones["L1"] == ["f_index.01.L", "f_index.02.L", "f_index.03.L"], bones
    assert len(bones) == 9, bones

    # 3. Markers + Autoassign
    place_markers(s, arm)
    markers = rig.find_markers()
    s.force_autoassign = True
    try:
        _, _, problems, _ = autoassign.autoassign(bpy.context, s)
    finally:
        s.force_autoassign = False
    assert problems == [], problems
    for name in ("F.LT.Register.Down", "F.LT.RegOnly.Up", "F.L1.A.Down", "F.L4.E/B.Down",
                 "F.L4.C#/G#.Down", "F.R1.Eb/Bb.Down", "F.R4.Ab/Eb.Up"):
        a = bpy.data.actions.get(name)
        assert a is not None and a.asset_data is not None, name
    against, locked, worst_tip = bend_checks(s, arm, markers)
    print(f"clarinet bend: against {against:.3f} deg, locked axes {locked:.3f} deg, "
          f"tip {worst_tip * 1000:.2f} mm")
    assert against < 1.0 and locked < 1.0 and worst_tip < 0.004, (against, locked, worst_tip)
    rest = actions.pose_values(bpy.data.actions["F.Rest"])
    home_up = actions.pose_values(bpy.data.actions["F.L4.E/B.Up"])
    assert home_up and all(abs(rest[k] - v) < 1e-5 for k, v in home_up.items())

    # 4. Whole chart
    s.notes.clear()
    assert bpy.ops.midianim.fill_from_chart(which="ALL") == {"FINISHED"}
    assert [r.pitch for r in s.notes] == list(range(52, 85)), [r.pitch for r in s.notes]
    holes = {k: "Hole" for k in ("L1", "L2", "L3", "R1", "R2", "R3")}
    b4 = state.find_note(s, parse_note_name("B4"))
    assert state.parse_combination(b4.combination) == {**holes, "LT": "Register", "L4": "E/B"}, b4.combination
    as4 = state.find_note(s, parse_note_name("A#4"))
    assert state.parse_combination(as4.combination) == {"LT": "RegOnly", "L1": "A"}, as4.combination
    g4 = state.find_note(s, parse_note_name("G4"))
    assert state.parse_combination(g4.combination) == {}, g4.combination

    # 5. The sample file: E6 (88) is above the clarinet chart
    s.notes.clear()
    assert bpy.ops.midianim.fill_from_chart(which="FILE") == {"FINISHED"}
    pitches = [r.pitch for r in s.notes]
    assert len(pitches) == 13 and 88 not in pitches, pitches
    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    lines = [line.text for line in s.report if line.text.startswith("Unmapped notes")]
    assert lines == ["Unmapped notes: E6"], lines

    # 6. Bake
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert "MIDI: Fingering" in [t.name for t in arm.animation_data.nla_tracks]

    def check(frame, pose, bone_set=None):
        scene.frame_set(frame)
        for (path, idx), v in actions.pose_values(bpy.data.actions[pose], bone_set).items():
            owner, prop = path.rsplit(".", 1)
            got = getattr(arm.path_resolve(owner), prop)[idx]
            assert abs(got - v) < 1e-3, (pose, path, idx, got, v)

    check(int(1 + 2.1 * 24), "F.L1.A.Down", set(rig.finger_bones(s)["L1"]))
    check(int(1 + 2.7 * 24), "F.LT.Register.Down", set(rig.finger_bones(s)["LT"]))
    print("clarinet checks passed")


def two_finger_checks():
    """Step 11: a two-finger hand (CJ-style numbered bones, no thumb). Detect Fingers proposes the
    sharing (finger 1 = index, finger 2 = middle + ring + pinky) and the thumb as the hand's tilt;
    the proposal survives both sync paths; shared slots autoassign onto their own markers with the
    shared chain and bake with "pressing wins"; the tilt bakes on the hand, and on the hold target
    while Lock is on."""
    scene, arm, sax, _ = build_scene(FINGERS2, cj_name)
    s = scene.midi_animator
    s.midi_path, s.rig, s.instrument = MID, arm, sax
    pb = arm.pose.bones

    def finger(slot):
        return next(f for f in s.fingers if f.slot == slot)

    # 1. Detect: numbered names, sharing and the thumb tilt proposed
    s.bend_axis = "X"
    assert bpy.ops.midianim.detect_fingers() == {"FINISHED"}
    assert s.bend_axis == "-X", s.bend_axis
    bones = rig.finger_bones(s)
    assert bones["L1"] == ["arm left finger 1a_044", "arm left finger 1b_045", "arm left finger 1c_046"], bones
    assert bones["L3"] is bones["L2"] and bones["L4"] is bones["L2"] and bones["R4"] is bones["R2"], bones
    assert finger("L3").shares == "L2" and finger("L4").shares == "L2" and finger("R3").shares == "R2"
    assert finger("L1").shares == "" and len(finger("L3").bones) == 0
    assert bones["LT"] == ["hand.L"] and finger("LT").tilt == 3.0 and finger("LT").shares == ""
    assert rig.share_groups(s) == {"LT": ["LT"], "L1": ["L1"], "L2": ["L2", "L3", "L4"],
                                   "R1": ["R1"], "R2": ["R2", "R3", "R4"]}, rig.share_groups(s)
    assert rig.tilt_slots(s) == {"LT"}

    # 2. Both sync paths keep the new fields: relabel (same ids) and rebuild (ids changed)
    s.profile = "CLARINET_BB"
    assert finger("L3").shares == "L2" and finger("LT").tilt == 3.0 and finger("LT").label.endswith("(register)")
    s.profile = "MONO_WIND"
    finger("LT").tilt = 4.5
    s.fingers.remove(1)                                    # drop L1: the ids no longer match
    rig.sync_finger_slots(s)
    assert [f.slot for f in s.fingers] == ["LT", "L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"]
    assert finger("L3").shares == "L2" and finger("L4").shares == "L2", "shares lost on rebuild"
    assert finger("LT").tilt == 4.5 and [b.bone for b in finger("LT").bones] == ["hand.L"], "tilt lost on rebuild"
    assert len(finger("L1").bones) == 0
    assert bpy.ops.midianim.detect_fingers() == {"FINISHED"}
    assert finger("LT").tilt == 4.5, "Detect must keep a tilt the user set"
    finger("LT").tilt = 3.0

    # 3. Markers for every slot that has a chain (shared ones included), none for the tilt slot
    place_markers(s, arm)
    markers = rig.find_markers()
    assert ("L3", "G") in markers and ("L4", "LowC#") in markers and not any(sl == "LT" for sl, _ in markers)
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
    for name in ("F.L2.A.Down", "F.L3.G.Down", "F.L3.G.Up", "F.L4.LowC#.Down", "F.R4.LowC.Up",
                 "F.LT.Octave.Down", "F.LT.Octave.Up", "F.Rest"):
        assert name in bpy.data.actions, name
    l2 = set(bones["L2"])
    assert {actions.bone_of(p) for p, _ in actions.pose_values(bpy.data.actions["F.L3.G.Down"])} == l2
    bpy.ops.midianim.apply_pose(action="F.L3.G.Down")
    d = (tip_world(arm, bones["L2"][-1]) - markers[("L3", "G")].matrix_world.translation).length
    bpy.ops.midianim.apply_pose(action="F.L2.A.Down")
    d2 = (tip_world(arm, bones["L2"][-1]) - markers[("L2", "A")].matrix_world.translation).length
    print(f"shared chain tip distance: on L3's key {d * 1000:.2f} mm, on L2's key {d2 * 1000:.2f} mm")
    assert d < 0.004 and d2 < 0.004, (d, d2)
    against, locked, worst_tip = bend_checks(s, arm, markers, {"L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4"})
    assert against < 1.0 and locked < 1.0 and worst_tip < 0.004, (against, locked, worst_tip)
    # The tilt poses: rotation channels of the hand only; Down is Up turned 3 deg around the bend axis (-X)
    up = actions.pose_values(bpy.data.actions["F.LT.Octave.Up"])
    down = actions.pose_values(bpy.data.actions["F.LT.Octave.Down"])
    assert set(up) == set(down) == {('pose.bones["hand.L"].rotation_quaternion', i) for i in range(4)}, up
    q_up = Quaternion([up[('pose.bones["hand.L"].rotation_quaternion', i)] for i in range(4)])
    q_down = Quaternion([down[('pose.bones["hand.L"].rotation_quaternion', i)] for i in range(4)])
    rel = q_up.inverted() @ q_down
    assert abs(math.degrees(rel.angle) - 3.0) < 1e-3, math.degrees(rel.angle)
    assert (rel.axis - Vector((-1, 0, 0))).length < 1e-4, tuple(rel.axis)
    # F.Rest: each chain once (over the first listed slot's home key), the hand's rotation, the other hand
    rest_bones = {actions.bone_of(p) for p, _ in actions.pose_values(bpy.data.actions["F.Rest"])}
    assert rest_bones == set(bones["L1"]) | l2 | set(bones["R1"]) | set(bones["R2"]) | {"hand.L", "hand.R"}, rest_bones
    rest = actions.pose_values(bpy.data.actions["F.Rest"])
    for k, v in actions.pose_values(bpy.data.actions["F.L2.A.Up"]).items():
        assert abs(rest[k] - v) < 1e-5
    assert "forearm.L" not in rest_bones          # the tilt slot's parent is not a "hand bone"

    # 4. A slot with no bones is skipped silently by Autoassign and listed once by Analyze
    finger("R4").shares = ""
    assert "R4" not in rig.finger_bones(s)
    _, _, problems, _ = autoassign.autoassign(bpy.context, s)
    assert problems == [], problems
    assert bpy.ops.midianim.fill_from_chart(which="FILE") == {"FINISHED"}
    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    lines = [line.text for line in s.report]
    assert "Not animated (no bones): R Pinky" in lines, lines
    assert not any(line.startswith("Keys without a marker") for line in lines), lines    # LT needs none
    finger("R4").shares = "R2"
    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    assert not any(line.text.startswith("Not animated") for line in s.report), [line.text for line in s.report]

    # 5. Bake: pressing wins. G4 (1.8-2.4 s) is remapped to L1 + L3 only, so the shared chain goes to
    # L3's marker; A4 (2.4-3.0 s, L1 L2) puts it on L2's; D5 (4.2-5.4 s) adds the octave key: the
    # hand tilts; C#5 (3.6-4.2 s) is open: the hand is back.
    state.find_note(s, parse_note_name("G4")).combination = "L1=B;L3=G"
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert "MIDI: Fingering" in [t.name for t in arm.animation_data.nla_tracks]

    def check(frame, pose, bone_set):
        scene.frame_set(frame)
        vals = actions.pose_values(bpy.data.actions[pose], bone_set)
        assert vals, pose
        for (path, idx), v in vals.items():
            owner, prop = path.rsplit(".", 1)
            got = getattr(arm.path_resolve(owner), prop)[idx]
            assert abs(got - v) < 1e-3, (frame, pose, path, idx, got, v)

    fps = 24
    check(int(1 + 2.1 * fps), "F.L3.G.Down", l2)
    check(int(1 + 2.7 * fps), "F.L2.A.Down", l2)
    check(int(1 + 4.8 * fps), "F.LT.Octave.Down", {"hand.L"})
    check(int(1 + 3.9 * fps), "F.LT.Octave.Up", {"hand.L"})
    # the rest between phrases (5.4-6.6 s): the chain is up over the key it left last (D5: L2's A)
    check(int(1 + 6.0 * fps), "F.Rest", l2)

    # 6. Lock on: the hand's rotation comes from the hold target, so the tilt is baked there too
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    assert (s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r) == ("chest", "hand.L", "hand.R")
    scene.frame_set(1)
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    tgt = bpy.data.objects["MIDI Hold L"]
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert [t.name for t in tgt.animation_data.nla_tracks] == ["MIDI: Fingering"], \
        [t.name for t in tgt.animation_data.nla_tracks]

    def hand_rot(frame):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        return (arm.matrix_world @ pb["hand.L"].matrix).to_3x3(), (arm.matrix_world @ pb["hand.L"].head).copy()

    m_up, head_up = hand_rot(int(1 + 3.9 * fps))
    m_down, head_down = hand_rot(int(1 + 4.8 * fps))
    rel = (m_up.inverted() @ m_down).to_quaternion()
    print(f"locked thumb tilt: {math.degrees(rel.angle):.3f} deg around {tuple(round(v, 3) for v in rel.axis)}, "
          f"hand moved {(head_down - head_up).length * 1000:.3f} mm")
    assert abs(math.degrees(rel.angle) - 3.0) < 0.05, math.degrees(rel.angle)
    assert (rel.axis - Vector((-1, 0, 0))).length < 1e-2, tuple(rel.axis)       # the hand's own X
    assert (head_down - head_up).length < 1e-3, "the wrist left its hold target"
    assert (head_up - tgt.matrix_world.translation).length < 1e-3
    # Re-bake replaces the target's track; Clear removes it
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert [t.name for t in tgt.animation_data.nla_tracks] == ["MIDI: Fingering"]
    assert bpy.ops.midianim.clear() == {"FINISHED"}
    assert not tgt.animation_data.nla_tracks
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    print("two-finger checks passed")


def build_cj_scene(sideways_spine=False, clavicles=False):
    """A rig like CJ's FBX import (step 6, P1): hands named wrist, a spine lower/middle/upper
    chain, and arm bones whose tails sit beside the limb instead of on the next joint. A skinned
    strip of points along each arm checks that the mesh never moves. The instrument is an empty
    with a long box mesh (the clarinet's tube) whose local +Y is the key side."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    arm_data = bpy.data.armatures.new("Object_3")
    arm = bpy.data.objects.new("Object_3", arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    prev = None
    # sideways_spine: the original FBX rig, whose spine bones point along +X / -X and are rolled
    for name, z, tail, roll in (("spine lower_011", 1.0, (0.15, 0, 0), 0.0), ("spine middle_012", 1.15, (-0.15, 0, 0), 0.7),
                                ("spine upper_013", 1.3, (-0.2, 0, 0), -0.4)):
        b = eb.new(name)
        b.head, b.parent = (0, 0, z), prev
        b.tail = (tail[0], 0, z + tail[2]) if sideways_spine else (0, 0, z + 0.15)
        if sideways_spine:
            b.roll = roll
        prev = b
    chest = prev
    joints = {}
    for side, sx in (("left", 1), ("right", -1)):
        sh, el, wr = Vector((0.2 * sx, 0, 1.4)), Vector((0.5 * sx, -0.05, 1.2)), Vector((0.45 * sx, -0.4, 1.25))
        up = eb.new(f"arm {side} shoulder 2_039")
        up.head, up.tail, up.parent = sh, sh + Vector((0.1 * sx, 0.25, 0.1)), chest     # off the elbow
        if clavicles:        # CJ's "shoulder 1": the bone between the ribcage and the upper arm
            cl = eb.new(f"arm {side} shoulder 1_038")
            cl.head, cl.tail, cl.parent = Vector((0.05 * sx, 0, 1.45)), sh, chest
            up.parent = cl
        fo = eb.new(f"arm {side} elbow_040")
        fo.head, fo.tail, fo.parent = el, el + Vector((0.3 * sx, 0.05, -0.25)), up      # 39 cm off the wrist
        hand = eb.new(f"arm {side} wrist_041")
        hand.head, hand.tail, hand.parent = wr, wr + Vector((0, -0.1, 0)), fo
        for i in range(1, 4):
            f = eb.new(f"f_index.0{i}.{'L' if sx > 0 else 'R'}")
            f.head = hand.tail + Vector((0, -0.03 * (i - 1), 0))
            f.tail = f.head + Vector((0, -0.03, 0))
            f.parent = hand if i == 1 else eb[f"f_index.0{i - 1}.{'L' if sx > 0 else 'R'}"]
        joints[side] = (sh, el, wr)
    bpy.ops.object.mode_set(mode="OBJECT")

    # skin: points along each limb, weighted to the bone (half-half at the joints)
    verts, groups = [], []
    for side, (sh, el, wr) in joints.items():
        for a, b, bone_a, bone_b in ((sh, el, f"arm {side} shoulder 2_039", f"arm {side} elbow_040"),
                                     (el, wr, f"arm {side} elbow_040", f"arm {side} wrist_041")):
            for t in (0.0, 0.25, 0.5, 0.75, 1.0):
                verts.append(a.lerp(b, t) + Vector((0, 0, 0.03)))
                groups.append({bone_a: 1.0} if t < 1.0 else {bone_a: 0.5, bone_b: 0.5})
    mesh = bpy.data.meshes.new("Skin")
    mesh.from_pydata([tuple(v) for v in verts], [], [])
    skin = bpy.data.objects.new("Skin", mesh)
    scene.collection.objects.link(skin)
    skin.parent = arm
    for i, g in enumerate(groups):
        for bone, w in g.items():
            vg = skin.vertex_groups.get(bone) or skin.vertex_groups.new(name=bone)
            vg.add([i], w, "REPLACE")
    skin.modifiers.new("Armature", "ARMATURE").object = arm

    # the arms posed (not the rest pose), so the fix has a real deformation to keep
    for side, sx in (("left", 1), ("right", -1)):
        pb = arm.pose.bones
        pb[f"arm {side} shoulder 2_039"].rotation_quaternion = Quaternion((1, 0, 0), math.radians(25 * sx))
        pb[f"arm {side} elbow_040"].rotation_quaternion = Quaternion((0, 0, 1), math.radians(-40 * sx))
        pb[f"arm {side} wrist_041"].rotation_quaternion = Quaternion((0, 1, 0), math.radians(15))

    inst = bpy.data.objects.new("Clarinet", None)
    scene.collection.objects.link(inst)
    inst.location = (0, -0.3, 1.1)
    tube_mesh = bpy.data.meshes.new("Tube")
    tube_mesh.from_pydata([(x, y, z) for x in (-0.02, 0.02) for y in (-0.02, 0.02) for z in (-0.3, 0.3)], [], [])
    tube = bpy.data.objects.new("Tube", tube_mesh)
    scene.collection.objects.link(tube)
    tube.parent = inst
    bpy.context.view_layer.update()
    return scene, arm, skin, inst, tube


def offjoint_and_front_checks():
    """Step 7a: Lock on a rig whose arm tails sit off the joints (P1) moves nothing; Guess Bones
    finds wrists and the upper chest (P2); the instrument's front is set from the view or the
    markers, checked before Lock, and turned forward about the tube (P10)."""
    from midi_animator.blender import hold
    scene, arm, skin, inst, tube = build_cj_scene()
    s = scene.midi_animator
    s.rig, s.instrument = arm, inst
    pb = arm.pose.bones

    def skin_points():
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        e = skin.evaluated_get(dg)
        m = e.to_mesh()
        pts = [e.matrix_world @ v.co for v in m.vertices]
        e.to_mesh_clear()
        return pts

    def world(bone):
        bpy.context.view_layer.update()
        return (arm.matrix_world @ pb[bone].head).copy()

    # P2: wrists and the upper chest
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    assert (s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r) == \
        ("spine upper_013", "arm left wrist_041", "arm right wrist_041"), (s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r)

    # P1: the four arm bones are off their joints
    bad = hold.off_joint_bones(s)
    assert sorted(n for n, _, _ in bad) == sorted(f"arm {sd} {b}" for sd in ("left", "right")
                                                  for b in ("shoulder 2_039", "elbow_040")), bad
    fore_off = next(d for n, _, d in bad if n == "arm left elbow_040")
    assert fore_off > 0.3, fore_off
    # a hidden rig can't be edited: Lock says so instead of failing half way
    arm.hide_set(True)
    assert "hidden" in hold.check(s), hold.check(s)
    arm.hide_set(False)

    # P10: the instrument's key side (+Y) faces the player (+Y world): Lock refuses
    s.hold_front = "+Y"
    angle, verdict = hold.front_status(s)
    assert verdict == "player" and abs(angle - 180) < 1e-3, (angle, verdict)
    assert "faces the player" in hold.check(s)
    try:
        bpy.ops.midianim.lock_hands()
        raise AssertionError("Lock with the front toward the player should fail")
    except RuntimeError as e:
        assert "faces the player" in str(e), e
    # From View: looking at the instrument from the back (viewer on +Y) names +Y; from the front, -Y
    class View:
        def __init__(self, from_dir):
            self.view_rotation = Vector(from_dir).to_track_quat("Z", "Y")
    assert hold.set_front_from_view(s, View((0, 1, 0)))[0] == "+Y"
    assert hold.set_front_from_view(s, View((0.2, -1, 0.1)))[0] == "-Y"
    s.hold_front = "+Y"
    # Turn Front Forward: rolls about the tube's length, so the tube's centre line stays
    ends_before = [tube.matrix_world @ Vector((0, 0, z)) for z in (-0.3, 0.3)]
    marker = bpy.data.objects.new("Key.L1.B", None)
    marker["midianim_slot"], marker["midianim_key"] = "L1", "B"
    scene.collection.objects.link(marker)
    marker.parent = inst
    marker.matrix_world = inst.matrix_world @ Matrix.Translation((0, 0.02, 0.1)) @ Vector((0, 1, 0)).to_track_quat("Z", "Y").to_matrix().to_4x4()
    deg = hold.turn_front_forward(bpy.context, s)
    angle, verdict = hold.front_status(s)
    print(f"front: turned {deg:.1f} deg, now {angle:.2f} deg from forward ({verdict})")
    assert abs(abs(deg) - 180) < 0.5 and verdict == "forward" and angle < 0.5, (deg, angle, verdict)
    ends_after = [tube.matrix_world @ Vector((0, 0, z)) for z in (-0.3, 0.3)]
    assert max((a - b).length for a, b in zip(ends_before, ends_after)) < 1e-4, "the tube's centre line moved"
    # the marker turned with it: its arrow now points forward, and From Markers reads +Y back
    assert (marker.matrix_world.to_3x3().col[2].normalized() - Vector((0, -1, 0))).length < 1e-3
    s.hold_front = "NONE"
    assert hold.set_front_from_markers(s)[0] == "+Y"
    assert hold.check(s) == "", hold.check(s)

    # Lock: the hands and the skin stay (0 mm), the tails now sit on the joints
    before_skin = skin_points()
    before = {b: world(b) for b in ("arm left wrist_041", "arm right wrist_041", "arm left elbow_040", "arm right elbow_040")}
    msg = hold.lock_hands(bpy.context, s)
    assert "Moved 4 arm bone tails" in msg, msg
    jump = max((world(b) - p).length for b, p in before.items())
    skin_move = max((a - b).length for a, b in zip(before_skin, skin_points()))
    print(f"off-joint rig: Lock moved the hands and elbows {jump * 1000:.4f} mm, the skin {skin_move * 1000:.4f} mm")
    assert jump < 1e-5 and skin_move < 1e-5, (jump, skin_move)
    assert hold.off_joint_bones(s) == []
    for side in ("left", "right"):
        fo, wr = arm.data.bones[f"arm {side} elbow_040"], arm.data.bones[f"arm {side} wrist_041"]
        assert (fo.tail_local - wr.head_local).length < 1e-6
    # the hands follow the instrument now (the forearm's tail is the wrist)
    inst.location.x += 0.05
    bpy.context.view_layer.update()
    tgt = bpy.data.objects["MIDI Hold L"]
    assert (world("arm left wrist_041") - tgt.matrix_world.translation).length < 1e-3
    inst.location.x -= 0.05
    # a second Lock has nothing to fix and moves nothing
    msg = hold.lock_hands(bpy.context, s)
    assert "Moved" not in msg
    assert max((world(b) - p).length for b, p in before.items()) < 1e-5
    # turning the instrument while locked is refused
    try:
        hold.turn_front_forward(bpy.context, s)
        raise AssertionError("turn while locked should fail")
    except RuntimeError as e:
        assert "Unlock" in str(e), e
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    print("off-joint rig and front checks passed")


class _Recorder:
    """A stand-in for a panel layout: records the properties and operators the panel draws."""
    def __init__(self, log):
        self.log = log

    def __getattr__(self, name):
        def call(*args, **kw):
            if name == "prop":
                self.log.append(("prop", args[1]))
            elif name == "operator":
                self.log.append(("operator", args[0]))
            return _Recorder(self.log)
        return call


def breathing_panel_checks(s):
    """The Breathing box offers Add Breathing; once set up, the five sliders and the remove button."""
    from midi_animator.blender import ui
    log = []
    ui.MIDIANIM_PT_blow.draw_breathing(_Recorder(log), s)
    shown = [x for k, x in log if k == "operator"]
    assert shown == ["midianim.breathing_add", "midianim.breathing_remove"] if breathing.is_set_up(s) else         shown == ["midianim.breathing_add"], (shown, breathing.is_set_up(s))
    for kind, name in log:
        if kind == "prop":
            assert hasattr(s, name), name
        else:
            mod, op = name.split(".")
            assert hasattr(getattr(bpy.ops, mod), op), name
    props = [x for k, x in log if k == "prop"]
    assert props == (["breath_intensity", "breath_chest", "breath_belly", "breath_shoulders", "breath_torso"]
                     if breathing.is_set_up(s) else []), props


def breathing_checks(sideways_spine):
    """Step 7b on a CJ-style rig: the right axes whatever the spine bones' orientation, the head and arms
    keep their size, the hands stay on their targets, and every slider works live (no re-bake)."""
    from midi_animator.blender import hold
    scene, arm, skin, inst, tube = build_cj_scene(sideways_spine, clavicles=True)
    s = scene.midi_animator
    s.rig, s.instrument = arm, inst
    s.midi_path = MID
    pb = arm.pose.bones
    ribs, middle, lower = "spine upper_013", "spine middle_012", "spine lower_011"
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    assert bpy.ops.midianim.breathing_add() == {"FINISHED"}
    print("breathing on", "sideways" if sideways_spine else "upright", "spine:", arm["midianim_breath"][:60], "...")

    def settle():
        bpy.context.view_layer.update()

    def full_scale(name):
        return (arm.matrix_world @ pb[name].matrix).to_scale()

    def world_axis(name, i):
        return (arm.matrix_world.to_3x3() @ pb[name].matrix.to_3x3()).col[i].normalized()

    def set_lung(v):
        arm["breath_lung"] = v
        arm.update_tag()                    # a custom property set from a script doesn't wake the drivers itself
        settle()

    def err():
        return max((bpy.data.objects[f"MIDI Hold {sd}"].matrix_world.translation
                    - arm.matrix_world @ pb[b].matrix.translation).length
                   for sd, b in (("L", s.hold_hand_l), ("R", s.hold_hand_r)))

    set_lung(0.0)
    for name in (ribs, middle, lower):
        assert max(abs(v - 1.0) for v in pb[name].scale) < 1e-9, "empty lungs: still"
    set_lung(1.0)
    # which axes grew: the ribcage's depth axis points front-back (world Y), its width axis side to side (X)
    grown = [i for i in range(3) if pb[ribs].scale[i] > 1.001]
    assert len(grown) == 2, tuple(pb[ribs].scale)
    by_amount = sorted(grown, key=lambda i: -pb[ribs].scale[i])
    depth, width = by_amount
    assert abs(pb[ribs].scale[depth] - 1.10) < 1e-6 and abs(pb[ribs].scale[width] - 1.04) < 1e-6
    aligned = 0.9 if sideways_spine else 0.99          # the sideways rig's bones are rolled up to 23 degrees
    assert abs(world_axis(ribs, depth).y) > aligned, world_axis(ribs, depth)
    assert abs(world_axis(ribs, width).x) > aligned, world_axis(ribs, width)
    bdepth = max(range(3), key=lambda i: pb[lower].scale[i])
    assert abs(pb[lower].scale[bdepth] - 1.06) < 1e-6 and abs(world_axis(lower, bdepth).y) > aligned
    # nothing above the chest grows: the arms (and with them anything under them), at every sampled lung
    arm_bones = [b.name for b in arm.data.bones if b.name not in (ribs, middle, lower)]
    worst, worst_hand = 0.0, 0.0
    for lung in (0.0, 0.3, 0.7, 1.0):
        set_lung(lung)
        for n in arm_bones:
            worst = max(worst, max(abs(v - 1.0) for v in full_scale(n)))
        worst_hand = max(worst_hand, err())
    print(f"  head/arm scale error {worst:.2e}, hand-to-target {worst_hand * 1000:.4f} mm")
    assert worst < 1e-4, worst
    assert worst_hand < 1e-3, worst_hand

    # each part moves the right way: full minus empty lungs, one slider at a time (world space, metres)
    def snapshot(lung):
        set_lung(lung)
        return {n: (arm.matrix_world @ pb[n].head).copy() for n in
                ("arm left shoulder 2_039", "arm right shoulder 2_039", ribs)} |             {"ribs_tail": (arm.matrix_world @ pb[ribs].tail).copy()}

    def only(part):
        for p in breathing.PARTS:
            setattr(s, f"breath_{p}", 1.0 if p == part else 0.0)
        settle()
    only("shoulders")
    empty, full = snapshot(0.0), snapshot(1.0)
    rise = (full["arm left shoulder 2_039"] - empty["arm left shoulder 2_039"]).z
    assert rise > 0.001, f"shoulders did not rise: {rise}"
    only("torso")
    empty, full = snapshot(0.0), snapshot(1.0)
    back = (full["ribs_tail"] - empty["ribs_tail"]).y          # the character faces -Y: back is +Y
    assert back > 0.005, f"torso did not lean back: {back}"
    only("chest")
    empty, full = snapshot(0.0), snapshot(1.0)
    assert (full[ribs] - empty[ribs]).length < 1e-6          # the ribcage swells about its own head: no lean
    for p in breathing.PARTS:
        setattr(s, f"breath_{p}", 1.0)

    # the sliders are live: the update callback alone wakes the rig; master 0 / 1 / 2 = still / default / double
    set_lung(1.0)
    rest_z = []
    for master in (0.0, 1.0, 2.0):
        s.breath_intensity = master
        settle()
        rest_z.append(pb[ribs].scale[depth] - 1.0)
    assert abs(rest_z[0]) < 1e-9 and abs(rest_z[1] - 0.10) < 1e-6 and abs(rest_z[2] - 0.20) < 1e-6, rest_z
    s.breath_intensity = 1.0
    s.breath_chest = 3.0
    settle()
    assert abs(pb[ribs].scale[depth] - 1.30) < 1e-6
    s.breath_chest = 0.0
    settle()
    assert abs(pb[ribs].scale[depth] - 1.0) < 1e-9 and abs(pb[lower].scale[bdepth] - 1.06) < 1e-6
    s.breath_chest = 1.0
    assert err() < 1e-3

    # remove: back to the plain rig
    assert bpy.ops.midianim.breathing_remove() == {"FINISHED"}
    assert not any(d for d in (arm.animation_data.drivers if arm.animation_data else []))
    assert max(abs(v - 1.0) for v in pb[ribs].scale) < 1e-9 and "breath_lung" not in arm
    assert not any(e.name == "Breathing" for e in s.effects)
    bpy.ops.midianim.unlock_hands()


def old_chest_checks():
    """A file made before 7b has the old Chest effect (Lung mode, bone, Scale X+Z). Add Breathing turns
    it off (settings kept), Bake animates the spine only through Breathing, and Bake warns if the old
    effect is switched on again."""
    scene, arm, skin, inst, tube = build_cj_scene(False, clavicles=True)
    s = scene.midi_animator
    s.rig, s.instrument, s.midi_path = arm, inst, MID
    s.fingering_enabled = False
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    e = s.effects.add()
    e.name, e.target_type, e.target, e.bone = "Chest", "BONE", arm, "spine lower_011"
    e.channel, e.mode, e.out_max, e.blend_type = "SCALE_XZ", "LUNG", 0.04, "COMBINE"
    e.attack, e.release = 0.15, 0.4
    assert bpy.ops.midianim.breathing_add() == {"FINISHED"}
    chest = next(x for x in s.effects if x.name == "Chest")
    assert not chest.enabled and abs(chest.out_max - 0.04) < 1e-6 and chest.bone == "spine lower_011"
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    tracks = [t.name for t in arm.animation_data.nla_tracks]
    assert tracks == ["MIDI: Breathing"], tracks
    for f in (1, 30, 60, 90):
        scene.frame_set(f)
        low = arm.pose.bones["spine lower_011"]
        lung = arm["breath_lung"]
        assert abs(low.scale.y - 1.0) < 1e-6, tuple(low.scale)             # the old effect's Y (up) channel
        assert abs(low.scale.z - (1 + 0.06 * lung)) < 1e-4, (tuple(low.scale), lung)      # Breathing's belly only
    chest.enabled = True                                        # switched on again by hand: Bake warns
    msgs, warnings = bake.bake_all(bpy.context)
    assert any("Chest" in w and "second time" in w for w in warnings), warnings
    chest.enabled = False
    assert bpy.ops.midianim.breathing_remove() == {"FINISHED"}
    assert chest.enabled, "Remove gives the old effect back"
    print("old Chest effect checks passed")


def main():
    midi_animator.register()
    scene, arm, sax, face = build_scene()
    s = scene.midi_animator
    s.midi_path = MID
    s.rig = arm
    s.instrument = sax
    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    assert any("Unmapped" in line.text for line in s.report)

    # Fingers (Detect Fingers also reads the bend axis from the rest curl)
    s.bend_axis = "X"
    assert bpy.ops.midianim.detect_fingers() == {"FINISHED"}
    assert s.bend_axis == "-X", s.bend_axis
    s.bend_axis = "Z"
    assert bpy.ops.midianim.detect_bend_axis() == {"FINISHED"} and s.bend_axis == "-X"
    bones = rig.finger_bones(s)
    assert bones["L1"] == ["f_index.01.L", "f_index.02.L", "f_index.03.L"], bones
    assert bones["LT"][0] == "thumb.01.L" and len(bones) == 9

    # Markers + autoassign
    place_markers(s, arm)
    markers = rig.find_markers()
    assert markers[("L1", "B")].parent == sax
    rest_rot = tuple(arm.pose.bones["f_index.01.L"].rotation_quaternion)
    ik_before = {a: getattr(arm.pose.bones["f_index.02.L"], a) for a in autoassign._IK_ATTRS}
    assert s.rest_pose is None
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
    ik_after = {a: getattr(arm.pose.bones["f_index.02.L"], a) for a in autoassign._IK_ATTRS}
    assert ik_after == ik_before, "bone IK settings not restored"
    down = bpy.data.actions.get("F.L1.B.Down")
    up = bpy.data.actions.get("F.L1.B.Up")
    assert down is not None and down.asset_data is not None and up is not None
    assert tuple(arm.pose.bones["f_index.01.L"].rotation_quaternion) == rest_rot, "rig not restored"
    # The Down pose puts the fingertip on the marker; Up hovers above it
    bpy.ops.midianim.apply_pose(action="F.L1.B.Down")
    d_down = (tip_world(arm, "f_index.03.L") - markers[("L1", "B")].matrix_world.translation).length
    bpy.ops.midianim.apply_pose(action="F.L1.B.Up")
    d_up = (tip_world(arm, "f_index.03.L") - markers[("L1", "B")].matrix_world.translation).length
    print(f"tip distance: down {d_down:.4f}, up {d_up:.4f}")
    assert d_down < 0.004, d_down
    assert d_up > d_down + 0.005, (d_up, d_down)

    # Bend direction: no joint twists, turns sideways (beyond the knuckle) or bends backwards
    against, locked, worst_tip = bend_checks(s, arm, markers)
    print(f"bend: max against the axis {against:.3f} deg, max on locked axes {locked:.3f} deg, "
          f"max tip-to-target distance (Down and Up) {worst_tip * 1000:.2f} mm")
    assert against < 1.0 and locked < 1.0 and worst_tip < 0.004, (against, locked, worst_tip)
    # Plain IK for comparison (shows the check can fail)
    saved_limits = autoassign._limit_chain
    autoassign._limit_chain = lambda *a: {}
    try:
        s.force_autoassign = True
        autoassign.autoassign(bpy.context, s, "L1")
        free_against, free_locked, _ = bend_checks(s, arm, markers, {"L1"})
    finally:
        autoassign._limit_chain = saved_limits
    print(f"plain IK for comparison: against {free_against:.1f} deg, locked axes {free_locked:.1f} deg")
    assert max(free_against, free_locked) > 1.0, "plain IK already bends correctly: the check proves nothing"
    # Keep Twist off: twist is free, the hinges still don't turn sideways or bend backwards
    s.keep_twist = False
    autoassign.autoassign(bpy.context, s, "L1")
    nt = bend_checks(s, arm, markers, {"L1"}, keep_twist=False)
    print(f"keep twist off: against {nt[0]:.3f} deg, side turn {nt[1]:.3f} deg, tip {nt[2] * 1000:.2f} mm")
    assert nt[0] < 1.0 and nt[1] < 1.0 and nt[2] < 0.004, nt
    s.keep_twist = True
    autoassign.autoassign(bpy.context, s, "L1")
    _, _, problems, _ = autoassign.autoassign(bpy.context, s)
    assert problems == [], problems          # every Down and Up target reached
    assert autoassign.misses("L1") == [] and autoassign.status_line(32, 0, []) == "32 poses"
    reach_checks(s, arm, markers)
    # A marker out of reach is reported, not silently missed: one line per finger, every missing
    # pose listed on the pose (panel 2) and in the Info log lines, with which way to move the hand
    e_marker = markers[("R2", "E")]
    e_marker.location.z += 0.2
    created, skipped, problems, rest_msg = autoassign.autoassign(bpy.context, s, "R2")
    assert len(problems) == 1 and problems[0].startswith("R Middle: 2 of 2 poses miss") and "mm off" in problems[0], problems
    r2 = autoassign.misses("R2")
    assert [n for n, _, _ in r2] == ["F.R2.E.Down", "F.R2.E.Up"] and all(mm > 100 and adv for _, mm, adv in r2), r2
    assert autoassign.misses("R3") == []
    lines = autoassign.report_lines(s, problems, rest_msg)
    assert lines[1] == problems[0] and any("F.R2.E.Down" in ln and "mm off" in ln for ln in lines), lines
    status = autoassign.status_line(created, skipped, problems)
    assert status == f"{created} poses; 1 finger misses: see panel 2 (details in the Info log)", status
    print("miss list:", status, "|", " / ".join(lines[1:]))
    e_marker.location.z -= 0.2
    autoassign.autoassign(bpy.context, s, "R2")
    s.force_autoassign = False
    assert max(bend_checks(s, arm, markers)[:2]) < 1.0

    # Auto Rest: every finger up over its home key, plus the hand bones
    rest = bpy.data.actions.get("F.Rest")
    assert rest is not None and rest.asset_data is not None and s.rest_pose == rest
    rest_vals = actions.pose_values(rest)
    rest_bones = {actions.bone_of(p) for p, _ in rest_vals}
    expected = {b for chain in rig.finger_bones(s).values() for b in chain} | {"hand.L", "hand.R"}
    assert rest_bones == expected, rest_bones ^ expected
    home_up = actions.pose_values(bpy.data.actions["F.L1.B.Up"])
    assert all(abs(rest_vals[k] - v) < 1e-5 for k, v in home_up.items())
    # A manual Rest pose wins
    manual = actions.build_action(arm, "My Rest", [('pose.bones["hand.L"].location', 0, [(1, 0.0)])],
                                  "CONSTANT", fake_user=True)
    manual.asset_mark()
    s.rest_pose = manual
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
    assert s.rest_pose == manual and "F.Rest" in bpy.data.actions
    s.rest_pose = None
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
    assert s.rest_pose == bpy.data.actions["F.Rest"]
    bpy.data.actions.remove(manual)

    # Lock: editing a pose locks it; Autoassign keeps it
    autoassign_pose = bpy.data.actions["F.L2.A.Down"]
    fc = actions.action_fcurves(autoassign_pose)[0]
    fc.keyframe_points[0].co.y += 0.1
    fc.update()
    edited_value = fc.keyframe_points[0].co.y
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
    fc = actions.action_fcurves(bpy.data.actions["F.L2.A.Down"])[0]
    assert abs(fc.keyframe_points[0].co.y - edited_value) < 1e-6, "edited pose was overwritten"
    assert autoassign.is_locked(bpy.data.actions["F.L2.A.Down"])

    # Note map
    assert bpy.ops.midianim.fill_from_chart(which="FILE") == {"FINISHED"}
    g4 = state.find_note(s, parse_note_name("G4"))
    assert state.parse_combination(g4.combination) == {"L1": "B", "L2": "A", "L3": "G"}
    # Whole chart: Bb3 .. F#6, and the high F# key has its poses like any other key
    assert bpy.ops.midianim.fill_from_chart(which="ALL") == {"FINISHED"}
    assert [r.pitch for r in s.notes] == list(range(58, 91))
    fs6 = state.find_note(s, parse_note_name("F#6"))
    assert state.parse_combination(fs6.combination) == {"LT": "Octave", "L1": "PalmF", "R1": "HighF#"}
    assert "F.R1.HighF#.Down" in bpy.data.actions and "F.R1.HighF#.Up" in bpy.data.actions

    hold_checks(scene, s, arm, sax, markers)

    # Blow effects
    bpy.context.view_layer.objects.active = face
    assert bpy.ops.midianim.effect_add(preset="CHEEKS") == {"FINISHED"}
    assert not any(p.id == "CHEST" for p in state.profile(s).presets), "Chest preset is part of Breathing now"
    assert not breathing.is_set_up(s)
    breathing_panel_checks(s)
    assert bpy.ops.midianim.breathing_add() == {"FINISHED"}
    assert breathing.is_set_up(s)
    breathing_panel_checks(s)
    cheeks, lungs = s.effects
    assert cheeks.target == face and lungs.name == "Breathing" and lungs.target == arm
    assert lungs.mode == "LUNG" and lungs.data_path == '["breath_lung"]'
    assert bpy.ops.midianim.breathing_add() == {"FINISHED"} and len(s.effects) == 2     # Redo: no duplicates
    bpy.ops.midianim.effect_add(preset="")
    missing = s.effects[2]
    missing.name, missing.target, missing.target_type = "Missing", face, "SHAPE_KEY"
    missing.cc_number = 11                      # not in the file
    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    assert missing.missing and not cheeks.missing

    assert bpy.ops.midianim.bake() == {"FINISHED"}
    tracks = [t.name for t in arm.animation_data.nla_tracks]
    assert "MIDI: Fingering" in tracks and "MIDI: Breathing" in tracks and "Base: Idle" in tracks, tracks
    sk_tracks = [t.name for t in face.data.shape_keys.animation_data.nla_tracks]
    assert sk_tracks == ["MIDI: Cheeks"], sk_tracks         # Missing was skipped, not silently baked

    # Evaluate: during G4 (4th note, 1.8 s .. 2.4 s) L3 is down, R1 is up
    fps = 24
    scene.frame_set(int(1 + 2.1 * fps))
    l3 = actions.pose_values(bpy.data.actions["F.L3.G.Down"])
    for (path, idx), v in l3.items():
        owner, prop = path.rsplit(".", 1)
        got = getattr(arm.path_resolve(owner), prop)[idx]
        assert abs(got - v) < 1e-3, (path, idx, got, v)
    assert face.data.shape_keys.key_blocks["CheekPuff"].value > 0.3
    # Breathing: the baked lung drives the ribcage (Rigify-style chest: depth = Z, width = X)
    lung = arm["breath_lung"]
    cs = arm.pose.bones["chest"].scale
    assert 0.0 < lung <= 1.0 and abs(cs.z - (1 + 0.10 * lung)) < 1e-4 and abs(cs.x - (1 + 0.04 * lung)) < 1e-4, (lung, tuple(cs))
    assert abs(cs.y - 1.0) < 1e-6
    lungs_seen = set()
    for f in range(1, int(1 + 8 * fps), 2):
        scene.frame_set(f)
        lungs_seen.add(round(arm["breath_lung"], 2))
    assert len(lungs_seen) > 10 and min(lungs_seen) < 0.8 and max(lungs_seen) > 0.95, sorted(lungs_seen)
    scene.frame_set(int(1 + 2.1 * fps))
    assert abs(arm.pose.bones["hand.L"].location.y - 0.05) < 1e-4, "base idle lost"
    # The rest between phrases (5.4 s .. 6.6 s) uses the auto Rest pose
    scene.frame_set(int(1 + 6.0 * fps))
    l2 = set(rig.finger_bones(s)["L2"])
    for (path, idx), v in actions.pose_values(bpy.data.actions["F.Rest"], l2).items():
        owner, prop = path.rsplit(".", 1)
        got = getattr(arm.path_resolve(owner), prop)[idx]
        assert abs(got - v) < 1e-3, ("rest", path, idx, got, v)

    hold_breath_checks(scene, s, arm, sax)

    # Re-bake replaces only MIDI tracks
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert [t.name for t in arm.animation_data.nla_tracks].count("MIDI: Fingering") == 1
    assert bpy.ops.midianim.clear() == {"FINISHED"}
    assert not any(t.name.startswith("MIDI:") for t in arm.animation_data.nla_tracks)

    # HUD names
    s.hud.naming = "SOLFEGE"
    assert state.display_name(s, parse_note_name("D4")) == "Ré4"
    clarinet_checks(scene, s, arm)
    two_finger_checks()
    offjoint_and_front_checks()
    breathing_checks(sideways_spine=False)
    breathing_checks(sideways_spine=True)
    old_chest_checks()
    midi_animator.unregister()
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
