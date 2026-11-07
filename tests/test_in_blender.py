"""End-to-end test inside Blender:

    blender -b --factory-startup --python tests/test_in_blender.py

Builds a small rig with Rigify-style finger names, an instrument with key markers and a
face with a CheekPuff shape key; then Detect Fingers -> Autoassign -> Fill From Chart ->
blow effects -> Bake, and checks the result.
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
            parent = hand
            for i in range(1, 4):
                b = eb.new(f"{name}.0{i}.{side}")
                y0 = 0.1 + (i - 1) * 0.03
                b.head, b.tail = (x, y0, 1.3 + z), (x, y0 + 0.03, 1.3 + z)
                b.parent = parent
                b.use_connect = i > 1
                parent = b
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
    """One marker per key, a little below each fingertip (keys of one finger side by side)."""
    prof = state.profile(s)
    ctx = bpy.context
    ctx.view_layer.update()
    for slot in prof.slots:
        chain = rig.finger_bones(s)[slot.id]
        tip = arm.matrix_world @ arm.pose.bones[chain[-1]].tail
        for k, key in enumerate(slot.keys):
            ctx.scene.cursor.location = tip + Vector((0.0, -0.01 - 0.004 * k, -0.02))
            ctx.scene.cursor.rotation_euler = (0, 0, 0)
            rig.add_marker(ctx, s, slot.id, key)


def tip_world(arm, bone):
    bpy.context.view_layer.update()
    return arm.matrix_world @ arm.pose.bones[bone].tail


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
    print(f"max hand-to-target gap while breathing: {gap * 1000:.1f} mm")
    assert gap < 0.02, gap          # Blender's IK is not exact under a scaled parent
    bpy.data.objects.remove(probe)

    # Idempotent re-lock; unlock cleans up
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    n_con = sum(1 for b in pb for c in b.constraints if c.name.startswith("MIDI Hold"))
    assert n_con == 4, n_con
    assert sum(1 for c in sax.constraints if c.name == "MIDI Hold Strap") == 1
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    assert not any(c.name.startswith("MIDI Hold") for b in pb for c in b.constraints)
    assert "MIDI Hold L" not in bpy.data.objects and "MIDI Hold R" not in bpy.data.objects
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

    # Fingers
    assert bpy.ops.midianim.detect_fingers() == {"FINISHED"}
    bones = rig.finger_bones(s)
    assert bones["L1"] == ["f_index.01.L", "f_index.02.L", "f_index.03.L"], bones
    assert bones["LT"][0] == "thumb.01.L" and len(bones) == 9

    # Markers + autoassign
    place_markers(s, arm)
    markers = rig.find_markers()
    assert markers[("L1", "B")].parent == sax
    rest_rot = tuple(arm.pose.bones["f_index.01.L"].rotation_quaternion)
    assert bpy.ops.midianim.autoassign() == {"FINISHED"}
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
