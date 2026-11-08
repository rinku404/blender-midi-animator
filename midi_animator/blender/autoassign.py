"""Autoassign: solve each finger onto its key markers with a temporary IK constraint and save
the result as pose assets ("F.<slot>.<key>.Down" / ".Up").

While solving, each finger joint only turns around the rig's Bend Axis and only in the curling
direction (the knuckle may also spread a little sideways), so fingers neither twist nor bend
backwards. The bones' own IK settings are put back afterwards.

Autoassign also builds "F.Rest": every finger hovering over its home key, plus the hand bones
as they are now. It becomes the Rest pose unless you picked your own.

Generated poses remember a fingerprint of their values. If you edit a pose (or lock it by
hand), Autoassign leaves it alone unless "Overwrite Locked" is on.
"""

import hashlib

import bpy

from ..core import rigs
from . import actions, rig, state

GEN_PROP = "midianim_generated"
HASH_PROP = "midianim_hash"
LOCK_PROP = "midianim_locked"
REST_NAME = "F.Rest"
MISS_TOLERANCE = 0.003      # m: report a fingertip that ends further than this from its target
_IK_ATTRS = tuple(f"{k}_{a}" for k in ("lock_ik", "use_ik_limit", "ik_min", "ik_max") for a in "xyz")


def pose_name(slot, key, down):
    return f"F.{slot}.{key}.{'Down' if down else 'Up'}"


def _fingerprint(values):
    items = sorted((p, i, round(v, 5)) for (p, i), v in values.items())
    return hashlib.sha1(repr(items).encode()).hexdigest()[:16]


def is_locked(action):
    """Locked by hand, or edited since Autoassign generated it (which locks it)."""
    if action is None:
        return False
    if action.get(LOCK_PROP):
        return True
    stored = action.get(HASH_PROP)
    if stored and stored != _fingerprint(actions.pose_values(action)):
        action[LOCK_PROP] = True
        return True
    return False


def _save_pose(arm, name, bones):
    values = {}
    for b in bones:
        values.update(actions.bone_channels(arm.pose.bones[b]))
    return _save_values(arm, name, values)


def _save_values(arm, name, values):
    chans = [(p, i, [(1.0, v)]) for (p, i), v in sorted(values.items())]
    act = actions.build_action(arm, name, chans, "CONSTANT", fake_user=True, replace=True)
    if act.asset_data is None:
        act.asset_mark()
    act[GEN_PROP] = True
    act[HASH_PROP] = _fingerprint(actions.pose_values(act))
    act[LOCK_PROP] = False
    return act


def _limit_chain(arm, chain, bend_axis, keep_twist):
    """Give the chain's bones bend-only IK settings. Returns what _unlimit_chain puts back."""
    saved = {}
    for i, b in enumerate(chain):
        pb = arm.pose.bones[b]
        saved[b] = {a: getattr(pb, a) for a in _IK_ATTRS}
        for a, v in rigs.ik_joint_settings(bend_axis, keep_twist, root=i == 0).items():
            setattr(pb, a, v)
    return saved


def _unlimit_chain(arm, saved):
    for b, attrs in saved.items():
        pb = arm.pose.bones[b]
        for a, v in attrs.items():
            setattr(pb, a, v)


def _solve(context, arm, chain, target_world):
    """Pose `chain` so its tip (tail of the last bone) reaches target_world. Leaves the
    solved rotations in the bones' basis. Returns how far the tip ends from the target."""
    empty = bpy.data.objects.new("MIDIANIM_IK_target", None)
    context.scene.collection.objects.link(empty)
    empty.location = target_world
    tip = arm.pose.bones[chain[-1]]
    con = tip.constraints.new("IK")
    con.target = empty
    con.chain_count = len(chain)
    con.use_tail = True
    con.use_stretch = False
    try:
        context.view_layer.update()
        dg = context.evaluated_depsgraph_get()
        ev = arm.evaluated_get(dg)
        solved = [ev.pose.bones[b].matrix.copy() for b in chain]
    finally:
        tip.constraints.remove(con)
        bpy.data.objects.remove(empty)
    for b, m in zip(chain, solved):           # root first: each child sees its parent's new pose
        arm.pose.bones[b].matrix = m
        context.view_layer.update()
    return ((arm.matrix_world @ arm.pose.bones[chain[-1]].tail) - target_world).length


def _restore(arm, snapshot):
    for (path, idx), v in snapshot.items():
        owner, prop = path.rsplit(".", 1)
        getattr(arm.path_resolve(owner), prop)[idx] = v


def autoassign(context, s, only_slot=None):
    """Returns (created, skipped_locked, problems, rest_message)."""
    arm = s.rig
    prof = state.profile(s)
    bones = rig.finger_bones(s)
    markers = rig.find_markers()
    created, skipped, problems = 0, 0, []

    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    for slot in prof.slots:
        if only_slot and slot.id != only_slot:
            continue
        chain = bones.get(slot.id)
        if not chain:
            problems.append(f"{slot.label}: no bones")
            continue
        finger = next((f for f in s.fingers if f.slot == slot.id), None)
        snapshot = {}
        for b in chain:
            snapshot.update(actions.bone_channels(arm.pose.bones[b]))
        worst = (0.0, "")
        saved_ik = _limit_chain(arm, chain, s.bend_axis, s.keep_twist)
        try:
            for key in slot.keys:
                marker = markers.get((slot.id, key))
                if marker is None:
                    continue
                mw = marker.matrix_world
                z = mw.to_3x3().col[2].normalized()
                for down in (True, False):
                    if not down and finger is not None and finger.up_pose is not None:
                        continue      # an authored Up pose replaces hover poses
                    name = pose_name(slot.id, key, down)
                    old = bpy.data.actions.get(name)
                    if old is not None and is_locked(old) and not s.force_autoassign:
                        skipped += 1
                        continue
                    _restore(arm, snapshot)
                    target = mw.translation.copy() if down else mw.translation + z * s.hover
                    miss = _solve(context, arm, chain, target)
                    if miss > worst[0]:
                        worst = (miss, f"{key} {'Down' if down else 'Up'}")
                    _save_pose(arm, name, chain)
                    created += 1
        finally:
            _unlimit_chain(arm, saved_ik)
            _restore(arm, snapshot)
        if not any((slot.id, k) in markers for k in slot.keys):
            problems.append(f"{slot.label}: no key markers")
        elif worst[0] > MISS_TOLERANCE:
            problems.append(f"{slot.label}: fingertip {worst[0] * 1000:.0f} mm off its target ({worst[1]}); "
                            f"check the Bend Axis, or move the marker within reach")
    context.view_layer.update()
    return created, skipped, problems, build_rest(s, bones)


def _hand_bones(s, bones):
    """The bones that carry the fingers (each chain's parent) and the hold's hand bones."""
    arm = s.rig
    in_fingers = {b for chain in bones.values() for b in chain}
    out = set()
    for chain in bones.values():
        parent = arm.pose.bones[chain[0]].parent
        if parent is not None:
            out.add(parent.name)
    for name in (s.hold_hand_l, s.hold_hand_r):
        if name and name in arm.pose.bones:
            out.add(name)
    return sorted(out - in_fingers)


def _up_pose(s, slot):
    """The pose a finger rests in: its authored Up pose, else its Up pose over the home key
    (the slot's first key), else over any other key that has one."""
    finger = next((f for f in s.fingers if f.slot == slot.id), None)
    if finger is not None and finger.up_pose is not None:
        return finger.up_pose
    for key in slot.keys:
        act = bpy.data.actions.get(pose_name(slot.id, key, False))
        if act is not None:
            return act
    return None


def build_rest(s, bones):
    """Build F.Rest: each finger up over its home key, plus the hand bones as they are now.
    It becomes the Rest pose unless the user picked another one. Returns a one-line message."""
    arm = s.rig
    old = bpy.data.actions.get(REST_NAME)
    auto = s.rest_pose is None or s.rest_pose == old
    if old is not None and is_locked(old) and not s.force_autoassign:
        if s.rest_pose is None:
            s.rest_pose = old
        return f"{REST_NAME} is locked, kept"
    values, as_posed = {}, []
    for slot in state.profile(s).slots:
        chain = bones.get(slot.id)
        if not chain:
            continue
        act = _up_pose(s, slot)
        vals = actions.pose_values(act, set(chain)) if act is not None else {}
        if not vals:
            as_posed.append(slot.label)
            for b in chain:
                vals.update(actions.bone_channels(arm.pose.bones[b]))
        values.update(vals)
    if not values:
        return "no Rest pose built (no finger bones)"
    for b in _hand_bones(s, bones):
        values.update(actions.bone_channels(arm.pose.bones[b]))
    act = _save_values(arm, REST_NAME, values)
    if auto:
        s.rest_pose = act
        msg = f"Rest pose: {REST_NAME}"
    else:
        msg = f"{REST_NAME} built, your Rest pose '{s.rest_pose.name}' is kept"
    if as_posed:
        msg += " (no Up pose yet, used as posed now: " + ", ".join(as_posed) + ")"
    return msg


def generated_poses(slot_id):
    prefix = f"F.{slot_id}."
    return sorted((a for a in bpy.data.actions if a.name.startswith(prefix)), key=lambda a: a.name)
