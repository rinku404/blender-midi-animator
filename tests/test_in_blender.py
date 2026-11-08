"""End-to-end test inside Blender:

    blender -b --factory-startup --python tests/test_in_blender.py

Builds a small rig with Rigify-style finger names (fingers curled a little downwards at rest),
an instrument with key markers and a face with a CheekPuff shape key; then Detect Fingers ->
Autoassign -> Fill From Chart -> blow effects -> Bake, and checks the result.
"""
import math
import os
import sys
import traceback

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import midi_animator  # noqa: E402
from midi_animator.blender import actions, autoassign, rig, state  # noqa: E402
from midi_animator.core.notes import parse_note_name  # noqa: E402

MID = os.path.join(ROOT, "examples", "aerophone_sample.mid")
CURL = math.radians(8)        # rest curl per joint (downwards): the test rig's bend axis is -X
FINGERS = [("thumb", "L", -0.06), ("f_index", "L", -0.02), ("f_middle", "L", 0.0), ("f_ring", "L", 0.02),
           ("f_pinky", "L", 0.04), ("f_index", "R", -0.02), ("f_middle", "R", 0.0), ("f_ring", "R", 0.02),
           ("f_pinky", "R", 0.04)]


def build_scene():
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
        for name, s, z in FINGERS:
            if s != side:
                continue
            parent, head = hand, Vector((x, 0.1, 1.3 + z))
            for i in range(1, 4):
                b = eb.new(f"{name}.0{i}.{side}")
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
    for slot in prof.slots:
        chain = rig.finger_bones(s)[slot.id]
        tip = arm.matrix_world @ arm.pose.bones[chain[-1]].tail
        for k, key in enumerate(slot.keys):
            ctx.scene.cursor.location = tip + Vector((0.003 * k, -0.02, -0.03))
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
                    turns = [twist] if keep_twist else []
                    if i > 0:
                        turns += [side, math.degrees(e.z)] + ([math.degrees(e.y)] if keep_twist else [])
                    locked = max([locked] + [abs(v) for v in turns])
                mw = markers[(slot.id, key)].matrix_world
                target = mw.translation if down else mw.translation + mw.to_3x3().col[2].normalized() * s.hover
                worst_tip = max(worst_tip, (tip_world(arm, chain[-1]) - target).length)
    return against, locked, worst_tip


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
    """After a bake with the Chest effect and the hold locked."""
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
    chest_scale = max(pb["chest"].scale.x, 1.0)
    print(f"max sax scale error {worst:.2e}; chest scale up to {chest_scale:.3f}; bone-parented probe {probe_scale:.3f}")
    assert chest_scale > 1.005, "Chest effect did not scale the bone, so this test proves nothing"
    assert probe_scale > 1.005, "bone parenting should scale (the reason for Child Of)"
    assert worst < 1e-4, worst
    print(f"max hand-to-target gap while breathing: {gap * 1000:.3f} mm")
    assert gap < 0.001, gap         # the upper arms don't inherit the chest's scale while locked
    assert arm.data.bones["upper_arm.L"].inherit_scale == "NONE"
    bpy.data.objects.remove(probe)

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
        assert b.inherit_scale == "FULL" and "midianim_inherit_scale" not in b, "inherit scale not restored"
    # Missing bones give a clean error, not a traceback
    s.hold_hand_r = "nope"
    try:
        bpy.ops.midianim.lock_hands()
        raise AssertionError("lock with a missing bone should fail")
    except RuntimeError as e:
        assert "not found" in str(e), e
    s.hold_hand_r = "hand.R"


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
    # A marker out of reach is reported, not silently missed
    e_marker = markers[("R2", "E")]
    e_marker.location.z += 0.2
    _, _, problems, _ = autoassign.autoassign(bpy.context, s, "R2")
    assert len(problems) == 1 and "mm off" in problems[0], problems
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
    assert bpy.ops.midianim.effect_add(preset="CHEST") == {"FINISHED"}
    cheeks, chest = s.effects
    assert cheeks.target == face and chest.target == arm and chest.bone == "chest"
    assert chest.mode == "LUNG"
    bpy.ops.midianim.effect_add(preset="")
    missing = s.effects[2]
    missing.name, missing.target, missing.target_type = "Missing", face, "SHAPE_KEY"
    missing.cc_number = 11                      # not in the file
    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    assert missing.missing and not cheeks.missing

    assert bpy.ops.midianim.bake() == {"FINISHED"}
    tracks = [t.name for t in arm.animation_data.nla_tracks]
    assert "MIDI: Fingering" in tracks and "MIDI: Chest" in tracks and "Base: Idle" in tracks, tracks
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
    sy_mid = arm.pose.bones["chest"].scale.x
    scene.frame_set(int(1 + 4.6 * fps))       # late in the first phrase: lungs emptier
    assert arm.pose.bones["chest"].scale.x < sy_mid
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
    midi_animator.unregister()
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
