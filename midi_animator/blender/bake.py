"""Bake fingering and blow effects into 'MIDI: …' NLA tracks."""

import math

import bpy
from mathutils import Quaternion, Vector

from ..core import fingering as core_fing
from ..core import rigs
from ..core import signal as core_signal
from . import actions, autoassign, breathing, hold, rig, state


# ---------------------------------------------------------------------------
# Fingering
# ---------------------------------------------------------------------------

def _hand_bones(s, slot_bones):
    """Bones keyed by the Rest pose or whole-hand override poses that belong to no finger."""
    in_fingers = {b for bones in slot_bones.values() for b in bones}
    extra = set()
    for act in [s.rest_pose] + [m.pose for m in s.notes if m.pose]:
        if act is None:
            continue
        for fc in actions.action_fcurves(act):
            b = actions.bone_of(fc.data_path)
            if b and b not in in_fingers and b in s.rig.pose.bones:
                extra.add(b)
    return sorted(extra)


class _Resolver:
    """Turns a (slot, state) into bone values, with fallbacks and warnings."""

    def __init__(self, s, slot_bones, homes):
        self.s, self.slot_bones, self.homes = s, slot_bones, homes
        self.cache, self.missing = {}, set()
        self.up_override = {f.slot: f.up_pose for f in s.fingers if f.up_pose}

    def _from(self, act, bones):
        return actions.pose_values(act, set(bones)) if act else {}

    def values(self, slot, st):
        key = (slot, st)
        if key in self.cache:
            return self.cache[key]
        bones = self.slot_bones[slot]
        kind = st[0]
        vals = {}
        if kind == "down":
            name = autoassign.pose_name(slot, st[1], True)
            act = bpy.data.actions.get(name)
            if act is None:
                self.missing.add(name)
            vals = self._from(act, bones)
        elif kind == "up" and slot != core_fing.HAND:
            if slot in self.up_override:
                vals = self._from(self.up_override[slot], bones)
            else:
                act = (bpy.data.actions.get(autoassign.pose_name(slot, st[1], False))
                       or bpy.data.actions.get(autoassign.pose_name(slot, self.homes.get(slot), False)))
                if act is None:
                    self.missing.add(autoassign.pose_name(slot, st[1], False))
                vals = self._from(act, bones)
        elif kind == "rest":
            vals = self._from(self.s.rest_pose, bones)
        elif kind == "pose":
            vals = self._from(bpy.data.actions.get(st[1]), bones)
        if not vals and slot != core_fing.HAND and not (kind == "up"):
            vals = self.values(slot, ("up", self.homes.get(slot)))   # fall back to hovering
        self.cache[key] = vals
        return vals


def tilt_targets(s):
    """[(finger, hold target)] for tilt slots whose bone is locked to the instrument (hold.py).
    The Copy Rotation overrides a tilt keyed on the bone, so Bake keys it on the target too."""
    out = []
    bones = rig.finger_bones(s)
    for f in s.fingers:
        if f.slot in rig.tilt_slots(s):
            tgt = hold.rotation_target(s.rig, bones[f.slot][0])
            if tgt is not None:
                out.append((f, tgt))
    return out


def _bake_tilt_on_target(s, finger, tgt, keys):
    """Key the hold target's rotation: tilted while a key of the slot is down, as it is now
    otherwise. Returns a message, or None if the target's rotation mode can't be keyed."""
    base = actions.rotation_channels(tgt)
    try:
        down = actions.rotation_channels(tgt, tilt=rigs.tilt_rotation(s.bend_axis, finger.tilt))
    except ValueError as e:
        return f"{finger.label}: {e}"
    chans = [(p, i, [(f, (down if st[0] == "down" else base)[(p, i)]) for f, _, st in keys])
             for p, i in sorted(base)]
    act = actions.build_action(tgt, f"{actions.GEN_PREFIX}Tilt {tgt.name.split()[-1]}", chans, "BEZIER")
    actions.push_strip(tgt, "Fingering", act, "REPLACE")
    return None


def bake_fingering(scene, s, data):
    """Returns (notes_used, missing_pitches, missing_poses, warnings)."""
    arm = s.rig
    prof = state.profile(s)
    slot_bones = rig.finger_bones(s)
    groups = rig.share_groups(s)
    homes = {sl.id: sl.keys[0] for sl in prof.slots}
    hand = _hand_bones(s, slot_bones)
    if hand:
        slot_bones[core_fing.HAND] = hand
    slots = list(slot_bones)
    if not slots:
        return 0, [], ["no finger bones set"], []

    notes = [(state.frame_of(s, scene, n.start), state.frame_of(s, scene, n.end), n.pitch + s.transpose)
             for n in state.performer_notes(s, data)]
    params = core_fing.TimingParams(
        transition=s.transition, lift_lead=s.lift_lead,
        rest_gap=s.relax_after * state.fps(scene), use_rest=s.rest_pose is not None)
    tl = core_fing.build_timeline(notes, state.mapping_dict(s), slots, homes, params)
    # slots sharing one bone chain become one timeline per chain: (frame, slot, state)
    merged = core_fing.merge_shared(tl.keys, groups)
    res = _Resolver(s, slot_bones, homes)

    finger_chans, hand_chans, influence = [], [], []
    for chain_slot, keys in merged.items():
        if not keys:
            continue
        if chain_slot == core_fing.HAND:
            # Hand bones only follow Rest / override poses; in between, the strip's influence
            # drops to 0 so your own hand animation shows through.
            posed = [(sl, st) for _, sl, st in keys if st[0] in ("rest", "pose")]
            channels = sorted({ch for sl, st in posed for ch in res.values(sl, st)})
            last = {}
            pts = {ch: [] for ch in channels}
            for f, sl, st in keys:
                vals = res.values(sl, st) if st[0] in ("rest", "pose") else last
                last = vals or last
                for ch in channels:
                    pts[ch].append((f, vals.get(ch, actions.identity_value(*ch))))
                influence.append((f, 1.0 if st[0] in ("rest", "pose") else 0.0))
            hand_chans = [(p, i, pts[(p, i)]) for p, i in channels]
            continue
        channels = sorted({ch for _, sl, st in keys for ch in res.values(sl, st)})
        for ch in channels:
            pts = [(f, res.values(sl, st).get(ch, actions.identity_value(*ch))) for f, sl, st in keys]
            finger_chans.append((ch[0], ch[1], pts))

    if finger_chans:
        act = actions.build_action(arm, actions.GEN_PREFIX + "Fingering", finger_chans, "BEZIER")
        actions.push_strip(arm, "Fingering", act, "REPLACE")
    if hand_chans:
        act = actions.build_action(arm, actions.GEN_PREFIX + "Hand", hand_chans, "BEZIER")
        strip = actions.push_strip(arm, "Hand Poses", act, "REPLACE")
        strip.use_animated_influence = True
        for f, v in influence:
            strip.influence = v
            strip.keyframe_insert("influence", frame=f)
    warnings = []
    for finger, tgt in tilt_targets(s):
        keys = merged.get(finger.slot)
        if keys:
            problem = _bake_tilt_on_target(s, finger, tgt, keys)
            warnings += [problem] if problem else []
    return tl.notes_used, tl.missing, sorted(res.missing), warnings


# ---------------------------------------------------------------------------
# Blow effects
# ---------------------------------------------------------------------------

def effect_notes(s, e, data):
    """The notes an effect follows (the performer's, or its own track and channel)."""
    if e.own_source:
        return data.notes_for(e.track, e.channel_filter)
    return state.performer_notes(s, data)


def effect_source(s, e, data):
    """(events or None, notes or None, label, problem). problem is set when the effect
    must not be baked as configured."""
    track = e.track if e.own_source else s.performer_track
    chan = e.channel_filter if e.own_source else s.performer_channel
    notes = [(n.start, n.end, n.velocity) for n in effect_notes(s, e, data)]
    if e.source == "VELOCITY":
        return None, notes, "note velocity", None
    kind, num = ("CC", e.cc_number) if e.source == "CC" else ("AT", 0)
    events = data.controller_events(kind, num, track, chan)
    label = f"CC{num}" if kind == "CC" else "aftertouch"
    if len(events) >= 4:
        return events, None, label, None
    if e.if_missing == "VELOCITY":
        return None, notes, f"note velocity ({label} not in file)", None
    if e.if_missing == "OFF":
        return None, None, "off", f"{e.name}: {label} not in file, turned off"
    return None, None, "", f"{e.name}: {label} not in file — choose Use Velocity or Turn Off"


def _bone_channels(pb, channel, values):
    """[(data_path, index, values)] for a bone channel; values are deltas from rest."""
    base = f'pose.bones["{pb.name}"]'
    kind, axes = channel.split("_")
    idx = ["XYZ".index(a) for a in axes]
    if kind == "LOC":
        return [(f"{base}.location", i, values) for i in idx]
    if kind == "SCALE":
        return [(f"{base}.scale", i, [1.0 + v for v in values]) for i in idx]
    # rotation, values in degrees
    if pb.rotation_mode == "QUATERNION":
        axis = Vector([1.0 if i in idx else 0.0 for i in range(3)])
        quats = [Quaternion(axis, math.radians(v)) for v in values]
        return [(f"{base}.rotation_quaternion", c, [q[c] for q in quats]) for c in range(4)]
    if pb.rotation_mode == "AXIS_ANGLE":
        raise ValueError(f"bone '{pb.name}' uses Axis Angle rotation; switch it to Euler or Quaternion")
    return [(f"{base}.rotation_euler", i, [math.radians(v) for v in values]) for i in idx]


def effect_owner(e):
    obj = e.target
    if e.target_type == "SHAPE_KEY":
        sk = obj.data.shape_keys if obj and obj.type == "MESH" else None
        return sk
    return obj


def bake_effect(scene, s, e, data):
    """Returns (label, problem)."""
    events, notes, label, problem = effect_source(s, e, data)
    if problem:
        return label, problem
    fr = state.fps(scene)
    f0 = min(s.start_frame, s.start_frame + int(math.floor(s.time_offset * fr)))
    f1 = int(math.ceil(state.frame_of(s, scene, data.length))) + int(fr)
    if e.mode == "LUNG":                    # keep breathing slowly after the last note, to the scene's end
        f1 = max(f1, scene.frame_end)
    frames = list(range(f0, f1 + 1))
    times = [state.time_of(s, scene, f) for f in frames]
    params = core_signal.BlowParams(
        attack=e.attack, release=e.release, threshold=e.threshold, curve=e.curve,
        normalize=e.normalize, mode=e.mode, sustain=e.sustain, decay=e.decay)
    spans = [(n.start, n.end) for n in effect_notes(s, e, data)]
    x = core_signal.blow_curve(times, params, events=events, notes=notes, spans=spans)
    vals = core_signal.remap(x, e.out_min, e.out_max)

    obj = e.target
    if e.target_type == "SHAPE_KEY":
        owner = effect_owner(e)
        if owner is None or e.shape_key not in owner.key_blocks:
            return label, f"{e.name}: '{obj.name}' has no shape key '{e.shape_key}'"
        chans = [(f'key_blocks["{e.shape_key}"].value', 0, vals)]
    elif e.target_type == "BONE":
        owner = obj
        if obj.type != "ARMATURE" or e.bone not in obj.pose.bones:
            return label, f"{e.name}: choose a bone on an armature"
        try:
            chans = _bone_channels(obj.pose.bones[e.bone], e.channel, vals)
        except ValueError as err:
            return label, f"{e.name}: {err}"
    else:
        owner = obj
        try:
            obj.path_resolve(e.data_path)
        except Exception:
            return label, f"{e.name}: '{obj.name}' has no property '{e.data_path}'"
        chans = [(e.data_path, e.array_index, vals)]

    act = actions.build_action(owner, f"{actions.GEN_PREFIX}{e.name}",
                               [(p, i, list(zip(frames, v))) for p, i, v in chans], "LINEAR")
    actions.push_strip(owner, e.name, act, e.blend_type)
    return label, None


# ---------------------------------------------------------------------------
# Everything
# ---------------------------------------------------------------------------

def bake_all(context):
    """Returns (info messages, warnings)."""
    scene = context.scene
    s = scene.midi_animator
    data = state.load_midi(s)
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")

    effects = [e for e in s.effects if e.enabled and e.target]
    owners = []
    if s.fingering_enabled and s.rig:
        owners.append(s.rig)
        owners += [t for _, t in tilt_targets(s) if t not in owners]     # thumb tilt on a hold target
    for e in effects:
        o = effect_owner(e)
        if o is not None and o not in owners:
            owners.append(o)
    candidates = list(actions.animated_ids([o for o in owners if isinstance(o, bpy.types.Object)]))
    candidates += [o for o in owners if not isinstance(o, bpy.types.Object)]
    actions.clear_baked(set(candidates))
    if s.keep_active_actions:
        for o in owners:
            actions.push_active_down(o)

    msgs, warnings = [], []
    if s.fingering_enabled and s.rig:
        used, missing_notes, missing_poses, tilt_warnings = bake_fingering(scene, s, data)
        msgs.append(f"{used} fingered notes")
        warnings += tilt_warnings
        if missing_notes:
            warnings.append("unmapped notes: " + ", ".join(state.ui_name(p) for p in missing_notes))
        if missing_poses:
            shown = ", ".join(missing_poses[:6]) + (" …" if len(missing_poses) > 6 else "")
            warnings.append("missing poses (run Autoassign): " + shown)
    if any(e.name == breathing.EFFECT for e in effects) and s.rig:
        for e in breathing.old_lung_effects(s, s.rig):
            if e in effects:
                warnings.append(f"{e.name} is a Lung-mode bone effect and moves the body a second time "
                                "next to Breathing: untick it in the Blow list")
    for e in effects:
        label, problem = bake_effect(scene, s, e, data)
        if problem:
            warnings.append(problem)
        else:
            msgs.append(f"{e.name} ← {label}")
    scene.frame_set(scene.frame_current)
    return msgs, warnings
