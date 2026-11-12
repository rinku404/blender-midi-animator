"""Hold the Instrument: the instrument hangs from a strap bone and both hands stay locked to it.

- The instrument gets a Child Of constraint on the strap bone with *scale off*, so the Chest
  (breathing) effect, which scales that bone, never scales the instrument (ADR 0011).
- One target empty per hand ("MIDI Hold L/R") is parented to the instrument at the hand's current
  place. A 2-bone IK on the forearm reaches the target and the hand copies its rotation.
- The arm chain's root (upper arm) stops inheriting scale while locked, so breathing (the Chest
  effect scales the chest) never scales the arm: Blender's IK misses its target under a
  non-uniformly scaled parent. Unlock puts the bone's setting back.
- Everything is created from the current pose, so locking moves nothing.
- Arm bones whose tail sits off the next joint (CJ's FBX import: the forearm's tail 39 cm from
  the wrist) would throw the hand off by that much, since the IK aims the forearm's tail at the
  target. Lock moves those tails onto the joints first, keeping the pose and the mesh exactly
  (pose_new = pose_old · rest_old⁻¹ · rest_new), and says so.
- The instrument's front (keys / tone holes) is one of its local axes (Front in the Hold box,
  set from the view or from the key markers). Lock refuses while the front faces the player;
  Turn Front Forward rolls the instrument about its length until it faces forward.
"""

import math

import bpy
from mathutils import Matrix, Vector

from ..core import hold as geom
from ..core import rigs
from . import rig as rig_mod
from . import state

PREFIX = "MIDI Hold"
STRAP_CON = f"{PREFIX} Strap"
TARGETS = (("L", "hold_hand_l"), ("R", "hold_hand_r"))
INHERIT_PROP = "midianim_inherit_scale"     # on the arm's root bone: its setting before Lock
FRONT_NONE = "NONE"


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
    angle, verdict = front_status(s)
    if verdict == "player":
        return (f"The instrument's front faces the player ({angle:.0f}° from forward): click "
                "Turn Front Forward, or set Front to Not Set")
    if off_joint_bones(s) and not _editable(s.rig):
        return f"{s.rig.name}'s arm bones need fixing, but it is hidden: unhide it, then Lock"
    return ""


# -- arm bones whose tail is off the next joint (P1) --------------------------

def _editable(arm):
    return arm.visible_get() and not arm.hide_get()


def arm_chain(arm, hand_name):
    """[(bone, child)] for the bones Lock's IK moves: the forearm (child: the hand) and the upper
    arm (child: the forearm). Both tails should sit on the child's head."""
    pb = arm.pose.bones.get(hand_name)
    fore = pb.parent if pb else None
    if fore is None:
        return []
    chain = [(fore.name, hand_name)]
    if fore.parent is not None:
        chain.append((fore.parent.name, fore.name))
    return chain


def off_joint_bones(s):
    """[(bone, child, distance in metres)] for arm bones whose tail is off the next joint."""
    arm = s.rig
    if arm is None:
        return []
    scale = max(arm.matrix_world.to_scale())
    out = []
    for _, attr in TARGETS:
        for name, child in arm_chain(arm, getattr(s, attr)):
            b, c = arm.data.bones[name], arm.data.bones[child]
            d = (b.tail_local - c.head_local).length * scale
            if geom.off_joint([(name, d, b.length * scale)]):
                out.append((name, child, d))
    return out


def _subtree(arm, names):
    """The named bones and all their descendants, parents before children."""
    seen, order = set(), []

    def walk(pb):
        if pb.name in seen:
            return
        seen.add(pb.name)
        order.append(pb)
        for c in pb.children:
            walk(c)

    def depth(pb):
        d = 0
        while pb.parent:
            pb, d = pb.parent, d + 1
        return d

    for n in sorted(names, key=lambda n: depth(arm.pose.bones[n])):   # the upper arm before the forearm
        walk(arm.pose.bones[n])
    return order


def fix_arm_tails(context, s):
    """Move the tails of the off-joint arm bones onto their joints (roll kept). The pose and the
    mesh don't change: every bone keeps its deformation (pose · rest⁻¹), so the fixed bones turn
    to point along the limb while the skin stays. Returns [(bone, distance moved in metres)]."""
    arm = s.rig
    bad = off_joint_bones(s)
    if not bad:
        return []
    if not _editable(arm):
        raise RuntimeError(f"{arm.name} is hidden: unhide it to fix its arm bones")
    names = [n for n, _, _ in bad]
    # the plain pose, without constraints (a previous Lock's IK would move the forearm)
    cons = [(c, c.mute) for pb in arm.pose.bones for c in pb.constraints]
    for c, _ in cons:
        c.mute = True
    context.view_layer.update()
    pose_old = {pb.name: pb.matrix.copy() for pb in arm.pose.bones}
    rest_old = {b.name: b.matrix_local.copy() for b in arm.data.bones}

    active = context.view_layer.objects.active
    context.view_layer.objects.active = arm
    mirror = arm.data.use_mirror_x
    arm.data.use_mirror_x = False
    try:
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.data.edit_bones
        for name, child, _ in bad:
            b = eb[name]
            z = b.z_axis.copy()
            b.tail = eb[child].head.copy()
            b.align_roll(z)
        bpy.ops.object.mode_set(mode="OBJECT")
    finally:
        arm.data.use_mirror_x = mirror
        if active is not None and active.name in context.view_layer.objects:
            context.view_layer.objects.active = active
    context.view_layer.update()
    rest_new = {b.name: b.matrix_local.copy() for b in arm.data.bones}
    for pb in _subtree(arm, names):
        n = pb.name
        pb.matrix = pose_old[n] @ rest_old[n].inverted() @ rest_new[n]
        context.view_layer.update()
    for c, mute in cons:
        c.mute = mute
    context.view_layer.update()
    return [(n, d) for n, _, d in bad]


# -- the instrument's front (P10) ---------------------------------------------

def front_world(s):
    """The instrument's front as a world direction, or None when Front is not set."""
    if s.instrument is None or s.hold_front == FRONT_NONE:
        return None
    v = s.instrument.matrix_world.to_3x3() @ Vector(geom.axis_vector(s.hold_front))
    return v.normalized() if v.length > 1e-9 else None


def player_forward(s):
    """Where the player faces: the rig's -Y, or the world's front when the rig isn't upright."""
    if s.rig is None:
        return Vector((0.0, -1.0, 0.0))
    return Vector(geom.player_forward(tuple(s.rig.matrix_world.to_3x3() @ Vector((0, -1, 0)))))


def front_status(s):
    """(angle from forward in degrees or None, verdict): "forward", "sideways", "player", or
    "unknown" when Front isn't set."""
    f = front_world(s)
    return geom.facing(tuple(f) if f is not None else None, tuple(player_forward(s)))


def set_front_from_direction(s, world_dir):
    """Store the instrument's local axis nearest to a world direction. Returns (axis, degrees off)."""
    local = s.instrument.matrix_world.to_3x3().inverted() @ Vector(world_dir)
    axis, off = geom.nearest_axis(tuple(local))
    if axis is None:
        raise RuntimeError("That direction is undefined")
    s.hold_front = axis
    return axis, off


def set_front_from_view(s, region_3d):
    """The side of the instrument that faces the viewer in this 3D view is its front."""
    toward_viewer = region_3d.view_rotation @ Vector((0.0, 0.0, 1.0))
    return set_front_from_direction(s, toward_viewer)


def marker_front(s):
    """Mean arrow of the key markers on the instrument (thumb keys left out: they sit on the back),
    as a world direction, or None without markers."""
    prof = state.profile(s)
    dirs = []
    for (slot, _), m in rig_mod.find_markers().items():
        sl = prof.slot(slot)
        if m.parent != s.instrument or (sl is not None and sl.finger == "thumb"):
            continue
        dirs.append(tuple(m.matrix_world.to_3x3().col[2]))
    v = geom.mean_direction(dirs)
    return Vector(v) if v is not None else None


def set_front_from_markers(s):
    v = marker_front(s)
    if v is None:
        raise RuntimeError("No key markers on the instrument yet: place them, or use From View")
    return set_front_from_direction(s, v)


def instrument_axis(inst):
    """(centre, unit direction) of the instrument's long axis from its meshes' vertices, world
    space, or None when it has no mesh."""
    import numpy as np
    pts = []
    for o in [inst] + list(inst.children_recursive):
        if o.type != "MESH" or not o.data.vertices:
            continue
        co = np.empty(len(o.data.vertices) * 3)
        o.data.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)[::max(1, len(o.data.vertices) // 4000)]
        m = np.array(o.matrix_world)
        pts.append(co @ m[:3, :3].T + m[:3, 3])
    if not pts:
        return None
    x = np.concatenate(pts)
    centre = x.mean(0)
    _, vecs = np.linalg.eigh((x - centre).T @ (x - centre))
    return Vector(centre), Vector(vecs[:, 2]).normalized()


def is_locked(s):
    return any(c.name.startswith(PREFIX) for pb in (s.rig.pose.bones if s.rig else ()) for c in pb.constraints)


def turn_front_forward(context, s):
    """Roll the instrument about its long axis until its front faces the player's forward.
    Children (key markers) turn with it. Returns the angle turned in degrees."""
    front = front_world(s)
    if front is None:
        raise RuntimeError("Set Front first (From View or From Markers)")
    if is_locked(s):
        raise RuntimeError("Unlock first: the hands would follow the keys round the tube")
    ax = instrument_axis(s.instrument)
    if ax is None:
        raise RuntimeError(f"{s.instrument.name} has no mesh to measure its length on")
    centre, axis = ax
    angle = geom.roll_angle(tuple(axis), tuple(front), tuple(player_forward(s)))
    if angle is None:
        raise RuntimeError("The front runs along the instrument's length: pick another Front axis")
    inst = s.instrument
    context.view_layer.update()
    world = inst.matrix_world.copy()
    delta = Matrix.Translation(centre) @ Matrix.Rotation(angle, 4, axis) @ Matrix.Translation(-centre)
    # keep parenting and the strap Child Of: change only what the object itself contributes
    before = world @ inst.matrix_basis.inverted()
    inst.matrix_basis = before.inverted() @ delta @ before @ inst.matrix_basis
    context.view_layer.update()
    return math.degrees(angle)


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
    fixed = fix_arm_tails(context, s)
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
    msg = (f"{s.instrument.name} hangs from {s.hold_strap_bone}; hands locked to "
           f"{', '.join(t.name for t in targets.values())}. Move the targets to adjust the grip")
    if fixed:
        msg += (f". Moved {len(fixed)} arm bone tail{'s' if len(fixed) != 1 else ''} onto the joint: "
                + ", ".join(f"{n} ({d * 100:.1f} cm)" for n, d in fixed))
    return msg


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
