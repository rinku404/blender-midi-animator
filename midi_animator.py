bl_info = {
    "name": "MIDI Animator",
    "author": "Paulo + Claude",
    "version": (0, 3, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar (N) > MIDI",
    "description": "Drive character and instrument animation from MIDI files: wind-instrument "
                   "fingering poses, breath-driven cheeks and bell, and note-triggered actions",
    "category": "Animation",
}

"""
MIDI Animator
=============

Bakes a MIDI file (for example a Roland Aerophone recording exported from Reaper) into
Blender animation, all as NLA tracks named "MIDI: ..." so it can be re-baked at any time.

* Fingering: each note holds a hand pose ("Fingering_<note>" actions, saxophone fingering),
  octave key layered on top, short rests hold, longer rests relax to "Fingering_Rest".
* Breath effects: the breath controller (auto-detected: CC2, CC11 or aftertouch; note velocity
  as fallback) drives a shape key (cheek puff), an object's scale (instrument bell) or any
  property (chest / sway bones), each with its own range, smoothing and curve.
* Note actions: generic "play this action when these notes play" (drums, piano, ...).

No external dependencies: the Standard MIDI File parser is built in.
"""

import bisect
import math
import os
import struct
from collections import defaultdict

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)

NLA_PREFIX = "MIDI:"
GEN_PREFIX = "MIDI_"          # generated actions, removed when no longer used
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_ALIAS = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}


def note_name(n):
    return f"{NOTE_NAMES[n % 12]}{n // 12 - 1}"


# ---------------------------------------------------------------------------
# Standard MIDI File parser (format 0/1, PPQ and SMPTE timing)
# ---------------------------------------------------------------------------

class MidiNote:
    __slots__ = ("track", "track_name", "channel", "pitch", "velocity", "start", "end")

    def __init__(self, track, track_name, channel, pitch, velocity, start, end):
        self.track = track
        self.track_name = track_name
        self.channel = channel      # 0-15
        self.pitch = pitch
        self.velocity = velocity
        self.start = start          # seconds
        self.end = end              # seconds

    @property
    def duration(self):
        return max(0.0, self.end - self.start)


class MidiData:
    """Parsed file. controllers: {(track, channel, kind, number): [(sec, value), ...]}
    where kind is "CC" (number = controller), "AT" (channel aftertouch) or "PAT" (poly aftertouch)."""

    def __init__(self, notes, tracks, controllers):
        self.notes = notes
        self.tracks = tracks
        self.controllers = controllers
        ends = [n.end for n in notes] + [ev[-1][0] for ev in controllers.values() if ev]
        self.length = max(ends, default=0.0)


def _read_vlq(data, pos):
    value = 0
    while True:
        b = data[pos]
        pos += 1
        value = (value << 7) | (b & 0x7F)
        if not b & 0x80:
            return value, pos


def parse_midi(path):
    with open(path, "rb") as f:
        data = f.read()

    if data[:4] != b"MThd":
        raise ValueError("Not a Standard MIDI File (missing MThd header)")
    hlen = struct.unpack(">I", data[4:8])[0]
    _fmt, ntracks, division = struct.unpack(">HHh", data[8:14])
    pos = 8 + hlen

    raw_tracks = []      # per track: list of (tick, kind, channel, a, b)
    tempo_events = []    # (tick, microseconds per quarter)
    track_names = []

    for t in range(ntracks):
        while pos + 8 <= len(data) and data[pos:pos + 4] != b"MTrk":
            pos += 8 + struct.unpack(">I", data[pos + 4:pos + 8])[0]
        if pos + 8 > len(data):
            break
        length = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        pos += 8
        end = min(pos + length, len(data))
        tick = 0
        status = 0
        events = []
        name = f"Track {t}"

        while pos < end:
            delta, pos = _read_vlq(data, pos)
            tick += delta
            b = data[pos]
            if b & 0x80:
                pos += 1
                if b < 0xF0:
                    status = b
            else:
                b = status  # running status

            if b == 0xFF:
                mtype = data[pos]
                mlen, pos = _read_vlq(data, pos + 1)
                payload = data[pos:pos + mlen]
                pos += mlen
                if mtype == 0x51 and mlen == 3:
                    tempo_events.append((tick, int.from_bytes(payload, "big")))
                elif mtype == 0x03:
                    name = payload.decode("latin-1", "replace").strip() or name
                elif mtype == 0x2F:
                    break
            elif b in (0xF0, 0xF7):
                slen, pos = _read_vlq(data, pos)
                pos += slen
            else:
                kind = b & 0xF0
                ch = b & 0x0F
                if kind in (0xC0, 0xD0):
                    d1 = data[pos]
                    pos += 1
                    if kind == 0xD0:
                        events.append((tick, "AT", ch, 0, d1))
                elif kind in (0x80, 0x90, 0xA0, 0xB0, 0xE0):
                    d1, d2 = data[pos], data[pos + 1]
                    pos += 2
                    if kind == 0x90 and d2 > 0:
                        events.append((tick, "on", ch, d1, d2))
                    elif kind == 0x80 or kind == 0x90:
                        events.append((tick, "off", ch, d1, 0))
                    elif kind == 0xB0:
                        events.append((tick, "CC", ch, d1, d2))
                    elif kind == 0xA0:
                        events.append((tick, "PAT", ch, 0, d2))
                else:
                    raise ValueError(f"Bad MIDI status byte 0x{b:02X} in track {t}")
        pos = end
        raw_tracks.append(events)
        track_names.append(name)

    # Tick -> seconds
    if division < 0:  # SMPTE
        fps = -(division >> 8)
        fps = 29.97 if fps == 29 else fps
        tpf = division & 0xFF

        def to_sec(tk):
            return tk / (fps * tpf)
    else:
        ppq = division
        tempo_events.sort(key=lambda e: e[0])
        seg_ticks, segs = [], []
        cur_tick, cur_sec, cur_tempo = 0, 0.0, 500000
        seg_ticks.append(0)
        segs.append((0, 0.0, 500000))
        for tk, tempo in tempo_events:
            cur_sec += (tk - cur_tick) * cur_tempo / (ppq * 1e6)
            cur_tick, cur_tempo = tk, tempo
            if seg_ticks[-1] == tk:
                segs[-1] = (tk, cur_sec, tempo)
            else:
                seg_ticks.append(tk)
                segs.append((tk, cur_sec, tempo))

        def to_sec(tk):
            s_tick, s_sec, tempo = segs[bisect.bisect_right(seg_ticks, tk) - 1]
            return s_sec + (tk - s_tick) * tempo / (ppq * 1e6)

    notes = []
    controllers = defaultdict(list)
    for ti, events in enumerate(raw_tracks):
        open_notes = defaultdict(list)
        for tick, kind, ch, a, b in events:
            if kind == "on":
                open_notes[(ch, a)].append((tick, b))
            elif kind == "off":
                if open_notes[(ch, a)]:
                    on_tick, on_vel = open_notes[(ch, a)].pop(0)
                    notes.append(MidiNote(ti, track_names[ti], ch, a, on_vel,
                                          to_sec(on_tick), to_sec(tick)))
            else:
                number = a if kind == "CC" else 0
                controllers[(ti, ch, kind, number)].append((to_sec(tick), b))
        for (ch, pitch), pending in open_notes.items():
            for on_tick, on_vel in pending:
                s = to_sec(on_tick)
                notes.append(MidiNote(ti, track_names[ti], ch, pitch, on_vel, s, s + 0.1))

    notes.sort(key=lambda n: (n.start, n.track, n.pitch))
    return MidiData(notes, track_names, dict(controllers))


# ---------------------------------------------------------------------------
# Breath / controller signal
# ---------------------------------------------------------------------------

# Most likely breath sources, best first. Aerophones send breath as a controller (CC2 by
# default on most wind controllers, CC11 expression or aftertouch depending on settings).
BREATH_PRIORITY = [("CC", 2), ("CC", 11), ("AT", 0), ("PAT", 0), ("CC", 7), ("CC", 1)]
IGNORED_CCS = {0, 6, 32, 38, 64, 98, 99, 100, 101, 120, 121, 123}


def _filter_ok(key, track, channel):
    t, ch, _kind, _num = key
    return (track < 0 or t == track) and (channel <= 0 or ch == channel - 1)


def detect_breath(midi, track=-1, channel=0):
    """Return the controller key that most likely carries breath, or None."""
    keys = [k for k, ev in midi.controllers.items()
            if _filter_ok(k, track, channel) and len(ev) >= 8 and len({v for _, v in ev}) > 2]
    if not keys:
        return None
    for kind, num in BREATH_PRIORITY:
        hits = [k for k in keys if k[2] == kind and k[3] == num]
        if hits:
            return max(hits, key=lambda k: len(midi.controllers[k]))
    others = [k for k in keys if not (k[2] == "CC" and k[3] in IGNORED_CCS)]
    return max(others, key=lambda k: len(midi.controllers[k])) if others else None


def describe_source(key):
    if key is None:
        return "none (note velocity fallback)"
    t, ch, kind, num = key
    label = {"CC": f"CC{num}", "AT": "Channel aftertouch", "PAT": "Poly aftertouch"}[kind]
    return f"{label} (track {t}, ch {ch + 1})"


def velocity_events(notes):
    ev = []
    for n in notes:
        ev.append((n.start, n.velocity))
        ev.append((n.end, 0))
    ev.sort(key=lambda e: (e[0], -e[1]))
    return ev


def sample_signal(events, times, attack, release):
    """Step-hold the events at the given times (seconds), then smooth with separate
    attack/release time constants. Returns raw 0-127 floats."""
    if not events:
        return [0.0] * len(times)
    ev_t = [e[0] for e in events]
    out = []
    y = None
    prev_t = None
    for t in times:
        i = bisect.bisect_right(ev_t, t) - 1
        x = float(events[i][1]) if i >= 0 else 0.0
        if y is None:
            y = x
        else:
            dt = max(t - prev_t, 1e-6)
            tau = attack if x > y else release
            a = 1.0 if tau <= 0 else 1.0 - math.exp(-dt / tau)
            y += (x - y) * a
        prev_t = t
        out.append(y)
    return out


# ---------------------------------------------------------------------------
# Action / keyframe helpers (work with legacy and slotted actions, 4.2 - 5.x)
# ---------------------------------------------------------------------------

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


def pose_values(action):
    """{(data_path, index): value} at the action's first frame."""
    f0 = action.frame_range[0]
    return {(fc.data_path, fc.array_index): fc.evaluate(f0) for fc in action_fcurves(action)}


def identity_value(data_path, index):
    if data_path.endswith("scale"):
        return 1.0
    if data_path.endswith("rotation_quaternion") and index == 0:
        return 1.0
    return 0.0


def _bone_group(data_path):
    if data_path.startswith('pose.bones["'):
        return data_path[len('pose.bones["'):].split('"]', 1)[0]
    return "MIDI"


def build_action(owner, name, channels, interpolation="BEZIER", fake_user=False, replace=False):
    """Create an action for `owner` (Object or Key) with channels:
    [(data_path, index, [(frame, value), ...]), ...]. The owner's active action is restored."""
    old = bpy.data.actions.get(name)
    if old and (replace or old.users == 0):
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = fake_user
    ad = owner.animation_data or owner.animation_data_create()
    prev = ad.action
    ad.action = act
    interp = {"CONSTANT": 0, "LINEAR": 1, "BEZIER": 2}[interpolation]
    try:
        for data_path, index, pts in channels:
            group = _bone_group(data_path)
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
    return act


def push_strip(owner, track_name, action, blend_type="REPLACE", influence=None):
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
    strip.extrapolation = "NOTHING"
    if influence is not None:
        strip.use_animated_influence = True
        strip.influence = influence
    return strip


def _assign_slot(strip, target):
    if not hasattr(strip, "action_slot") or strip.action_slot is not None:
        return
    slots = list(getattr(strip, "action_suitable_slots", []) or [])
    if not slots:
        slots = [s for s in strip.action.slots if s.target_id_type == target.id_type] or list(strip.action.slots)
    if slots:
        strip.action_slot = slots[0]


def animated_ids(objects):
    for obj in objects:
        yield obj
        sk = getattr(getattr(obj, "data", None), "shape_keys", None)
        if sk:
            yield sk


def has_midi_tracks(id_):
    ad = id_.animation_data
    return bool(ad and any(t.name.startswith(NLA_PREFIX) for t in ad.nla_tracks))


def clear_baked(objects):
    removed = 0
    for id_ in animated_ids(objects):
        ad = id_.animation_data
        if not ad:
            continue
        for tr in [t for t in ad.nla_tracks if t.name.startswith(NLA_PREFIX)]:
            ad.nla_tracks.remove(tr)
            removed += 1
    for a in [a for a in bpy.data.actions if a.name.startswith(GEN_PREFIX) and a.users == 0]:
        bpy.data.actions.remove(a)
    return removed


def push_active_down(id_):
    """Keep the user's active action (e.g. an idle) by moving it into a base NLA track,
    so it doesn't override the MIDI tracks (it's created before them, so it sits below)."""
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


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------

def _poll_anim_object(self, obj):
    return obj.type in {"ARMATURE", "MESH", "EMPTY", "CURVE", "CAMERA", "LIGHT"}


def _poll_armature(self, obj):
    return obj.type == "ARMATURE"


BLEND_ITEMS = [
    ("REPLACE", "Replace", "Use the value as is"),
    ("ADD", "Add", "Add on top of the animation below"),
    ("COMBINE", "Combine", "Combine (quaternion-aware) with the animation below"),
]


class MIDIANIM_Mapping(bpy.types.PropertyGroup):
    """Note -> action trigger (drums, piano, any one-shot gesture)."""
    name: StringProperty(name="Name", default="Mapping")
    enabled: BoolProperty(name="Enabled", default=True)
    track: IntProperty(name="Track", default=-1, min=-1, description="MIDI track index (-1 = any)")
    channel: IntProperty(name="Channel", default=0, min=0, max=16, description="1-16 (0 = any)")
    note_low: IntProperty(name="Note From", default=60, min=0, max=127)
    note_high: IntProperty(name="Note To", default=60, min=0, max=127)
    min_velocity: IntProperty(name="Min Velocity", default=1, min=1, max=127)
    target: PointerProperty(name="Target", type=bpy.types.Object, poll=_poll_anim_object)
    action: PointerProperty(name="Action", type=bpy.types.Action)
    mode: EnumProperty(
        name="Mode",
        items=[
            ("TRIGGER", "Trigger", "Play the action once at its natural speed for every note"),
            ("HOLD", "Stretch to Note", "Stretch the action to cover the note's length"),
            ("LOOP", "Loop While Held", "Repeat the action for as long as the note is held"),
        ],
        default="TRIGGER",
    )
    hit_frame: FloatProperty(name="Hit Frame", default=0.0,
                             description="Frame inside the action that lands on the note start")
    use_hit_frame: BoolProperty(name="Align Hit Frame", default=False)
    velocity_influence: BoolProperty(name="Velocity → Influence", default=False)
    blend_type: EnumProperty(name="Blend", items=BLEND_ITEMS, default="REPLACE")
    blend_frames: FloatProperty(name="Blend In/Out", default=2.0, min=0.0)


def _effect_type_update(self, context):
    if self.target_type == "SCALE":
        self.out_min, self.out_max = 1.0, 1.3
        self.blend_type = "REPLACE"
    elif self.target_type == "SHAPE_KEY":
        self.out_min, self.out_max = 0.0, 1.0
        self.blend_type = "REPLACE"
    else:
        self.out_min, self.out_max = 0.0, 0.05
        self.blend_type = "ADD"


class MIDIANIM_Effect(bpy.types.PropertyGroup):
    """Breath / controller -> shape key, scale or property."""
    name: StringProperty(name="Name", default="Effect")
    enabled: BoolProperty(name="Enabled", default=True)
    source: EnumProperty(
        name="Source",
        items=[
            ("AUTO", "Breath (auto-detect)", "Use the controller that looks like breath; note velocity if none"),
            ("CC", "Controller (CC)", "A specific MIDI CC number"),
            ("AT", "Aftertouch", "Channel aftertouch"),
            ("VELOCITY", "Note Velocity", "Velocity of each note, held for the note's length"),
        ],
        default="AUTO",
    )
    cc_number: IntProperty(name="CC", default=2, min=0, max=127)
    track: IntProperty(name="Track", default=-1, min=-1)
    channel: IntProperty(name="Channel", default=0, min=0, max=16)

    target: PointerProperty(name="Target", type=bpy.types.Object, poll=_poll_anim_object)
    target_type: EnumProperty(
        name="Drive",
        items=[
            ("SHAPE_KEY", "Shape Key", "A shape key value (e.g. CheekPuff)"),
            ("SCALE", "Scale", "The object's scale (e.g. the instrument bell)"),
            ("PROPERTY", "Property", "Any animatable property, e.g. a bone rotation"),
        ],
        default="SHAPE_KEY",
        update=_effect_type_update,
    )
    shape_key: StringProperty(name="Shape Key", default="CheekPuff")
    scale_axes: EnumProperty(
        name="Axes",
        items=[("XYZ", "XYZ", ""), ("X", "X", ""), ("Y", "Y", ""), ("Z", "Z", ""),
               ("XY", "XY", ""), ("XZ", "XZ", ""), ("YZ", "YZ", "")],
        default="XYZ",
    )
    base_scale: FloatVectorProperty(name="Rest Scale", default=(1.0, 1.0, 1.0), size=3,
                                    description="Scale at rest; captured automatically on the first bake")
    data_path: StringProperty(name="Data Path", default="",
                              description='e.g. pose.bones["spine.003"].rotation_euler')
    array_index: IntProperty(name="Index", default=0, min=0)

    out_min: FloatProperty(name="Min", default=0.0, description="Output with no breath")
    out_max: FloatProperty(name="Max", default=1.0, description="Output at full breath")
    threshold: FloatProperty(name="Threshold", default=0.05, min=0.0, max=0.95,
                             description="Ignore breath below this fraction (removes noise)")
    curve: FloatProperty(name="Curve", default=1.0, min=0.1, max=5.0,
                         description="<1 reacts early (soft breath shows), >1 only reacts to strong breath")
    attack: FloatProperty(name="Attack (s)", default=0.04, min=0.0, max=2.0,
                          description="How fast it grows when blowing harder")
    release: FloatProperty(name="Release (s)", default=0.15, min=0.0, max=3.0,
                           description="How fast it relaxes")
    normalize: BoolProperty(name="Normalize to Peak", default=True,
                            description="Treat the loudest breath in the recording as full breath")
    blend_type: EnumProperty(name="Blend", items=BLEND_ITEMS, default="REPLACE")


class MIDIANIM_Settings(bpy.types.PropertyGroup):
    midi_path: StringProperty(name="MIDI File", subtype="FILE_PATH")
    audio_path: StringProperty(name="Audio File", subtype="FILE_PATH")
    start_frame: IntProperty(name="Start Frame", default=1)
    time_offset: FloatProperty(name="Offset (s)", default=0.0,
                               description="Shift all MIDI by this many seconds")
    keep_active_actions: BoolProperty(
        name="Keep Active Actions as Base", default=True,
        description="Move targets' active actions (e.g. an idle) into a base NLA track so the MIDI "
                    "tracks play on top of them instead of being overridden")
    summary: StringProperty(default="")

    # Fingering
    fing_enabled: BoolProperty(name="Bake Fingering", default=True)
    fing_target: PointerProperty(name="Character Rig", type=bpy.types.Object, poll=_poll_armature)
    fing_prefix: StringProperty(name="Pose Prefix", default="Fingering_")
    fing_track: IntProperty(name="Track", default=-1, min=-1)
    fing_channel: IntProperty(name="Channel", default=0, min=0, max=16)
    transpose: IntProperty(name="Transpose", default=0, min=-48, max=48,
                           description="Semitones added to MIDI notes before picking the fingering "
                                       "(use if the Aerophone is set to an alto/tenor key)")
    use_octave_key: BoolProperty(name="Octave Key", default=True,
                                 description="Notes from written D5 up reuse the lower fingering plus "
                                             "the OctaveKey pose")
    transition: FloatProperty(name="Transition (frames)", default=2.0, min=0.0, max=12.0)
    rest_gap: FloatProperty(name="Relax After (s)", default=0.5, min=0.0,
                            description="Rests longer than this relax the hand to the Rest pose")
    fing_mode: EnumProperty(
        name="Fingering Mode",
        items=[
            ("CHART", "Per Finger (sax chart)",
             "Pose each finger pressed once; the built-in saxophone chart presses the right fingers "
             "for every note. Most natural: fingers stay on the keys and only press or lift"),
            ("POSES", "Whole-Hand Pose per Note",
             "Pose the whole hand once per note name (Fingering_C, Fingering_D, ...)"),
        ],
        default="CHART",
    )
    save_note: EnumProperty(name="Fingering", items=lambda s, c: CHART_ITEMS if s.fing_mode == "CHART" else FINGERING_ITEMS)
    fing_missing: StringProperty(default="")

    # Hold setup
    hold_instrument: PointerProperty(name="Instrument", type=bpy.types.Object,
                                     description="The saxophone body (the bell can stay its child)")
    hold_chest_bone: StringProperty(name="Strap Bone", description="Chest/neck bone the instrument hangs from")
    hold_hand_l: StringProperty(name="Left Hand", description="Left hand bone")
    hold_hand_r: StringProperty(name="Right Hand", description="Right hand bone")

    effects: CollectionProperty(type=MIDIANIM_Effect)
    effect_index: IntProperty(default=0)
    mappings: CollectionProperty(type=MIDIANIM_Mapping)
    active_index: IntProperty(default=0)


# ---------------------------------------------------------------------------
# Fingering logic
# ---------------------------------------------------------------------------

# Names you can save poses as. Pitch-class names cover the main sax octave (written D4-C#5,
# and D5-C#6 with the octave key). Octave-specific names override them (low Bb-C#, palm keys).
FINGERING_NAMES = (
    NOTE_NAMES
    + ["A#3", "B3", "C4", "C#4", "C5", "C#5", "D6", "D#6", "E6", "F6", "F#6"]
    + ["OctaveKey", "Rest"]
)
FINGERING_ITEMS = [(n, n + (f" ({FLAT_ALIAS[n[:2]]})" if n[:2] in FLAT_ALIAS else ""), "")
                   for n in FINGERING_NAMES]


# Per-finger mode: each element is one finger (all its joints) pressing its key(s). "Rest" is the
# hold pose with every finger resting on its key, nothing pressed. Fingers not pressed for a note
# stay at Rest, so only the fingers that change move.
CHART_ELEMENTS = [
    ("Rest", "Rest: hold pose, fingers on keys, nothing pressed"),
    ("L1", "L1: left index presses B key"),
    ("L2", "L2: left middle presses A key"),
    ("L3", "L3: left ring presses G key"),
    ("LP", "LP: left pinky presses G#/low B/Bb/C#"),
    ("R1", "R1: right index presses F key"),
    ("R2", "R2: right middle presses E key"),
    ("R3", "R3: right ring presses D key"),
    ("RP", "RP: right pinky presses low C/Eb"),
    ("OctaveKey", "OctaveKey: left thumb presses octave key"),
    ("Palm", "Palm: left hand palm keys (high D to F#)"),
]
CHART_ITEMS = [(n, label, "") for n, label in CHART_ELEMENTS]
_L123, _R123 = ("L1", "L2", "L3"), ("R1", "R2", "R3")
# Written saxophone pitch -> pressed elements (standard fingerings, main octave + low notes)
SAX_CHART = {
    58: _L123 + _R123 + ("LP",),   # low Bb
    59: _L123 + _R123 + ("LP",),   # low B
    60: _L123 + _R123 + ("RP",),   # low C
    61: _L123 + _R123 + ("LP",),   # low C#
    62: _L123 + _R123,             # D
    63: _L123 + _R123 + ("RP",),   # Eb
    64: _L123 + ("R1", "R2"),      # E
    65: _L123 + ("R1",),           # F
    66: _L123 + ("R2",),           # F#
    67: _L123,                     # G
    68: _L123 + ("LP",),           # G#
    69: ("L1", "L2"),              # A
    70: ("L1", "R1"),              # Bb (1 and 1)
    71: ("L1",),                   # B
    72: ("L2",),                   # C
    73: (),                        # C# (open)
}


def chart_elements(written, octave_key=True):
    """Pressed elements for a written sax pitch (clamped to the Bb3-F#6 range)."""
    w = min(max(written, 58), 90)
    if w >= 86:
        return ("OctaveKey", "Palm") if octave_key else ("Palm",)
    if w >= 74:
        base = SAX_CHART[w - 12]
        return base + ("OctaveKey",) if octave_key else base
    return SAX_CHART[w]


def chart_pose(settings, pitch):
    """Return (pose_values or None, missing element names) for per-finger mode."""
    elems = chart_elements(pitch + settings.transpose, settings.use_octave_key)
    pose, missing = {}, []
    for el in elems:
        a = bpy.data.actions.get(settings.fing_prefix + el)
        if a is None:
            missing.append(settings.fing_prefix + el)
        else:
            pose.update(pose_values(a))
    return (None if missing else pose), missing, elems


def _name_variants(base):
    out = [base]
    for sharp, flat in FLAT_ALIAS.items():
        if base.startswith(sharp):
            out.append(flat + base[len(sharp):])
    return out


def fingering_for(settings, pitch):
    """Return (base_action, octave_key: bool, wanted_name)."""
    w = pitch + settings.transpose
    pfx = settings.fing_prefix
    for cand in _name_variants(note_name(w)):
        a = bpy.data.actions.get(pfx + cand)
        if a:
            return a, False, pfx + note_name(w)
    pc = NOTE_NAMES[w % 12]
    octave = settings.use_octave_key and w >= 74
    for cand in _name_variants(pc):
        a = bpy.data.actions.get(pfx + cand)
        if a:
            return a, octave, pfx + pc
    return None, octave, pfx + pc


def bake_fingering(scene, s, midi):
    arm = s.fing_target
    fps = scene.render.fps / scene.render.fps_base
    notes = [n for n in midi.notes
             if (s.fing_track < 0 or n.track == s.fing_track)
             and (s.fing_channel <= 0 or n.channel == s.fing_channel - 1)]
    if not notes:
        return 0, []

    octave_act = bpy.data.actions.get(s.fing_prefix + "OctaveKey")
    rest_act = bpy.data.actions.get(s.fing_prefix + "Rest")
    rest = pose_values(rest_act) if rest_act else None
    octave = pose_values(octave_act) if octave_act else {}

    def frame(t):
        return s.start_frame + (t + s.time_offset) * fps

    # Resolve poses; monophonic: a note ends when the next one starts
    events, missing, cache = [], set(), {}
    chart = s.fing_mode == "CHART"
    if chart:
        octave = {}  # the octave key is just another element in the chart
    for i, n in enumerate(notes):
        if chart:
            p, miss, elems = chart_pose(s, n.pitch)
            if p is None:
                missing.update(miss)
                continue
            key = elems
            cache.setdefault(key, p)
        else:
            act, use_oct, wanted = fingering_for(s, n.pitch)
            if act is None:
                missing.add(wanted)
                continue
            key = (act.name, use_oct)
            if key not in cache:
                p = dict(pose_values(act))
                if use_oct:
                    p.update(octave)
                cache[key] = p
        end = n.end if i + 1 >= len(notes) else min(n.end, notes[i + 1].start)
        events.append((frame(n.start), frame(max(end, n.start)), cache[key]))
    if not events:
        return 0, sorted(missing)

    channels = set(octave) | (set(rest) if rest else set())
    for _, _, p in events:
        channels |= set(p)
    channels = sorted(channels)
    defaults = {ch: (rest.get(ch) if rest and ch in rest else identity_value(*ch)) for ch in channels}

    def full(p):
        return {ch: p.get(ch, defaults[ch]) for ch in channels}

    rest_full = full(rest) if rest else None
    tf = s.transition
    gap_f = s.rest_gap * fps
    keys = []  # (frame, pose)

    def add(f, pose):
        if keys and f <= keys[-1][0] + 1e-3:
            if f >= keys[-1][0] - 1e-3:
                keys[-1] = (keys[-1][0], pose)
            return
        keys.append((f, pose))

    prev_pose, prev_end = None, None
    for start, end, p in events:
        pose = full(p)
        if prev_pose is None:
            add(start - tf, rest_full or pose)
        elif rest_full and start - prev_end > gap_f and start - prev_end > 2 * tf:
            add(prev_end, prev_pose)
            add(prev_end + tf, rest_full)
            add(start - tf, rest_full)
        else:
            add(start - tf, prev_pose)
        add(start, pose)
        prev_pose, prev_end = pose, end
    add(prev_end, prev_pose)
    if rest_full:
        add(prev_end + tf, rest_full)

    chan_data = [(ch[0], ch[1], [(f, pose[ch]) for f, pose in keys]) for ch in channels]
    if s.keep_active_actions:
        push_active_down(arm)
    act = build_action(arm, GEN_PREFIX + "Fingering", chan_data, "BEZIER")
    push_strip(arm, "Fingering", act, "REPLACE")
    return len(events), sorted(missing)


# ---------------------------------------------------------------------------
# Breath effects
# ---------------------------------------------------------------------------

def effect_events(e, midi, notes_filtered):
    if e.source == "VELOCITY":
        return velocity_events(notes_filtered), "note velocity"
    if e.source == "AUTO":
        key = detect_breath(midi, e.track, e.channel)
        if key is None:
            return velocity_events(notes_filtered), "note velocity (no breath data found)"
        return midi.controllers[key], describe_source(key)
    kind, num = ("CC", e.cc_number) if e.source == "CC" else ("AT", 0)
    ev = []
    for k, v in midi.controllers.items():
        if k[2] == kind and k[3] == num and _filter_ok(k, e.track, e.channel):
            ev.extend(v)
    ev.sort()
    return ev, describe_source(next((k for k in midi.controllers if k[2] == kind and k[3] == num), None))


def effect_values(scene, s, e, midi):
    fps = scene.render.fps / scene.render.fps_base
    notes = [n for n in midi.notes
             if (e.track < 0 or n.track == e.track) and (e.channel <= 0 or n.channel == e.channel - 1)]
    events, label = effect_events(e, midi, notes)
    f0 = s.start_frame + int(math.floor(s.time_offset * fps))
    f1 = s.start_frame + int(math.ceil((midi.length + s.time_offset) * fps)) + int(fps)
    frames = list(range(min(f0, s.start_frame), f1 + 1))
    times = [(f - s.start_frame) / fps - s.time_offset for f in frames]
    raw = sample_signal(events, times, e.attack, e.release)
    peak = max((v for _, v in events), default=127) if e.normalize else 127.0
    peak = max(peak, 1.0)
    out = []
    for r in raw:
        x = min(max(r / peak, 0.0), 1.0)
        x = 0.0 if x <= e.threshold else (x - e.threshold) / (1.0 - e.threshold)
        x = x ** e.curve
        out.append(e.out_min + (e.out_max - e.out_min) * x)
    return frames, out, label


def bake_effect(scene, s, e, midi):
    frames, vals, label = effect_values(scene, s, e, midi)
    obj = e.target
    if e.target_type == "SHAPE_KEY":
        sk = obj.data.shape_keys if obj.type == "MESH" else None
        if not sk or e.shape_key not in sk.key_blocks:
            raise ValueError(f"'{obj.name}' has no shape key '{e.shape_key}'")
        owner = sk
        chans = [(f'key_blocks["{e.shape_key}"].value', 0, list(zip(frames, vals)))]
    elif e.target_type == "SCALE":
        owner = obj
        axes = ["XYZ".index(c) for c in e.scale_axes]
        chans = [("scale", i, [(f, e.base_scale[i] * v) for f, v in zip(frames, vals)]) for i in axes]
    else:
        owner = obj
        try:
            obj.path_resolve(e.data_path)
        except Exception:
            raise ValueError(f"'{obj.name}' has no property '{e.data_path}'")
        chans = [(e.data_path, e.array_index, list(zip(frames, vals)))]

    if s.keep_active_actions:
        push_active_down(owner)
    act = build_action(owner, f"{GEN_PREFIX}{e.name}", chans, "LINEAR")
    push_strip(owner, e.name, act, e.blend_type)
    return label


# ---------------------------------------------------------------------------
# Note -> action triggers
# ---------------------------------------------------------------------------

def mapping_matches(m, note):
    if m.track >= 0 and note.track != m.track:
        return False
    if m.channel > 0 and note.channel != m.channel - 1:
        return False
    lo, hi = sorted((m.note_low, m.note_high))
    return lo <= note.pitch <= hi and note.velocity >= m.min_velocity


def bake_mapping(scene, settings, m, notes):
    fps = scene.render.fps / scene.render.fps_base
    obj, action = m.target, m.action
    a_start, a_end = action.frame_range
    a_len = max(a_end - a_start, 1.0)
    lead = (m.hit_frame - a_start) if m.use_hit_frame else 0.0

    ad = obj.animation_data or obj.animation_data_create()
    if settings.keep_active_actions:
        push_active_down(obj)

    tracks = []
    count = 0
    for note in notes:
        if not mapping_matches(m, note):
            continue
        note_start = settings.start_frame + (note.start + settings.time_offset) * fps
        note_len = max(note.duration * fps, 1.0)
        if m.mode == "HOLD":
            scale, repeat, length = note_len / a_len, 1.0, note_len
        elif m.mode == "LOOP":
            repeat = max(note_len / a_len, 1.0)
            scale, length = 1.0, a_len * repeat
        else:
            scale, repeat, length = 1.0, 1.0, a_len
        frame = note_start - lead * scale

        lane = next((i for i, (_, last) in enumerate(tracks) if frame >= last), None)
        if lane is None:
            tr = ad.nla_tracks.new()
            tr.name = f"{NLA_PREFIX} {m.name} {len(tracks) + 1}"
            tracks.append((tr, -1e9))
            lane = len(tracks) - 1
        tr = tracks[lane][0]

        strip = tr.strips.new(f"{m.name} {note_name(note.pitch)}", int(round(frame)), action)
        _assign_slot(strip, obj)
        strip.blend_type = m.blend_type
        strip.extrapolation = "NOTHING"
        strip.scale = scale
        strip.repeat = repeat
        strip.frame_end = strip.frame_start + length
        offset = frame - strip.frame_start
        if abs(offset) > 1e-4:
            strip.frame_start += offset
            strip.frame_end = strip.frame_start + length
        bf = min(m.blend_frames, length / 2.0)
        strip.blend_in = bf
        strip.blend_out = bf
        if m.velocity_influence:
            strip.use_animated_influence = True
            strip.influence = note.velocity / 127.0
            strip.keyframe_insert("influence", frame=strip.frame_start)
        tracks[lane] = (tr, strip.frame_end)
        count += 1
    return count


# ---------------------------------------------------------------------------
# MIDI loading
# ---------------------------------------------------------------------------

_CACHE = {"path": None, "mtime": None, "data": None}


def load_midi(settings):
    path = bpy.path.abspath(settings.midi_path)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError("Choose a valid .mid file first")
    mtime = os.path.getmtime(path)
    if _CACHE["path"] != path or _CACHE["mtime"] != mtime:
        _CACHE.update(path=path, mtime=mtime, data=parse_midi(path))
    return _CACHE["data"]


def _guess_bone(arm, keywords):
    if not arm or arm.type != "ARMATURE":
        return None
    names = [b.name for b in arm.pose.bones]
    for kw in keywords:
        for n in names:
            if n.lower().replace("mixamorig:", "") == kw:
                return arm.pose.bones[n]
    for kw in keywords:
        for n in names:
            if kw in n.lower():
                return arm.pose.bones[n]
    return None


def _rot_path(pb, axis):
    if pb.rotation_mode == "QUATERNION":
        return f'pose.bones["{pb.name}"].rotation_quaternion', axis + 1
    if pb.rotation_mode == "AXIS_ANGLE":
        return f'pose.bones["{pb.name}"].rotation_axis_angle', 0
    return f'pose.bones["{pb.name}"].rotation_euler', axis


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class MIDIANIM_OT_import_model(bpy.types.Operator):
    """Import a character or instrument model (FBX, glTF/GLB, OBJ, USD)"""
    bl_idname = "midianim.import_model"
    bl_label = "Import Model"
    bl_options = {"REGISTER", "UNDO"}

    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.fbx;*.glb;*.gltf;*.obj;*.usd;*.usda;*.usdc;*.usdz",
                                options={"HIDDEN"})
    collection_name: StringProperty(name="Into Collection", default="")

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        ext = os.path.splitext(self.filepath)[1].lower()
        before = set(bpy.data.objects)
        try:
            if ext == ".fbx":
                bpy.ops.import_scene.fbx(filepath=self.filepath, automatic_bone_orientation=True)
            elif ext in (".glb", ".gltf"):
                bpy.ops.import_scene.gltf(filepath=self.filepath)
            elif ext == ".obj":
                bpy.ops.wm.obj_import(filepath=self.filepath)
            elif ext in (".usd", ".usda", ".usdc", ".usdz"):
                bpy.ops.wm.usd_import(filepath=self.filepath)
            else:
                self.report({"ERROR"}, f"Unsupported file type: {ext}")
                return {"CANCELLED"}
        except (RuntimeError, AttributeError) as e:
            self.report({"ERROR"}, f"Import failed: {e}")
            return {"CANCELLED"}
        new_objs = [o for o in bpy.data.objects if o not in before]
        name = self.collection_name or os.path.splitext(os.path.basename(self.filepath))[0]
        coll = bpy.data.collections.get(name) or bpy.data.collections.new(name)
        if coll.name not in context.scene.collection.children:
            context.scene.collection.children.link(coll)
        for o in new_objs:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o)
        self.report({"INFO"}, f"Imported {len(new_objs)} objects into '{coll.name}'")
        return {"FINISHED"}


class MIDIANIM_OT_add_metarig(bpy.types.Operator):
    """Add a Rigify human metarig at the 3D cursor (enables Rigify if needed)"""
    bl_idname = "midianim.add_metarig"
    bl_label = "Add Rigify Human Metarig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        import addon_utils
        if not addon_utils.check("rigify")[1]:
            try:
                addon_utils.enable("rigify", default_set=True, persistent=True)
            except Exception as e:
                self.report({"ERROR"}, f"Could not enable Rigify: {e}")
                return {"CANCELLED"}
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.armature_human_metarig_add()
        self.report({"INFO"}, "Metarig added: fit bones to your mesh, then Armature > Generate Rig")
        return {"FINISHED"}


class MIDIANIM_OT_bind_mesh(bpy.types.Operator):
    """Parent selected meshes to the active armature with automatic weights"""
    bl_idname = "midianim.bind_mesh"
    bl_label = "Bind Selected Meshes to Rig"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        a = context.active_object
        return a is not None and a.type == "ARMATURE" and context.mode == "OBJECT"

    def execute(self, context):
        meshes = [o for o in context.selected_objects if o.type == "MESH"]
        if not meshes:
            self.report({"ERROR"}, "Select mesh(es), then shift-select the armature last")
            return {"CANCELLED"}
        bpy.ops.object.parent_set(type="ARMATURE_AUTO")
        self.report({"INFO"}, f"Bound {len(meshes)} mesh(es) to {context.active_object.name}")
        return {"FINISHED"}


HOLD_PREFIX = "MIDI Hold"


def _find_bone(rig, keywords, side=None):
    """Best-effort bone lookup across Rigify, Mixamo and Biped naming."""
    def side_ok(name):
        if side is None:
            return True
        n = name.lower()
        l = side == "L"
        marks = ((".l", "_l_", "_l.", "left", "l_", " l ") if l else (".r", "_r_", "_r.", "right", "r_", " r "))
        return any(m in n for m in marks) or n.endswith("_l" if l else "_r")
    names = [b.name for b in rig.data.bones]
    for kw in keywords:
        for n in names:
            low = n.lower()
            if kw in low and side_ok(n) and "twist" not in low and "finger" not in low:
                return n
    return ""


class MIDIANIM_OT_guess_hold_bones(bpy.types.Operator):
    """Fill the strap and hand bones from the rig's bone names"""
    bl_idname = "midianim.guess_hold_bones"
    bl_label = "Guess Bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        rig = s.fing_target
        if not rig:
            self.report({"ERROR"}, "Set the Character Rig in 3. Fingering first")
            return {"CANCELLED"}
        s.hold_chest_bone = s.hold_chest_bone or _find_bone(
            rig, ["spine2", "spine4", "spine3", "chest", "spine.003", "upperchest", "spine1", "spine"])
        s.hold_hand_l = s.hold_hand_l or _find_bone(rig, ["hand"], "L")
        s.hold_hand_r = s.hold_hand_r or _find_bone(rig, ["hand"], "R")
        return {"FINISHED"}


class MIDIANIM_OT_lock_hands(bpy.types.Operator):
    """Hang the instrument from the strap bone and lock both hands onto it with IK, keeping the
    current pose. Pose the hold first (instrument at the lips, hands on the keys), then click this"""
    bl_idname = "midianim.lock_hands"
    bl_label = "Lock Hands to Instrument"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        rig, inst = s.fing_target, s.hold_instrument
        if not rig or not inst:
            self.report({"ERROR"}, "Set the Character Rig and the Instrument first")
            return {"CANCELLED"}
        for bone in (s.hold_chest_bone, s.hold_hand_l, s.hold_hand_r):
            if bone not in rig.pose.bones:
                self.report({"ERROR"}, f"Bone '{bone}' not found on {rig.name}")
                return {"CANCELLED"}
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        context.view_layer.update()

        # 1. Instrument hangs from the strap bone, keeping where it is now
        mw = inst.matrix_world.copy()
        inst.parent = rig
        inst.parent_type = "BONE"
        inst.parent_bone = s.hold_chest_bone
        context.view_layer.update()
        inst.matrix_world = mw

        # 2. One target per hand, child of the instrument, at the hand's current place
        made = []
        for side, bone_name in (("L", s.hold_hand_l), ("R", s.hold_hand_r)):
            pb = rig.pose.bones[bone_name]
            for c in [c for c in pb.constraints if c.name.startswith(HOLD_PREFIX)]:
                pb.constraints.remove(c)
            if pb.parent:
                for c in [c for c in pb.parent.constraints if c.name.startswith(HOLD_PREFIX)]:
                    pb.parent.constraints.remove(c)
            context.view_layer.update()

            name = f"{HOLD_PREFIX} {side}"
            tgt = bpy.data.objects.get(name)
            if tgt is None:
                tgt = bpy.data.objects.new(name, None)
                tgt.empty_display_type = "SPHERE"
                tgt.empty_display_size = 0.03 * max(rig.dimensions) / 2 or 0.05
                (inst.users_collection[0] if inst.users_collection else context.scene.collection).objects.link(tgt)
            hand_mw = rig.matrix_world @ pb.matrix
            tgt.parent = inst
            tgt.parent_type = "OBJECT"
            context.view_layer.update()
            tgt.matrix_world = hand_mw

            # Arm IK on the forearm (2 bones) reaches the wrist; the hand copies the target's rotation
            if pb.parent:
                ik = pb.parent.constraints.new("IK")
                ik.name = f"{HOLD_PREFIX} IK"
                ik.target = tgt
                ik.chain_count = 2
                ik.use_tail = True
                ik.use_stretch = False
            cr = pb.constraints.new("COPY_ROTATION")
            cr.name = f"{HOLD_PREFIX} Rotation"
            cr.target = tgt
            made.append(tgt.name)
        context.view_layer.update()
        self.report({"INFO"}, f"{inst.name} hangs from {s.hold_chest_bone}; hands locked to {', '.join(made)}. "
                              "Move the targets to adjust the grip")
        return {"FINISHED"}


class MIDIANIM_OT_unlock_hands(bpy.types.Operator):
    """Remove the hand lock constraints and targets (the instrument stays on the strap bone)"""
    bl_idname = "midianim.unlock_hands"
    bl_label = "Unlock Hands"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        rig = s.fing_target
        n = 0
        if rig:
            for pb in rig.pose.bones:
                for c in [c for c in pb.constraints if c.name.startswith(HOLD_PREFIX)]:
                    pb.constraints.remove(c)
                    n += 1
        for side in ("L", "R"):
            o = bpy.data.objects.get(f"{HOLD_PREFIX} {side}")
            if o:
                bpy.data.objects.remove(o)
        self.report({"INFO"}, f"Removed {n} hold constraints")
        return {"FINISHED"}


class MIDIANIM_OT_analyze(bpy.types.Operator):
    """Read the MIDI file: tracks, notes, breath controller and which fingering poses are missing"""
    bl_idname = "midianim.analyze"
    bl_label = "Analyze MIDI"

    def execute(self, context):
        s = context.scene.midi_animator
        try:
            midi = load_midi(s)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        lines = [f"{len(midi.notes)} notes, {midi.length:.1f}s"]
        for ti, tname in enumerate(midi.tracks):
            tn = [n for n in midi.notes if n.track == ti]
            if not tn:
                continue
            pitches = sorted({n.pitch for n in tn})
            chans = sorted({n.channel + 1 for n in tn})
            lines.append(f"T{ti} '{tname}' ch{','.join(map(str, chans))}: {len(tn)} notes, "
                         f"{note_name(pitches[0])}–{note_name(pitches[-1])}")
        lines.append("Breath: " + describe_source(detect_breath(midi)))

        missing = set()
        for n in midi.notes:
            if (s.fing_track < 0 or n.track == s.fing_track) and \
               (s.fing_channel <= 0 or n.channel == s.fing_channel - 1):
                if s.fing_mode == "CHART":
                    missing.update(chart_pose(s, n.pitch)[1])
                    continue
                act, use_oct, wanted = fingering_for(s, n.pitch)
                if act is None:
                    missing.add(wanted)
                if use_oct and not bpy.data.actions.get(s.fing_prefix + "OctaveKey"):
                    missing.add(s.fing_prefix + "OctaveKey")
        if s.fing_mode == "CHART" and not bpy.data.actions.get(s.fing_prefix + "Rest"):
            missing.add(s.fing_prefix + "Rest")
        s.fing_missing = ", ".join(sorted(m[len(s.fing_prefix):] for m in missing))
        s.summary = "|".join(lines)
        self.report({"INFO"}, lines[0])
        return {"FINISHED"}


class MIDIANIM_OT_set_scene_range(bpy.types.Operator):
    """Set the scene frame range to cover the whole MIDI file"""
    bl_idname = "midianim.set_scene_range"
    bl_label = "Fit Scene Range"

    def execute(self, context):
        s = context.scene.midi_animator
        try:
            midi = load_midi(s)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        fps = context.scene.render.fps / context.scene.render.fps_base
        context.scene.frame_start = s.start_frame
        context.scene.frame_end = int(s.start_frame + (midi.length + s.time_offset) * fps) + int(fps)
        return {"FINISHED"}


class MIDIANIM_OT_add_audio(bpy.types.Operator):
    """Add the audio file to the Video Sequencer at the start frame for playback sync"""
    bl_idname = "midianim.add_audio"
    bl_label = "Add Audio"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        path = bpy.path.abspath(s.audio_path)
        if not os.path.isfile(path):
            self.report({"ERROR"}, "Choose an audio file first")
            return {"CANCELLED"}
        scene = context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()
        se = scene.sequence_editor
        # Blender 5.0 renamed sequences -> strips; an empty collection is falsy, so test the attribute
        strips = se.strips if hasattr(se, "strips") else se.sequences
        strip = strips.new_sound("MIDI Audio", path, channel=1, frame_start=s.start_frame)
        scene.sync_mode = "AUDIO_SYNC"
        self.report({"INFO"}, f"Added {strip.name}")
        return {"FINISHED"}


class MIDIANIM_OT_save_fingering(bpy.types.Operator):
    """Save the current pose of the selected bones (your fingers) as the fingering for this note"""
    bl_idname = "midianim.save_fingering"
    bl_label = "Save Pose as Fingering"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return context.mode == "POSE" and context.active_object and context.selected_pose_bones

    def execute(self, context):
        s = context.scene.midi_animator
        arm = context.active_object
        chans = []
        for pb in context.selected_pose_bones:
            base = f'pose.bones["{pb.name}"]'
            props = ["location"]
            props.append({"QUATERNION": "rotation_quaternion",
                          "AXIS_ANGLE": "rotation_axis_angle"}.get(pb.rotation_mode, "rotation_euler"))
            props.append("scale")
            for prop in props:
                for i, v in enumerate(getattr(pb, prop)):
                    chans.append((f"{base}.{prop}", i, [(1.0, v)]))
        name = s.fing_prefix + s.save_note
        build_action(arm, name, chans, "CONSTANT", fake_user=True, replace=True)
        if s.fing_target is None:
            s.fing_target = arm
        self.report({"INFO"}, f"Saved '{name}' ({len(context.selected_pose_bones)} bones)")
        return {"FINISHED"}


class MIDIANIM_OT_preview_fingering(bpy.types.Operator):
    """Apply a saved fingering to the rig so you can check or tweak it"""
    bl_idname = "midianim.preview_fingering"
    bl_label = "Load Fingering"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        arm = s.fing_target or context.active_object
        act = bpy.data.actions.get(s.fing_prefix + s.save_note)
        if not arm or not act:
            self.report({"ERROR"}, "No rig or no saved pose with that name")
            return {"CANCELLED"}
        for (path, idx), v in pose_values(act).items():
            try:
                prop_owner, prop = path.rsplit(".", 1)
                getattr(arm.path_resolve(prop_owner), prop)[idx] = v
            except Exception:
                pass
        return {"FINISHED"}


class MIDIANIM_OT_effect_add(bpy.types.Operator):
    """Add a breath effect"""
    bl_idname = "midianim.effect_add"
    bl_label = "Add Breath Effect"
    bl_options = {"REGISTER", "UNDO"}

    preset: EnumProperty(items=[
        ("CHEEKS", "Cheeks", "Cheek puff shape key"),
        ("BELL", "Bell", "Scale the instrument's bell object"),
        ("CHEST", "Chest", "Chest rises with breath"),
        ("SWAY", "Sway", "Slow body lean with phrases"),
        ("CUSTOM", "Custom", ""),
    ], default="CUSTOM")

    def execute(self, context):
        s = context.scene.midi_animator
        e = s.effects.add()
        obj = context.active_object
        rig = s.fing_target or (obj if obj and obj.type == "ARMATURE" else None)
        if self.preset == "CHEEKS":
            e.name, e.target_type, e.shape_key = "Cheeks", "SHAPE_KEY", "CheekPuff"
            e.curve, e.attack, e.release = 0.8, 0.04, 0.15
            mesh = obj if obj and obj.type == "MESH" else None
            if mesh is None and rig:
                mesh = next((c for c in rig.children if c.type == "MESH" and c.data.shape_keys
                             and "CheekPuff" in c.data.shape_keys.key_blocks), None)
            e.target = mesh
        elif self.preset == "BELL":
            e.name, e.target_type = "Bell", "SCALE"
            e.attack, e.release = 0.05, 0.2
            e.target = obj if obj and obj.type != "ARMATURE" else None
        elif self.preset in ("CHEST", "SWAY"):
            chest = self.preset == "CHEST"
            e.name = "Chest" if chest else "Sway"
            e.target_type = "PROPERTY"
            e.target = rig
            pb = _guess_bone(rig, ["chest", "spine2", "spine.003", "spine_fk.003", "upperchest",
                                   "spine1", "spine"] if chest else
                             ["spine", "spine.001", "hips", "torso", "pelvis"])
            if pb:
                e.data_path, e.array_index = _rot_path(pb, 0)
            e.out_min, e.out_max = (0.0, 0.04) if chest else (0.0, 0.06)
            e.attack, e.release = (0.15, 0.4) if chest else (0.6, 1.2)
            e.blend_type = "ADD"
        else:
            e.target = obj
        if e.target is not None and e.target_type == "SCALE":
            e.base_scale = e.target.scale
        s.effect_index = len(s.effects) - 1
        return {"FINISHED"}


class MIDIANIM_OT_effect_remove(bpy.types.Operator):
    bl_idname = "midianim.effect_remove"
    bl_label = "Remove Breath Effect"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        if 0 <= s.effect_index < len(s.effects):
            s.effects.remove(s.effect_index)
            s.effect_index = max(0, s.effect_index - 1)
        return {"FINISHED"}


class MIDIANIM_OT_capture_scale(bpy.types.Operator):
    """Use the target's current scale as its rest scale"""
    bl_idname = "midianim.capture_scale"
    bl_label = "Capture Rest Scale"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        e = s.effects[s.effect_index]
        if e.target:
            e.base_scale = e.target.scale
        return {"FINISHED"}


class MIDIANIM_OT_mapping_add(bpy.types.Operator):
    """Add a note -> action mapping (uses the active object and its action as defaults)"""
    bl_idname = "midianim.mapping_add"
    bl_label = "Add Mapping"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        m = s.mappings.add()
        obj = context.active_object
        if obj and _poll_anim_object(None, obj):
            m.target = obj
            if obj.animation_data and obj.animation_data.action:
                m.action = obj.animation_data.action
        m.name = f"Mapping {len(s.mappings)}"
        s.active_index = len(s.mappings) - 1
        return {"FINISHED"}


class MIDIANIM_OT_mapping_remove(bpy.types.Operator):
    bl_idname = "midianim.mapping_remove"
    bl_label = "Remove Mapping"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = context.scene.midi_animator
        if 0 <= s.active_index < len(s.mappings):
            s.mappings.remove(s.active_index)
            s.active_index = max(0, s.active_index - 1)
        return {"FINISHED"}


class MIDIANIM_OT_mapping_from_notes(bpy.types.Operator):
    """Create one mapping per distinct note in a track (e.g. one per drum piece)"""
    bl_idname = "midianim.mapping_from_notes"
    bl_label = "Mappings From Notes"
    bl_options = {"REGISTER", "UNDO"}

    track: IntProperty(name="Track", default=-1, min=-1, description="-1 = all tracks")

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = context.scene.midi_animator
        try:
            midi = load_midi(s)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        pitches = sorted({n.pitch for n in midi.notes if self.track < 0 or n.track == self.track})
        obj = context.active_object
        for p in pitches:
            m = s.mappings.add()
            m.name = note_name(p)
            m.track = self.track
            m.note_low = m.note_high = p
            if obj and _poll_anim_object(None, obj):
                m.target = obj
            for a in bpy.data.actions:
                low = a.name.lower()
                if low.endswith(note_name(p).lower()) or low.endswith(f"_{p}"):
                    m.action = a
                    break
        self.report({"INFO"}, f"Created {len(pitches)} mappings")
        return {"FINISHED"}


class MIDIANIM_OT_bake(bpy.types.Operator):
    """Bake fingering, breath effects and note actions (replaces the previous MIDI bake)"""
    bl_idname = "midianim.bake"
    bl_label = "Bake MIDI to Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        s = scene.midi_animator
        try:
            midi = load_midi(s)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        targets = {m.target for m in s.mappings if m.target} | {e.target for e in s.effects if e.target}
        if s.fing_target:
            targets.add(s.fing_target)
        # Capture rest scale before old animation is removed
        for e in s.effects:
            if e.enabled and e.target and e.target_type == "SCALE" and not has_midi_tracks(e.target):
                e.base_scale = e.target.scale
        clear_baked(targets)

        msgs, warnings = [], []
        if s.fing_enabled and s.fing_target:
            n, missing = bake_fingering(scene, s, midi)
            msgs.append(f"{n} fingered notes")
            if missing:
                warnings.append("missing poses: " + ", ".join(m[len(s.fing_prefix):] for m in missing))
        for e in s.effects:
            if not (e.enabled and e.target):
                continue
            try:
                label = bake_effect(scene, s, e, midi)
                msgs.append(f"{e.name} ← {label}")
            except ValueError as err:
                warnings.append(str(err))
        strips = 0
        for m in s.mappings:
            if m.enabled and m.target and m.action:
                strips += bake_mapping(scene, s, m, midi.notes)
        if strips:
            msgs.append(f"{strips} action strips")

        scene.frame_set(scene.frame_current)
        text = "Baked: " + "; ".join(msgs) if msgs else "Nothing to bake: set a rig, an effect or a mapping"
        if warnings:
            text += " | " + " | ".join(warnings)
        self.report({"WARNING"} if warnings else {"INFO"}, text)
        return {"FINISHED"}


class MIDIANIM_OT_clear(bpy.types.Operator):
    """Remove all NLA tracks created by MIDI Animator"""
    bl_idname = "midianim.clear"
    bl_label = "Clear MIDI Bake"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = clear_baked(context.scene.objects)
        self.report({"INFO"}, f"Removed {n} MIDI NLA tracks")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

class MIDIANIM_UL_mappings(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "name", text="", emboss=False)
        lo, hi = sorted((item.note_low, item.note_high))
        row.label(text=note_name(lo) if lo == hi else f"{note_name(lo)}–{note_name(hi)}")
        row.label(text="", icon="CHECKMARK" if item.target and item.action else "ERROR")


class MIDIANIM_UL_effects(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "name", text="", emboss=False)
        row.label(text=item.target.name if item.target else "no target",
                  icon="CHECKMARK" if item.target else "ERROR")


class MIDIANIM_PT_base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MIDI"


class MIDIANIM_PT_setup(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "1. Models & Rigs"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        col = self.layout.column(align=True)
        col.operator("midianim.import_model", icon="IMPORT")
        col.separator()
        col.operator("midianim.add_metarig", icon="ARMATURE_DATA")
        col.operator("midianim.bind_mesh", icon="MOD_ARMATURE")


class MIDIANIM_PT_hold(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "Hold the Instrument"
    bl_parent_id = "MIDIANIM_PT_setup"

    def draw(self, context):
        s = context.scene.midi_animator
        layout = self.layout
        col = layout.column()
        col.label(text="Pose the hold first: mouthpiece at the lips,", icon="INFO")
        col.label(text="left hand on top, right hand below, then lock.")
        col.prop(s, "fing_target", text="Rig")
        col.prop(s, "hold_instrument")
        rig = s.fing_target
        if rig and rig.type == "ARMATURE":
            col.prop_search(s, "hold_chest_bone", rig.data, "bones")
            col.prop_search(s, "hold_hand_l", rig.data, "bones")
            col.prop_search(s, "hold_hand_r", rig.data, "bones")
            col.operator("midianim.guess_hold_bones", icon="VIEWZOOM")
        row = col.row(align=True)
        row.operator("midianim.lock_hands", icon="LOCKED")
        row.operator("midianim.unlock_hands", text="", icon="UNLOCKED")


class MIDIANIM_PT_midi(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "2. MIDI & Audio"

    def draw(self, context):
        s = context.scene.midi_animator
        col = self.layout.column()
        col.prop(s, "midi_path")
        row = col.row(align=True)
        row.operator("midianim.analyze", icon="VIEWZOOM")
        row.operator("midianim.set_scene_range", icon="TIME")
        if s.summary:
            box = col.box()
            for line in s.summary.split("|"):
                box.label(text=line)
        col.prop(s, "start_frame")
        col.prop(s, "time_offset")
        col.separator()
        col.prop(s, "audio_path")
        col.operator("midianim.add_audio", icon="SOUND")


class MIDIANIM_PT_fingering(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "3. Fingering"

    def draw_header(self, context):
        self.layout.prop(context.scene.midi_animator, "fing_enabled", text="")

    def draw(self, context):
        s = context.scene.midi_animator
        layout = self.layout
        layout.prop(s, "fing_target")
        layout.prop(s, "fing_mode", text="")
        box = layout.box()
        if s.fing_mode == "CHART":
            box.label(text="Rest: pose the hold, select ALL finger joints, Save.", icon="HAND")
            box.label(text="Others: press one finger (all its joints), select them, Save.")
        else:
            box.label(text="Pose the fingers, select those bones, then:", icon="HAND")
        row = box.row(align=True)
        row.prop(s, "save_note", text="")
        row.operator("midianim.save_fingering", text="Save", icon="FILE_TICK")
        row.operator("midianim.preview_fingering", text="", icon="HIDE_OFF")
        names = [n for n, _ in CHART_ELEMENTS] if s.fing_mode == "CHART" else FINGERING_NAMES
        saved = [n for n in names if bpy.data.actions.get(s.fing_prefix + n)]
        box.label(text=f"Saved: {', '.join(saved) if saved else 'none yet'}")
        if s.fing_missing:
            box.label(text=f"Needed by this MIDI: {s.fing_missing}", icon="ERROR")
        col = layout.column(align=True)
        col.prop(s, "transpose")
        col.prop(s, "use_octave_key")
        col.prop(s, "transition")
        col.prop(s, "rest_gap")
        row = layout.row(align=True)
        row.prop(s, "fing_track")
        row.prop(s, "fing_channel")
        layout.prop(s, "fing_prefix")


class MIDIANIM_PT_effects(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "4. Breath Effects"

    def draw(self, context):
        s = context.scene.midi_animator
        layout = self.layout
        row = layout.row(align=True)
        for preset, icon in (("CHEEKS", "USER"), ("BELL", "SPHERE"), ("CHEST", "BONE_DATA"), ("SWAY", "FORCE_WIND")):
            row.operator("midianim.effect_add", text=preset.title(), icon=icon).preset = preset
        row = layout.row()
        row.template_list("MIDIANIM_UL_effects", "", s, "effects", s, "effect_index", rows=3)
        col = row.column(align=True)
        col.operator("midianim.effect_add", icon="ADD", text="").preset = "CUSTOM"
        col.operator("midianim.effect_remove", icon="REMOVE", text="")
        if not (0 <= s.effect_index < len(s.effects)):
            return
        e = s.effects[s.effect_index]
        box = layout.box()
        box.prop(e, "source")
        if e.source == "CC":
            box.prop(e, "cc_number")
        box.prop(e, "target")
        box.prop(e, "target_type")
        if e.target_type == "SHAPE_KEY":
            sk = e.target.data.shape_keys if e.target and e.target.type == "MESH" else None
            if sk:
                box.prop_search(e, "shape_key", sk, "key_blocks")
            else:
                box.prop(e, "shape_key")
                box.label(text="Target mesh has no shape keys yet", icon="ERROR")
        elif e.target_type == "SCALE":
            box.prop(e, "scale_axes", expand=True)
            r = box.row(align=True)
            r.prop(e, "base_scale", text="")
            r.operator("midianim.capture_scale", text="", icon="EYEDROPPER")
        else:
            box.prop(e, "data_path")
            box.prop(e, "array_index")
        r = box.row(align=True)
        r.prop(e, "out_min")
        r.prop(e, "out_max")
        r = box.row(align=True)
        r.prop(e, "attack")
        r.prop(e, "release")
        r = box.row(align=True)
        r.prop(e, "threshold")
        r.prop(e, "curve")
        box.prop(e, "normalize")
        box.prop(e, "blend_type")
        r = box.row(align=True)
        r.prop(e, "track")
        r.prop(e, "channel")


class MIDIANIM_PT_mappings(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "5. Note → Action Triggers"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = context.scene.midi_animator
        layout = self.layout
        row = layout.row()
        row.template_list("MIDIANIM_UL_mappings", "", s, "mappings", s, "active_index", rows=3)
        col = row.column(align=True)
        col.operator("midianim.mapping_add", icon="ADD", text="")
        col.operator("midianim.mapping_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("midianim.mapping_from_notes", icon="SEQ_SEQUENCER", text="")
        if 0 <= s.active_index < len(s.mappings):
            m = s.mappings[s.active_index]
            box = layout.box()
            box.prop(m, "target")
            box.prop(m, "action")
            r = box.row(align=True)
            r.prop(m, "note_low")
            r.prop(m, "note_high")
            r = box.row(align=True)
            r.prop(m, "track")
            r.prop(m, "channel")
            box.prop(m, "min_velocity")
            box.prop(m, "mode")
            r = box.row(align=True)
            r.prop(m, "use_hit_frame", text="")
            sub = r.row()
            sub.enabled = m.use_hit_frame
            sub.prop(m, "hit_frame")
            box.prop(m, "velocity_influence")
            r = box.row(align=True)
            r.prop(m, "blend_type", text="")
            r.prop(m, "blend_frames")


class MIDIANIM_PT_bake(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "6. Bake"

    def draw(self, context):
        s = context.scene.midi_animator
        col = self.layout.column()
        col.prop(s, "keep_active_actions")
        col.scale_y = 1.3
        col.operator("midianim.bake", icon="REC")
        col.operator("midianim.clear", icon="TRASH")


classes = (
    MIDIANIM_Mapping,
    MIDIANIM_Effect,
    MIDIANIM_Settings,
    MIDIANIM_OT_import_model,
    MIDIANIM_OT_add_metarig,
    MIDIANIM_OT_bind_mesh,
    MIDIANIM_OT_guess_hold_bones,
    MIDIANIM_OT_lock_hands,
    MIDIANIM_OT_unlock_hands,
    MIDIANIM_OT_analyze,
    MIDIANIM_OT_set_scene_range,
    MIDIANIM_OT_add_audio,
    MIDIANIM_OT_save_fingering,
    MIDIANIM_OT_preview_fingering,
    MIDIANIM_OT_effect_add,
    MIDIANIM_OT_effect_remove,
    MIDIANIM_OT_capture_scale,
    MIDIANIM_OT_mapping_add,
    MIDIANIM_OT_mapping_remove,
    MIDIANIM_OT_mapping_from_notes,
    MIDIANIM_OT_bake,
    MIDIANIM_OT_clear,
    MIDIANIM_UL_mappings,
    MIDIANIM_UL_effects,
    MIDIANIM_PT_setup,
    MIDIANIM_PT_hold,
    MIDIANIM_PT_midi,
    MIDIANIM_PT_fingering,
    MIDIANIM_PT_effects,
    MIDIANIM_PT_mappings,
    MIDIANIM_PT_bake,
)


def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.midi_animator = PointerProperty(type=MIDIANIM_Settings)


def unregister():
    del bpy.types.Scene.midi_animator
    for c in reversed(classes):
        bpy.utils.unregister_class(c)


if __name__ == "__main__":
    register()
