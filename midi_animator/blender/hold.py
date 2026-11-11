"""Hold the Instrument: the instrument hangs from a strap bone and both hands stay locked to it.

- The instrument gets a Child Of constraint on the strap bone with *scale off*, so the Chest
  (breathing) effect, which scales that bone, never scales the instrument (ADR 0011).
- One target empty per hand ("MIDI Hold L/R") is parented to the instrument at the hand's current
  place. A 2-bone IK on the forearm reaches the target and the hand copies its rotation.
- The arm chain's root (upper arm) stops inheriting scale while locked, so breathing (the Chest
  effect scales the chest) never scales the arm: Blender's IK misses its target under a
  non-uniformly scaled parent. Unlock puts the bone's setting back.
- Everything is created from the current pose, so locking moves nothing.
"""

import bpy
from mathutils import Matrix

from ..core import rigs

PREFIX = "MIDI Hold"
STRAP_CON = f"{PREFIX} Strap"
TARGETS = (("L", "hold_hand_l"), ("R", "hold_hand_r"))
INHERIT_PROP = "midianim_inherit_scale"     # on the arm's root bone: its setting before Lock


def guess_bones(s):
    """Fill the three bone settings from the rig's names. Returns labels of the ones not found."""
    arm = s.rig
    bones = [(b.name, b.parent.name if b.parent else None) for b in arm.data.bones]
    s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r = rigs.guess_hold_bones(bones)
    return [n for n, v in (("strap", s.hold_strap_bone), ("left hand", s.hold_hand_l),
                           ("right hand", s.hold_hand_r)) if not v]


def check(s):
    """Error text if Lock can't run, else ''."""
    if not s.rig:
        return "Set the Character Rig first"
    if not s.instrument:
        return "Set the Instrument first"
    for label, name in (("Strap", s.hold_strap_bone), ("Left hand", s.hold_hand_l),
                        ("Right hand", s.hold_hand_r)):
        if name not in s.rig.pose.bones:
            return f"{label} bone '{name}' not found on {s.rig.name}: pick it or press Guess"
    if len({s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r}) < 3:
        return "Strap and hand bones must be three different bones"
    return ""


def _unscaled(m):
    loc, rot, _ = m.decompose()
    return Matrix.Translation(loc) @ rot.to_matrix().to_4x4()


def _hang_from_strap(context, s):
    inst, arm = s.instrument, s.rig
    context.view_layer.update()
    mw = inst.matrix_world.copy()
    for c in [c for c in inst.constraints if c.name == STRAP_CON]:
        inst.constraints.remove(c)
    if inst.parent is not None:
        inst.parent = None
    inst.matrix_world = mw
    con = inst.constraints.new("CHILD_OF")
    con.name = STRAP_CON
    con.target = arm
    con.subtarget = s.hold_strap_bone
    con.use_scale_x = con.use_scale_y = con.use_scale_z = False
    context.view_layer.update()
    # inverse of the strap bone's scale-free matrix: the instrument stays where it is
    con.inverse_matrix = _unscaled(arm.matrix_world @ arm.pose.bones[s.hold_strap_bone].matrix).inverted()
    context.view_layer.update()
    inst.matrix_world = mw


def _target(context, s, side, bone_name):
    arm, inst = s.rig, s.instrument
    name = f"{PREFIX} {side}"
    tgt = bpy.data.objects.get(name)
    if tgt is not None:
        return tgt            # keep a grip the user already adjusted
    pb = arm.pose.bones[bone_name]
    tgt = bpy.data.objects.new(name, None)
    tgt.empty_display_type = "SPHERE"
    tgt.empty_display_size = max(0.02, 0.015 * max(arm.dimensions))
    (inst.users_collection[0] if inst.users_collection else context.scene.collection).objects.link(tgt)
    hand_mw = arm.matrix_world @ pb.matrix
    tgt.parent = inst
    context.view_layer.update()
    tgt.matrix_world = hand_mw
    return tgt


def _clear_hand_constraints(arm):
    n = 0
    for pb in arm.pose.bones:
        for c in [c for c in pb.constraints if c.name.startswith(PREFIX)]:
            pb.constraints.remove(c)
            n += 1
    return n


def _arm_root(pb):
    """Root bone of the 2-bone arm IK on the hand's parent (the upper arm), or None."""
    fore = pb.parent
    if fore is None:
        return None
    return fore.parent or fore


def _stop_scale_inheritance(pb):
    root = _arm_root(pb)
    if root is None:
        return
    bone = root.bone
    if INHERIT_PROP not in bone:            # keep the original through repeated locks
        bone[INHERIT_PROP] = bone.inherit_scale
    bone.inherit_scale = "NONE"


def _restore_scale_inheritance(arm):
    for bone in arm.data.bones:
        if INHERIT_PROP in bone:
            bone.inherit_scale = bone[INHERIT_PROP]
            del bone[INHERIT_PROP]


def lock_hands(context, s):
    """Returns a one-line summary. Safe to call again (it rebuilds the constraints)."""
    arm = s.rig
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    context.view_layer.update()
    # Hang the instrument first (from the pose as it shows now), then place new targets
    # at the hands' current place.
    _hang_from_strap(context, s)
    targets = {side: _target(context, s, side, getattr(s, attr)) for side, attr in TARGETS}
    _clear_hand_constraints(arm)
    for side, attr in TARGETS:
        pb = arm.pose.bones[getattr(s, attr)]
        tgt = targets[side]
        if pb.parent:
            ik = pb.parent.constraints.new("IK")
            ik.name = f"{PREFIX} IK"
            ik.target = tgt
            ik.chain_count = 2
            ik.use_tail = True
            ik.use_stretch = False
        cr = pb.constraints.new("COPY_ROTATION")
        cr.name = f"{PREFIX} Rotation"
        cr.target = tgt
        _stop_scale_inheritance(pb)
    context.view_layer.update()
    return (f"{s.instrument.name} hangs from {s.hold_strap_bone}; hands locked to "
            f"{', '.join(t.name for t in targets.values())}. Move the targets to adjust the grip")


def rotation_target(arm, bone_name):
    """The hold target that holds `bone_name`'s rotation while locked, or None. While it does,
    a tilt keyed on the bone is overridden, so Bake keys the tilt on the target instead."""
    pb = arm.pose.bones.get(bone_name) if arm else None
    for c in (pb.constraints if pb else ()):
        if (c.type == "COPY_ROTATION" and c.name == f"{PREFIX} Rotation" and c.target is not None
                and not c.mute and c.influence > 0.0):
            return c.target
    return None


def unlock_hands(context, s):
    """Remove the hand constraints and targets, and give the arms back their scale inheritance.
    The instrument keeps hanging from the strap."""
    n = _clear_hand_constraints(s.rig) if s.rig else 0
    if s.rig:
        _restore_scale_inheritance(s.rig)
    for side, _ in TARGETS:
        o = bpy.data.objects.get(f"{PREFIX} {side}")
        if o:
            bpy.data.objects.remove(o)
    context.view_layer.update()
    return n
