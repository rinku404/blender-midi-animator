"""Per-finger sax chart and the hand lock. Run like test_in_blender.py."""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import midi_animator as ma  # noqa: E402

MID = os.path.join(ROOT, "examples", "aerophone_sample.mid")
FINGERS = {"L1": "index.L", "L2": "middle.L", "L3": "ring.L", "LP": "pinky.L",
           "R1": "index.R", "R2": "middle.R", "R3": "ring.R", "RP": "pinky.R"}


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    arm = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", arm)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones

    def bone(name, head, tail, parent=None, connect=False):
        b = eb.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    bone("spine", (0, 0, 0), (0, 0, 1))
    bone("chest", (0, 0, 1), (0, 0, 1.4), "spine", True)
    for side, x in (("L", 1), ("R", -1)):
        bone(f"upper_arm.{side}", (0.2 * x, 0, 1.35), (0.5 * x, 0.05, 1.1), "chest")
        bone(f"forearm.{side}", (0.5 * x, 0.05, 1.1), (0.3 * x, -0.25, 1.0), f"upper_arm.{side}", True)
        bone(f"hand.{side}", (0.3 * x, -0.25, 1.0), (0.25 * x, -0.33, 1.0), f"forearm.{side}", True)
        bone(f"thumb.{side}", (0.3 * x, -0.27, 1.0), (0.28 * x, -0.3, 0.98), f"hand.{side}")
        for f in ("index", "middle", "ring", "pinky"):
            prev = f"hand.{side}"
            for j in range(3):
                n = f"{f}{'' if j == 0 else j}.{side}"
                y0 = -0.33 - 0.02 * j
                bone(n, (0.25 * x, y0, 1.0), (0.25 * x, y0 - 0.02, 1.0), prev, j > 0)
                prev = n
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.6, location=(0, -0.3, 1.0))
    sax = bpy.context.active_object
    sax.name = "Saxophone"
    return scene, rig, sax


def joints(rig, finger_bone):
    base, side = finger_bone.split(".")
    return [rig.pose.bones[f"{base}{'' if j == 0 else j}.{side}"] for j in range(3)]


def save(rig, element, bones):
    s = bpy.context.scene.midi_animator
    s.save_note = element
    with bpy.context.temp_override(selected_pose_bones=bones):
        assert bpy.ops.midianim.save_fingering() == {"FINISHED"}


def main():
    ma.register()
    scene, rig, sax = build()
    s = scene.midi_animator
    s.midi_path = MID
    s.fing_target = rig
    assert s.fing_mode == "CHART"

    # Chart sanity
    assert ma.chart_elements(62) == ("L1", "L2", "L3", "R1", "R2", "R3")
    assert ma.chart_elements(74) == ma.chart_elements(62) + ("OctaveKey",)
    assert ma.chart_elements(73) == ()
    assert ma.chart_elements(86) == ("OctaveKey", "Palm")

    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    all_finger_bones = [pb for pb in rig.pose.bones
                        if any(pb.name.startswith(f) for f in ("index", "middle", "ring", "pinky", "thumb"))]
    for pb in all_finger_bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler.x = 0.3          # Rest: lightly curled on the keys
    save(rig, "Rest", all_finger_bones)
    for el, fb in FINGERS.items():
        js = joints(rig, fb)
        for pb in js:
            pb.rotation_euler.x = 0.5      # pressed
        save(rig, el, js)
        for pb in js:
            pb.rotation_euler.x = 0.3
    th = rig.pose.bones["thumb.L"]
    th.rotation_euler.x = 0.6
    save(rig, "OctaveKey", [th])
    th.rotation_euler.x = 0.3
    pinky_l = joints(rig, "pinky.L")
    for pb in pinky_l:
        pb.rotation_euler.x = 0.7
    save(rig, "Palm", pinky_l)
    for pb in pinky_l:
        pb.rotation_euler.x = 0.3
    bpy.ops.object.mode_set(mode="OBJECT")

    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    assert s.fing_missing == "", s.fing_missing
    assert bpy.ops.midianim.bake() == {"FINISHED"}

    beat = 0.6 * 24

    def at(frame):
        scene.frame_set(int(frame), subframe=frame - int(frame))
        pb = rig.pose.bones
        return {k: pb[v].rotation_euler.x for k, v in FINGERS.items()} | \
               {"tip": pb["index2.L"].rotation_euler.x, "OCT": pb["thumb.L"].rotation_euler.x}

    d4 = at(1 + 0.5 * beat)                       # D4: six fingers down, pinkies and thumb up
    assert all(approx(d4[k], 0.5) for k in ("L1", "L2", "L3", "R1", "R2", "R3")), d4
    assert approx(d4["LP"], 0.3) and approx(d4["RP"], 0.3) and approx(d4["OCT"], 0.3), d4
    assert approx(d4["tip"], 0.5), "tip joints must move too"
    e4 = at(1 + 1.5 * beat)                       # E4: R3 lifts, the rest stay pressed
    assert approx(e4["R3"], 0.3) and approx(e4["R2"], 0.5) and approx(e4["L1"], 0.5), e4
    cs5 = at(1 + 6.5 * beat)                      # C#5: everything open
    assert all(approx(cs5[k], 0.3) for k in FINGERS), cs5
    d5 = at(1 + 7.5 * beat)                       # D5: like D4 + octave key
    assert approx(d5["L1"], 0.5) and approx(d5["OCT"], 0.6), d5
    lowc = at(1 + 17.5 * beat)                    # low C4: six down + right pinky
    assert approx(lowc["RP"], 0.5) and approx(lowc["R3"], 0.5), lowc
    # Smooth: half way through the E4 -> F#4 transition R2 is between up and down
    mid = at(1 + 2 * beat - 1)
    assert 0.3 - 1e-3 <= mid["R1"] <= 0.5 + 1e-3, mid
    print("chart OK")

    # ---- Hold: sax hangs from chest, hands locked to it ----
    s.hold_instrument = sax
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    assert (s.hold_chest_bone, s.hold_hand_l, s.hold_hand_r) == ("chest", "hand.L", "hand.R"), \
        (s.hold_chest_bone, s.hold_hand_l, s.hold_hand_r)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    pb = rig.pose.bones
    hand_before = (rig.matrix_world @ pb["hand.L"].head).copy()
    elbow_before = (rig.matrix_world @ pb["forearm.L"].head).copy()
    sax_before = sax.matrix_world.translation.copy()
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    bpy.context.view_layer.update()
    assert sax.parent == rig and sax.parent_bone == "chest"
    assert (sax.matrix_world.translation - sax_before).length < 1e-4, "sax moved when parented"
    assert ((rig.matrix_world @ pb["hand.L"].head) - hand_before).length < 1e-3, "hand moved on lock"
    assert ((rig.matrix_world @ pb["forearm.L"].head) - elbow_before).length < 1e-2, "elbow drifted"

    # Bend the chest: the sax follows, and the hands stay on the sax
    pb["chest"].rotation_mode = "XYZ"
    pb["chest"].rotation_euler.x = math.radians(20)
    bpy.context.view_layer.update()
    tgt = bpy.data.objects["MIDI Hold L"]
    hand_now = rig.matrix_world @ pb["hand.L"].head
    assert (sax.matrix_world.translation - sax_before).length > 0.01, "sax did not follow chest"
    assert (hand_now - tgt.matrix_world.translation).length < 1e-3, (hand_now, tgt.matrix_world.translation)

    # Rebake still works with the lock on; unlock cleans up
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}   # idempotent
    n_ik = sum(1 for b in pb for c in b.constraints if c.name.startswith("MIDI Hold"))
    assert n_ik == 4, n_ik
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    assert not any(c.name.startswith("MIDI Hold") for b in pb for c in b.constraints)
    assert "MIDI Hold L" not in bpy.data.objects

    ma.unregister()
    print("ALL CHART/HOLD TESTS PASSED")


main()
