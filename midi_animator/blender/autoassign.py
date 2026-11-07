"""Autoassign: solve each finger onto its key markers with a temporary IK constraint and save
the result as pose assets ("F.<slot>.<key>.Down" / ".Up").

Generated poses remember a fingerprint of their values. If you edit a pose (or lock it by
hand), Autoassign leaves it alone unless "Overwrite Locked" is on.
"""

import hashlib

import bpy

from . import actions, rig, state

GEN_PROP = "midianim_generated"
HASH_PROP = "midianim_hash"
LOCK_PROP = "midianim_locked"


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
    chans = [(p, i, [(1.0, v)]) for (p, i), v in sorted(values.items())]
    act = actions.build_action(arm, name, chans, "CONSTANT", fake_user=True, replace=True)
    if act.asset_data is None:
        act.asset_mark()
    act[GEN_PROP] = True
    act[HASH_PROP] = _fingerprint(actions.pose_values(act))
    act[LOCK_PROP] = False
    return act


def _solve(context, arm, chain, target_world):
    """Pose `chain` so its tip (tail of the last bone) reaches target_world. Leaves the
    solved rotations in the bones' basis."""
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


def _restore(arm, snapshot):
    for (path, idx), v in snapshot.items():
        owner, prop = path.rsplit(".", 1)
        getattr(arm.path_resolve(owner), prop)[idx] = v


def autoassign(context, s, only_slot=None):
    """Returns (created, skipped_locked, problems)."""
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
                _solve(context, arm, chain, target)
                _save_pose(arm, name, chain)
                created += 1
        _restore(arm, snapshot)
        if not any((slot.id, k) in markers for k in slot.keys):
            problems.append(f"{slot.label}: no key markers")
    context.view_layer.update()
    return created, skipped, problems


def generated_poses(slot_id):
    prefix = f"F.{slot_id}."
    return sorted((a for a in bpy.data.actions if a.name.startswith(prefix)), key=lambda a: a.name)
