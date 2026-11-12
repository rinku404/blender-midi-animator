"""Breathing: one baked breath signal moves the ribcage, belly, shoulders and torso through drivers.

- The breath is a custom property on the rig, `breath_lung` (0 empty .. 1 full). Bake writes it from
  the "Breathing" effect (Lung mode: the breath planner of core/signal.py), like any Property effect.
- Drivers on the body bones read that property and the sliders on Scene.midi_animator (a master
  Intensity and one slider per part). They are live: nothing is baked into the bones, so a slider
  moves the body at once, also while the animation plays.
- Which bone axis is depth, width and up is read from the bone's rest orientation in the world
  (core/breathing.py), so a Rigify rig and an FBX rig with sideways spine bones breathe alike.
- The ribcage's children (neck, shoulders) and the spine bone below the ribcage stop inheriting
  scale, so the head and arms keep their size (ADR 0014).
"""

import json
import math

import bpy
from mathutils import Quaternion, Vector

from ..core import breathing as geom
from . import hold, state

LUNG = "breath_lung"
SETUP = "midianim_breath"           # on the rig: JSON of everything Add Breathing changed
INHERIT = hold.BREATH_INHERIT_PROP  # on a bone: its Inherit Scale before Add Breathing
EFFECT = "Breathing"
PARTS = ("chest", "belly", "shoulders", "torso")
RAD = math.pi / 180.0
UP = (0.0, 0.0, 1.0)


def is_set_up(s):
    return bool(s.rig and SETUP in s.rig)


def _setup_info(arm):
    try:
        return json.loads(arm.get(SETUP, "{}"))
    except ValueError:
        return {}


def _world_axes(arm, bone):
    m = arm.matrix_world.to_3x3() @ bone.matrix_local.to_3x3()
    return [tuple(m.col[i].normalized()) for i in range(3)]


def _world_head(arm, bone):
    return tuple(arm.matrix_world @ bone.head_local)


def _shoulder(pb, ribs_name):
    """The bone of a hand's ancestors that hangs from the ribcage (the shoulder or clavicle)."""
    b = pb
    while b is not None:
        if b.parent is not None and b.parent.name == ribs_name:
            return b
        b = b.parent
    return None


def _body_frame(s, shoulders):
    """(forward, side, how) in world space, from the left and right shoulder (or hand) bones."""
    arm = s.rig
    pair = shoulders if all(shoulders) else None
    if pair is None:
        pair = [arm.data.bones[n] for n in (s.hold_hand_l, s.hold_hand_r)]
    frame = geom.body_frame(_world_head(arm, pair[0]), _world_head(arm, pair[1]))
    how = "from the left and right " + ("shoulders" if all(shoulders) else "hands")
    if frame is None:
        f = tuple(hold.player_forward(s))
        up = UP
        side = geom._cross(f, up)
        return f, side, "from the rig's -Y (no spread between left and right)"
    forward = frame[0]
    if s.instrument is not None:
        ribs = _world_head(arm, arm.data.bones[s.hold_strap_bone])
        turned = geom.face_the_instrument(forward, ribs, tuple(s.instrument.matrix_world.translation))
        if turned != forward:
            how += ", turned round to face the instrument"
            forward = turned
            frame = (forward, tuple(-c for c in frame[1]), UP)
    return forward, frame[1], how


def _inherit_none(arm, name, saved):
    bone = arm.data.bones[name]
    if INHERIT not in bone:
        # while locked, the hold already holds the original (its own restore would undo ours otherwise)
        bone[INHERIT] = bone.get(hold.INHERIT_PROP, bone.inherit_scale)
    bone.inherit_scale = "NONE"
    saved.append(name)


def _euler_xyz(pb):
    """Switch the bone to XYZ Euler rotation (keeping its pose) and return its rotation."""
    if pb.rotation_mode == "QUATERNION":
        e = pb.rotation_quaternion.to_euler("XYZ")
    elif pb.rotation_mode == "AXIS_ANGLE":
        a = pb.rotation_axis_angle
        e = Quaternion(a[1:], a[0]).to_euler("XYZ")
    else:
        e = pb.rotation_euler.copy()
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = e
    return tuple(e)


def _drive(arm, scene, path, index, expr, part):
    fc = arm.driver_add(path, index)
    d = fc.driver
    d.type = "SCRIPTED"
    for v in list(d.variables):
        d.variables.remove(v)
    for name, id_type, idb, data_path in (
            ("lung", "OBJECT", arm, f'["{LUNG}"]'),
            ("master", "SCENE", scene, "midi_animator.breath_intensity"),
            ("part", "SCENE", scene, f"midi_animator.breath_{part}")):
        v = d.variables.new()
        v.name, v.type = name, "SINGLE_PROP"
        v.targets[0].id_type, v.targets[0].id = id_type, idb
        v.targets[0].data_path = data_path
    d.expression = expr
    for m in list(fc.modifiers):
        fc.modifiers.remove(m)
    return (path, index)


def _spine_chain(arm, ribs_name):
    """(middle, lower): the two bones below the ribcage, nearest first (None where the rig has none)."""
    ribs = arm.pose.bones[ribs_name]
    middle = ribs.parent
    lower = middle.parent if middle is not None else None
    return middle, lower


def old_lung_effects(s, arm):
    """Enabled Lung-mode Bone effects on the rig other than Breathing: the old Chest preset's kind,
    which would move the same body a second time."""
    return [e for e in s.effects if e.enabled and e.name != EFFECT and e.mode == "LUNG"
            and e.target_type == "BONE" and e.target == arm]


def remove(context, s):
    """Take the breathing off the rig: drivers, rest pose of the bones, scale inheritance, the effect."""
    arm = s.rig
    info = _setup_info(arm) if arm else {}
    for path, index in info.get("drivers", []):
        try:
            arm.driver_remove(path, index)
        except TypeError:
            pass
    for name, rest in info.get("rest", {}).items():
        pb = arm.pose.bones.get(name)
        if pb is not None:
            pb.scale = (1.0, 1.0, 1.0)
            if "rotation" in rest:
                pb.rotation_euler = rest["rotation"]
    for bone in arm.data.bones if arm else ():
        if INHERIT in bone:
            if hold.INHERIT_PROP not in bone:       # locked: Unlock gives the original back
                bone.inherit_scale = bone[INHERIT]
            del bone[INHERIT]
    if arm and SETUP in arm:
        del arm[SETUP]
    if arm and LUNG in arm:
        del arm[LUNG]
    for e in s.effects:                         # give back the effects Add Breathing turned off
        if e.name in info.get("turned_off", []):
            e.enabled = True
    for i in reversed(range(len(s.effects))):
        if s.effects[i].name == EFFECT:
            s.effects.remove(i)
    s.effect_index = max(0, min(s.effect_index, len(s.effects) - 1))
    if arm and arm.animation_data:
        for tr in [t for t in arm.animation_data.nla_tracks if t.name == f"MIDI: {EFFECT}"]:
            arm.animation_data.nla_tracks.remove(tr)
    context.view_layer.update()
    return "Breathing removed"


def setup(context, s):
    """Set up the body motion on the rig (safe to repeat). Returns a one-line summary. Raises
    RuntimeError with what to fix when it can't."""
    arm, scene = s.rig, context.scene
    if arm is None or arm.type != "ARMATURE":
        raise RuntimeError("Set the Character Rig first")
    if not (s.hold_strap_bone and s.hold_hand_l and s.hold_hand_r):
        hold.guess_bones(s)
    for label, name in (("Strap (upper chest)", s.hold_strap_bone), ("Left hand", s.hold_hand_l),
                        ("Right hand", s.hold_hand_r)):
        if name not in arm.pose.bones:
            raise RuntimeError(f"{label} bone '{name}' not found on {arm.name}: pick it in panel 1 "
                               "(Hold the Instrument) or press Guess Bones")
    if context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    if is_set_up(s):
        remove(context, s)
    context.view_layer.update()

    pb, bones = arm.pose.bones, arm.data.bones
    ribs_name = s.hold_strap_bone
    middle, lower = _spine_chain(arm, ribs_name)
    belly = lower or middle
    shoulders = [_shoulder(pb[n], ribs_name) for n in (s.hold_hand_l, s.hold_hand_r)]
    # a shoulder that is the arm's own IK root (no clavicle) would just be re-solved by the IK: no lift
    lifts = [sh if sh is not None and sh != hold._arm_root(pb[h]) else None
             for sh, h in zip(shoulders, (s.hold_hand_l, s.hold_hand_r))]
    forward, side, how = _body_frame(s, [sh.bone if sh else None for sh in shoulders])
    notes = [f"front {how}"]

    # the signal and its sliders
    arm[LUNG] = 0.5
    arm.id_properties_ui(LUNG).update(min=0.0, max=1.0, description="Air in the lungs, baked from the "
                                      "breath (set by Bake; the Breathing sliders scale its effect)")
    info = {"drivers": [], "rest": {}, "inherit": []}
    saved = []

    def axes(name):
        return _world_axes(arm, bones[name])

    # no head or arm growth: neck and shoulders keep their size, the belly swell stays in the belly
    for child in bones[ribs_name].children:
        _inherit_none(arm, child.name, saved)
    if lower is not None:
        _inherit_none(arm, middle.name, saved)
    else:                                   # one spine bone: it is the belly, the ribcage must not inherit it
        _inherit_none(arm, ribs_name, saved)
    info["inherit"] = saved

    def drive_scale(name, axis, amount, part):
        pb[name].scale = (1.0, 1.0, 1.0)
        info["rest"].setdefault(name, {})
        info["drivers"].append(_drive(arm, scene, f'pose.bones["{name}"].scale', axis,
                                      f"1 + {amount:.6f} * lung * part * master", part))

    def drive_rotation(name, axis, expr_from_rest, part):
        rest = _euler_xyz(pb[name])
        info["rest"][name] = {"rotation": list(rest)}
        info["drivers"].append(_drive(arm, scene, f'pose.bones["{name}"].rotation_euler', axis,
                                      expr_from_rest(rest[axis]), part))

    depth, width, _ = geom.pick_axes(axes(ribs_name), forward, side, UP)
    drive_scale(ribs_name, depth, geom.CHEST_DEPTH, "chest")
    drive_scale(ribs_name, width, geom.CHEST_WIDTH, "chest")
    notes.append(f"ribcage {ribs_name}: depth = local {'XYZ'[depth]}, width = local {'XYZ'[width]}")
    if belly is not None:
        bdepth = geom.pick_axes(axes(belly.name), forward, side, UP)[0]
        drive_scale(belly.name, bdepth, geom.BELLY_DEPTH, "belly")
        notes.append(f"belly {belly.name}: depth = local {'XYZ'[bdepth]}")
    for bone, full, empty in ((middle, geom.TORSO_FULL, geom.TORSO_EMPTY),
                              (lower, geom.TORSO_FULL * geom.LOWER_FRACTION,
                               geom.TORSO_EMPTY * geom.LOWER_FRACTION)):
        if bone is None:
            continue
        ax, sign = geom.lean_back_axis(axes(bone.name), UP, forward)
        lo, hi = sign * empty * RAD, sign * full * RAD
        drive_rotation(bone.name, ax, lambda r, lo=lo, hi=hi:
                       f"{r:.6f} + ({lo:.6f} + {hi - lo:.6f} * lung) * part * master", "torso")
    for sh in lifts:
        if sh is None:
            continue
        child = sh.children[0].bone.head_local if sh.children else sh.bone.tail_local
        d = arm.matrix_world.to_3x3() @ (Vector(child) - sh.bone.head_local)
        ax, sign = geom.lift_axis(axes(sh.name), tuple(d.normalized()) if d.length > 1e-9 else side, UP)
        drive_rotation(sh.name, ax, lambda r, k=sign * geom.SHOULDER_LIFT * RAD:
                       f"{r:.6f} + {k:.6f} * lung * part * master", "shoulders")
    if not all(lifts):
        notes.append("no shoulder bone above the upper arm on every side: no shoulder lift there")
    old = old_lung_effects(s, arm)
    for e in old:
        e.enabled = False
    info["turned_off"] = [e.name for e in old]
    if old:
        notes.append("turned off the old " + ", ".join(e.name for e in old) + " effect"
                     + ("s" if len(old) > 1 else ""))
    arm[SETUP] = json.dumps(info)

    # the effect that bakes the signal
    e = next((x for x in s.effects if x.name == EFFECT), None) or s.effects.add()
    e.name, e.enabled = EFFECT, True
    e.target_type, e.target = "PROPERTY", arm
    e.data_path, e.array_index = f'["{LUNG}"]', 0
    e.mode, e.source, e.cc_number = "LUNG", "CC", 2
    e.out_min, e.out_max, e.attack, e.release = 0.0, 1.0, 0.15, 0.4
    e.blend_type = "REPLACE"
    s.effect_index = list(s.effects).index(e)
    arm.update_tag()
    context.view_layer.update()
    return "Breathing added (" + "; ".join(notes) + "). Bake to animate it"
