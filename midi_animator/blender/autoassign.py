"""Autoassign: solve each finger onto its key markers with a temporary IK constraint and save
the result as pose assets ("F.<slot>.<key>.Down" / ".Up").

While solving, each finger joint only turns around the rig's Bend Axis and only in the curling
direction (the knuckle may also spread sideways, plus the Knuckle Swing along the instrument,
and the thumb's base joint may turn by Thumb Turn about its own length), so fingers neither
twist nor bend backwards (ADR 0015). The bones' own IK settings are put back afterwards.

A pose whose fingertip ends more than MISS_TOLERANCE from its target remembers the miss and
which way to move the hand (panel 2 lists it next to the pose).

Autoassign also builds "F.Rest": every finger hovering over its home key, plus the hand bones
as they are now. It becomes the Rest pose unless you picked your own.

Hands with fewer fingers: a slot that shares another slot's bones is solved with that chain onto
its own markers (pose names stay per slot and key). A slot with a Press Tilt (a thumb on a hand
without a thumb bone) gets no IK: its Down poses turn the first bone by the tilt around the Bend
Axis, its Up poses are the bone as posed now. A slot with no bones is skipped.

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
MISS_PROP = "midianim_miss_mm"       # how far the pose's fingertip ended from its target (only if it misses)
ADVICE_PROP = "midianim_miss_advice"
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


def _limit_chain(arm, chain, bend_axis, keep_twist, swing_deg=0.0, turn_deg=0.0):
    """Give the chain's bones bend-only IK settings; the root also gets the knuckle swing
    (fingers) or the base turn (thumb). Returns what _unlimit_chain puts back."""
    saved = {}
    for i, b in enumerate(chain):
        pb = arm.pose.bones[b]
        saved[b] = {a: getattr(pb, a) for a in _IK_ATTRS}
        st = rigs.ik_joint_settings(bend_axis, keep_twist, root=i == 0, swing_deg=swing_deg, turn_deg=turn_deg)
        for a, v in st.items():
            setattr(pb, a, v)
    return saved


def _unlimit_chain(arm, saved):
    for b, attrs in saved.items():
        pb = arm.pose.bones[b]
        for a, v in attrs.items():
            setattr(pb, a, v)


def _solve(context, arm, chain, target_world):
    """Pose `chain` so its tip (tail of the last bone) reaches target_world. Leaves the
    solved rotations in the bones' basis. Returns the miss: target minus where the tip ends."""
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
    return target_world - (arm.matrix_world @ arm.pose.bones[chain[-1]].tail)


def _restore(arm, snapshot):
    for (path, idx), v in snapshot.items():
        owner, prop = path.rsplit(".", 1)
        getattr(arm.path_resolve(owner), prop)[idx] = v


def _tilt_poses(arm, s, slot, finger, bone):
    """Poses for a tilt slot (a thumb standing in as the hand's tilt): every key's Down is `bone`
    turned by the finger's tilt around the Bend Axis, Up is the bone as posed now. Rotation
    channels only, so the hand's location and the user's own keys stay untouched.
    Returns (created, skipped_locked)."""
    pb = arm.pose.bones[bone]
    base = f'pose.bones["{bone}"]'
    up_vals = actions.rotation_channels(pb, base)
    down_vals = actions.rotation_channels(pb, base, rigs.tilt_rotation(s.bend_axis, finger.tilt))
    created = skipped = 0
    for key in slot.keys:
        for down in (True, False):
            if not down and finger.up_pose is not None:
                continue
            name = pose_name(slot.id, key, down)
            old = bpy.data.actions.get(name)
            if old is not None and is_locked(old) and not s.force_autoassign:
                skipped += 1
                continue
            _save_values(arm, name, down_vals if down else up_vals)
            created += 1
    return created, skipped


def _set_miss(act, miss_vec, up, out):
    """Store how far this pose's fingertip ends from its target, and the advice, on the pose."""
    mm = miss_vec.length * 1000
    if mm * 0.001 > MISS_TOLERANCE:
        act[MISS_PROP] = round(mm, 1)
        act[ADVICE_PROP] = rigs.miss_advice(tuple(miss_vec), up, tuple(out))
    else:
        for p in (MISS_PROP, ADVICE_PROP):
            if p in act:
                del act[p]


def misses(slot_id):
    """[(pose name, mm, advice)] for this finger's generated poses that miss their target, as
    the last Autoassign left them (a locked pose keeps what it had)."""
    return [(a.name, a[MISS_PROP], a.get(ADVICE_PROP, "")) for a in generated_poses(slot_id)
            if a.get(MISS_PROP)]


def tube_up(prof, markers):
    """Unit vector up the instrument (toward the mouthpiece) from the key markers, or None."""
    rank = {sl.id: i for i, sl in enumerate(prof.slots)}
    pts = [(rank.get(sl, 0), tuple(m.matrix_world.translation)) for (sl, _), m in markers.items()]
    return rigs.tube_axis(pts)


def autoassign(context, s, only_slot=None):
    """Returns (created, skipped_locked, problems, rest_message). problems: one line per finger."""
    arm = s.rig
    prof = state.profile(s)
    bones = rig.finger_bones(s)
    context.view_layer.update()          # markers moved from a script: read their new matrices
    markers = rig.find_markers()
    created, skipped, problems = 0, 0, []
    up = tube_up(prof, markers)

    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    tilt_slots = rig.tilt_slots(s)
    for slot in prof.slots:
        if only_slot and slot.id != only_slot:
            continue
        chain = bones.get(slot.id)
        if not chain:
            continue                  # not animated (Analyze says so); shared slots have a chain
        finger = next((f for f in s.fingers if f.slot == slot.id), None)
        if slot.id in tilt_slots:
            try:
                n_created, n_locked = _tilt_poses(arm, s, slot, finger, chain[0])
            except ValueError as e:
                problems.append(f"{slot.label}: {e}")
                continue
            created += n_created
            skipped += n_locked
            continue
        snapshot = {}
        for b in chain:
            snapshot.update(actions.bone_channels(arm.pose.bones[b]))
        worst = (0.0, "", "")
        n_miss = n_solved = 0
        thumb = slot.finger == "thumb"
        saved_ik = _limit_chain(arm, chain, s.bend_axis, s.keep_twist,
                                0.0 if thumb else s.knuckle_swing, s.thumb_turn if thumb else 0.0)
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
                    miss_vec = _solve(context, arm, chain, target)
                    miss = miss_vec.length
                    act = _save_pose(arm, name, chain)
                    _set_miss(act, miss_vec, up, z)
                    n_solved += 1
                    if miss > MISS_TOLERANCE:
                        n_miss += 1
                    if miss > worst[0]:
                        worst = (miss, f"{key} {'Down' if down else 'Up'}", act.get(ADVICE_PROP, ""))
                    created += 1
        finally:
            _unlimit_chain(arm, saved_ik)
            _restore(arm, snapshot)
        if not any((slot.id, k) in markers for k in slot.keys):
            problems.append(f"{slot.label}: no key markers")
        elif worst[0] > MISS_TOLERANCE:
            problems.append(f"{slot.label}: {n_miss} of {n_solved} poses miss; worst {worst[1]}, "
                            f"{worst[0] * 1000:.0f} mm off: {worst[2]}")
    context.view_layer.update()
    return created, skipped, problems, build_rest(s, bones)


def status_line(created, skipped, problems):
    """The short status-bar line: "32 poses; 3 fingers miss: see panel 2"."""
    msg = f"{created} poses"
    if skipped:
        msg += f", {skipped} locked kept"
    if problems:
        n = len(problems)
        msg += f"; {n} {'finger misses' if n == 1 else 'fingers miss'}: see panel 2 (details in the Info log)"
    return msg


def report_lines(s, problems, rest_msg):
    """The Info log lines: the Rest pose message, then each finger's summary followed by every
    pose of it that misses, with its advice."""
    lines = [rest_msg]
    labels = {sl.label: sl.id for sl in state.profile(s).slots}
    for p in problems:
        lines.append(p)
        slot = labels.get(p.split(":", 1)[0])
        for name, mm, advice in misses(slot) if slot else ():
            lines.append(f"    {name}: {mm:.0f} mm off; {advice}")
    return lines


def _hand_bones(s, bones):
    """The bones that carry the fingers (each chain's parent) and the hold's hand bones."""
    arm = s.rig
    in_fingers = {b for chain in bones.values() for b in chain}
    out = set()
    tilt = rig.tilt_slots(s)
    for slot, chain in bones.items():
        if slot in tilt:
            continue              # a tilt slot's bone is the hand itself; its parent is the forearm
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
    values, as_posed, seen = {}, [], set()
    for slot in state.profile(s).slots:
        chain = bones.get(slot.id)
        if not chain or tuple(chain) in seen:
            continue                  # a shared chain rests over the first listed slot's home key
        seen.add(tuple(chain))
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
