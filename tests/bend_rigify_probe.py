"""Probe (not a pass/fail test): Detect Bend Axis + Autoassign on Rigify's human metarig.

    blender -b --factory-startup --python tests/bend_rigify_probe.py

Adds the metarig (fingers slightly curled at rest), puts one key marker 1.5 cm towards the palm
and 1.5 cm back from each fingertip, with the hand left in its rest pose (not posed onto an
instrument), and prints:
- the detected bend axis (Rigify: X),
- per finger, how far the tip ends from its Down and Up targets, with the step-4 limits and with
  the knuckle allowed to extend 10 or 20 degrees against the bend axis, and with plain IK,
- the worst turn against the bend axis and on a locked axis.
Written for plan step 4; the numbers are in docs/plan/reports/step-04-finger-quality.md.
"""
import math
import os
import sys

import addon_utils
import bpy
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import midi_animator  # noqa: E402
from midi_animator.blender import autoassign, rig, state  # noqa: E402
from midi_animator.core import rigs as core_rigs  # noqa: E402


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    midi_animator.register()
    addon_utils.enable("rigify", default_set=True)
    bpy.ops.object.armature_human_metarig_add()
    arm = bpy.context.active_object
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    sax = bpy.data.objects.new("Sax", None)
    bpy.context.scene.collection.objects.link(sax)
    s = bpy.context.scene.midi_animator
    s.rig, s.instrument = arm, sax
    rig.sync_finger_slots(s)
    return s, arm


def place_markers(s, arm):
    bpy.context.view_layer.update()
    for slot in state.profile(s).slots:
        chain = rig.finger_bones(s)[slot.id]
        m = (arm.matrix_world @ arm.pose.bones[chain[-1]].matrix).to_3x3()
        y, palm = m.col[1].normalized(), m.col[2].normalized()   # +X curl moves the tip towards +Z
        tip = arm.matrix_world @ arm.pose.bones[chain[-1]].tail
        bpy.context.scene.cursor.location = tip + palm * 0.015 - y * 0.015
        rig.add_marker(bpy.context, s, slot.id, slot.keys[0])


def measure(s, arm):
    markers = rig.find_markers()
    miss, against, locked = {}, 0.0, 0.0
    for slot in state.profile(s).slots:
        chain = rig.finger_bones(s)[slot.id]
        key = slot.keys[0]
        mw = markers[(slot.id, key)].matrix_world
        row = []
        for down in (True, False):
            bpy.ops.midianim.apply_pose(action=autoassign.pose_name(slot.id, key, down))
            bpy.context.view_layer.update()
            target = mw.translation if down else mw.translation + mw.to_3x3().col[2].normalized() * s.hover
            row.append(round(((arm.matrix_world @ arm.pose.bones[chain[-1]].tail) - target).length * 1000, 1))
            for i, b in enumerate(chain):
                q = arm.pose.bones[b].rotation_quaternion
                against = max(against, -math.degrees(2 * math.atan2(q.x, q.w)))
                twist = abs(math.degrees(2 * math.atan2(q.y, q.w)))
                e = q.to_euler("XYZ")
                turns = [twist] + ([abs(math.degrees(e.z))] if i > 0 else [])
                locked = max([locked] + turns)
        miss[slot.id] = row
    return miss, against, locked


def main():
    s, arm = setup()
    s.bend_axis = "Z"
    rig.detect_fingers(s)
    print("PROBE detected bend axis:", rig.detect_bend_axis(s))
    place_markers(s, arm)
    s.force_autoassign = True
    original = core_rigs.ik_joint_settings
    for ext in (0, 10, 20):
        def settings(axis, keep_twist=True, root=False, ext=ext):
            out = original(axis, keep_twist, root)
            if root:
                out["ik_min_x"] = -math.radians(ext)
            return out
        autoassign.rigs.ik_joint_settings = settings
        autoassign.autoassign(bpy.context, s)
        miss, against, locked = measure(s, arm)
        print(f"PROBE knuckle extension {ext:2d} deg: against {against:.1f} deg, locked {locked:.1f} deg, "
              f"tip off (Down, Up) mm {miss}")
    autoassign.rigs.ik_joint_settings = original
    saved = autoassign._limit_chain
    autoassign._limit_chain = lambda *a: {}
    autoassign.autoassign(bpy.context, s)
    autoassign._limit_chain = saved
    miss, against, locked = measure(s, arm)
    print(f"PROBE plain IK: against {against:.1f} deg, locked {locked:.1f} deg, tip off (Down, Up) mm {miss}")


main()
