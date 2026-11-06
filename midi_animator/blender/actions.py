"""Action, keyframe and NLA helpers (slotted actions, Blender 4.4+ / 5.x)."""

import math

import bpy

NLA_PREFIX = "MIDI:"
GEN_PREFIX = "MIDI_"   # baked actions; removed when no longer used


def action_fcurves(action):
    if getattr(action, "layers", None) is not None and len(action.layers):
        from bpy_extras import anim_utils
        result = []
        for slot in action.slots:
            cb = anim_utils.action_get_channelbag_for_slot(action, slot)
            if cb:
                result.extend(cb.fcurves)
        return result
    return list(getattr(action, "fcurves", []))


def pose_values(action, bones=None):
    """{(data_path, index): value} at the action's first frame, optionally only for some bones."""
    f0 = action.frame_range[0]
    out = {}
    for fc in action_fcurves(action):
        if bones is not None and bone_of(fc.data_path) not in bones:
            continue
        out[(fc.data_path, fc.array_index)] = fc.evaluate(f0)
    return out


def bone_of(data_path):
    if data_path.startswith('pose.bones["'):
        return data_path[len('pose.bones["'):].split('"]', 1)[0]
    return None


def identity_value(data_path, index):
    if data_path.endswith("scale"):
        return 1.0
    if data_path.endswith("rotation_quaternion") and index == 0:
        return 1.0
    if data_path.endswith("rotation_axis_angle") and index == 2:
        return 1.0
    return 0.0


def rotation_prop(pb):
    return {"QUATERNION": "rotation_quaternion",
            "AXIS_ANGLE": "rotation_axis_angle"}.get(pb.rotation_mode, "rotation_euler")


def bone_channels(pb):
    """Current local (basis) values of a pose bone: {(data_path, index): value}."""
    base = f'pose.bones["{pb.name}"]'
    out = {}
    for prop in ("location", rotation_prop(pb), "scale"):
        for i, v in enumerate(getattr(pb, prop)):
            out[(f"{base}.{prop}", i)] = float(v)
    return out


def build_action(owner, name, channels, interpolation="BEZIER", fake_user=False, replace=False):
    """Create an action for `owner` (Object or Key) with channels
    [(data_path, index, [(frame, value), ...]), ...]. The owner's active action is restored."""
    old = bpy.data.actions.get(name)
    if old and (replace or old.users == 0):
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = fake_user
    ad = owner.animation_data or owner.animation_data_create()
    prev, prev_slot = ad.action, getattr(ad, "action_slot", None)
    ad.action = act
    interp = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}[interpolation]
    try:
        for data_path, index, pts in channels:
            group = bone_of(data_path) or "MIDI"
            if hasattr(act, "fcurve_ensure_for_datablock"):
                fc = act.fcurve_ensure_for_datablock(owner, data_path, index=index, group_name=group)
            else:
                fc = act.fcurves.new(data_path, index=index, action_group=group)
            kp = fc.keyframe_points
            kp.add(len(pts))
            kp.foreach_set("co", [c for p in pts for c in p])
            kp.foreach_set("interpolation", [interp] * len(pts))
            fc.update()
    finally:
        ad.action = prev
        if prev is not None and prev_slot is not None and hasattr(ad, "action_slot"):
            try:
                ad.action_slot = prev_slot
            except Exception:
                pass
    return act


def _assign_slot(strip, target):
    if not hasattr(strip, "action_slot") or strip.action_slot is not None:
        return
    slots = list(getattr(strip, "action_suitable_slots", []) or [])
    if not slots:
        slots = [s for s in strip.action.slots if s.target_id_type == target.id_type] or list(strip.action.slots)
    if slots:
        strip.action_slot = slots[0]


def push_strip(owner, track_name, action, blend_type="REPLACE"):
    ad = owner.animation_data or owner.animation_data_create()
    f0, f1 = action.frame_range
    s0 = math.floor(f0)
    tr = ad.nla_tracks.new()
    tr.name = f"{NLA_PREFIX} {track_name}"
    strip = tr.strips.new(track_name, int(s0), action)
    _assign_slot(strip, owner)
    strip.use_sync_length = False
    strip.action_frame_start = s0
    strip.action_frame_end = max(math.ceil(f1), s0 + 1)
    strip.blend_type = blend_type
    strip.extrapolation = "HOLD_FORWARD"
    return strip


def animated_ids(objects):
    for obj in objects:
        yield obj
        sk = getattr(getattr(obj, "data", None), "shape_keys", None)
        if sk:
            yield sk


def clear_baked(ids):
    removed = 0
    for id_ in ids:
        ad = getattr(id_, "animation_data", None)
        if not ad:
            continue
        for tr in [t for t in ad.nla_tracks if t.name.startswith(NLA_PREFIX)]:
            ad.nla_tracks.remove(tr)
            removed += 1
    for a in [a for a in bpy.data.actions if a.name.startswith(GEN_PREFIX) and a.users == 0]:
        bpy.data.actions.remove(a)
    return removed


def push_active_down(id_):
    """Move the user's active action (e.g. an idle) into a 'Base:' NLA track. New NLA tracks
    are added on top, so this must run before any MIDI track is created for this ID."""
    ad = id_.animation_data
    if not ad or ad.action is None:
        return
    act = ad.action
    if act.name.startswith(GEN_PREFIX):
        ad.action = None
        return
    tr = ad.nla_tracks.new()
    tr.name = f"Base: {act.name}"
    strip = tr.strips.new(act.name, int(act.frame_range[0]), act)
    _assign_slot(strip, id_)
    ad.action = None
