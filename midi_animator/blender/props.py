"""Scene settings (Scene.midi_animator)."""

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

from ..core import hud as core_hud
from ..core import profiles


def _profile_items(self, context):
    return [(p.id, p.name, p.description) for p in profiles.REGISTRY.values()]


def _poll_armature(self, obj):
    return obj.type == "ARMATURE"


def _poll_pose_asset(self, action):
    return action.asset_data is not None


def _poll_mesh_or_armature(self, obj):
    return obj.type in {"MESH", "ARMATURE", "EMPTY", "CURVE"}


BLEND_ITEMS = [
    ("REPLACE", "Replace", "Use the value as is"),
    ("ADD", "Add", "Add on top of the animation below"),
    ("COMBINE", "Combine", "Add location/rotation, multiply scale (quaternion-aware)"),
]

CHANNEL_ITEMS = [
    ("LOC_X", "Location X", ""), ("LOC_Y", "Location Y", ""), ("LOC_Z", "Location Z", ""),
    ("ROT_X", "Rotation X", "Degrees"), ("ROT_Y", "Rotation Y", "Degrees"), ("ROT_Z", "Rotation Z", "Degrees"),
    ("SCALE_X", "Scale X", "Added to 1"), ("SCALE_Y", "Scale Y", "Added to 1"),
    ("SCALE_Z", "Scale Z", "Added to 1"), ("SCALE_XZ", "Scale X+Z", "Added to 1 (chest width and depth)"),
    ("SCALE_XYZ", "Scale XYZ", "Added to 1"),
]


class MIDIANIM_TrackInfo(bpy.types.PropertyGroup):
    index: IntProperty()
    label: StringProperty()


class MIDIANIM_Line(bpy.types.PropertyGroup):
    text: StringProperty()
    icon: StringProperty(default="NONE")


class MIDIANIM_BoneRef(bpy.types.PropertyGroup):
    bone: StringProperty(name="Bone")


class MIDIANIM_FingerBones(bpy.types.PropertyGroup):
    slot: StringProperty()
    label: StringProperty()
    bones: CollectionProperty(type=MIDIANIM_BoneRef)
    up_pose: PointerProperty(
        name="Up Pose", type=bpy.types.Action, poll=_poll_pose_asset,
        description="Optional authored Up pose for this finger. Empty = hover over the key")


class MIDIANIM_NoteMapping(bpy.types.PropertyGroup):
    pitch: IntProperty(name="Note", min=0, max=127, description="Written pitch (after Transpose)")
    combination: StringProperty(
        name="Fingers", description="Pressed keys, e.g. 'L1=B;L2=A' (fingers not listed are up)")
    pose: PointerProperty(
        name="Whole-hand Pose", type=bpy.types.Action, poll=_poll_pose_asset,
        description="Optional: use this pose for the whole hand instead of the finger combination")


def _effect_target_update(self, context):
    if self.target_type == "SHAPE_KEY":
        self.blend_type = "REPLACE"
    elif self.target_type == "BONE":
        self.blend_type = "COMBINE"


class MIDIANIM_Effect(bpy.types.PropertyGroup):
    """Blow -> shape key, bone channel or any property."""
    name: StringProperty(name="Name", default="Effect")
    enabled: BoolProperty(name="Enabled", default=True)

    source: EnumProperty(
        name="Source",
        items=[
            ("CC", "Controller (CC)", "A MIDI CC number (CC2 = breath controller)"),
            ("AT", "Aftertouch", "Channel aftertouch"),
            ("VELOCITY", "Note Velocity", "Shape each note from its velocity"),
        ],
        default="CC",
    )
    cc_number: IntProperty(name="CC", default=2, min=0, max=127)
    if_missing: EnumProperty(
        name="If Missing",
        items=[
            ("ASK", "Ask", "Don't bake this effect until you choose"),
            ("VELOCITY", "Use Velocity", "Fall back to note velocity"),
            ("OFF", "Turn Off", "Skip this effect for this file"),
        ],
        default="ASK",
        description="What to do when the file has no data for the chosen controller",
    )
    status: StringProperty(default="")      # filled by Analyze
    missing: BoolProperty(default=False)    # filled by Analyze

    target: PointerProperty(name="Object", type=bpy.types.Object, poll=_poll_mesh_or_armature)
    target_type: EnumProperty(
        name="Drive",
        items=[
            ("SHAPE_KEY", "Shape Key", "A shape key value (e.g. CheekPuff)"),
            ("BONE", "Bone", "A bone's location, rotation or scale"),
            ("PROPERTY", "Property", "Any animatable property by data path (advanced)"),
        ],
        default="SHAPE_KEY",
        update=_effect_target_update,
    )
    shape_key: StringProperty(name="Shape Key", default="CheekPuff")
    bone: StringProperty(name="Bone")
    channel: EnumProperty(name="Channel", items=CHANNEL_ITEMS, default="ROT_X")
    data_path: StringProperty(name="Data Path", description='e.g. pose.bones["chest"].scale')
    array_index: IntProperty(name="Index", default=0, min=0)

    mode: EnumProperty(
        name="Mode",
        items=[
            ("DIRECT", "Direct", "Follows blow intensity (cheeks)"),
            ("LUNG", "Lung", "Follows the air left in the lungs: empties while blowing, refills in rests (chest)"),
        ],
        default="DIRECT",
    )
    out_min: FloatProperty(name="Min", default=0.0, description="Output with no blow (Lung: empty lungs)")
    out_max: FloatProperty(name="Max", default=1.0, description="Output at full blow (Lung: full lungs)")
    threshold: FloatProperty(name="Threshold", default=0.05, min=0.0, max=0.95,
                             description="Ignore blow below this fraction (noise)")
    curve: FloatProperty(name="Curve", default=1.0, min=0.1, max=5.0,
                         description="<1 soft blow already shows, >1 only strong blow moves it")
    attack: FloatProperty(name="Attack (s)", default=0.04, min=0.0, max=2.0)
    release: FloatProperty(name="Release (s)", default=0.15, min=0.0, max=3.0)
    normalize: BoolProperty(name="Normalize to Peak", default=True,
                            description="The strongest blow in the take counts as full")
    sustain: FloatProperty(name="Sustain", default=0.6, min=0.0, max=1.0,
                           description="Velocity fallback: level held while the note sounds")
    decay: FloatProperty(name="Decay (s)", default=0.2, min=0.0, max=3.0,
                         description="Velocity fallback: time to fall from the peak to sustain")
    lung_capacity: FloatProperty(name="Lung Capacity (s)", default=6.0, min=0.5, max=60.0,
                                 description="Seconds of full blow that empty the lungs")
    refill_time: FloatProperty(name="Refill (s)", default=0.35, min=0.01, max=5.0,
                               description="How fast the lungs refill in rests")
    blend_type: EnumProperty(name="Blend", items=BLEND_ITEMS, default="REPLACE")

    own_source: BoolProperty(name="Own Track/Channel", default=False,
                             description="Read this effect from a different track/channel than the performer")
    track: IntProperty(name="Track", default=-1, min=-1)
    channel_filter: IntProperty(name="Channel", default=0, min=0, max=16)
    show_advanced: BoolProperty(default=False)


def _color(name, default):
    return FloatVectorProperty(name=name, subtype="COLOR_GAMMA", size=4, min=0.0, max=1.0, default=default)


class MIDIANIM_Hud(bpy.types.PropertyGroup):
    preview: BoolProperty(name="Show in Viewport", default=False)
    preview_scale: FloatProperty(name="Preview Scale", default=0.5, min=0.1, max=2.0)
    preview_position: EnumProperty(name="Preview Position",
                                   items=[("BOTTOM", "Bottom", ""), ("TOP", "Top", "")], default="BOTTOM")
    width: IntProperty(name="Width", default=1920, min=64, max=8192)
    height: IntProperty(name="Height", default=360, min=32, max=4320)
    lookahead: FloatProperty(name="Look-ahead (s)", default=3.0, min=0.5, max=20.0)
    hit_x: FloatProperty(name="Hit Line", default=0.22, min=0.05, max=0.8, subtype="FACTOR")
    pitch_auto: BoolProperty(name="Auto Pitch Range", default=True)
    pitch_lo: IntProperty(name="Lowest", default=58, min=0, max=127)
    pitch_hi: IntProperty(name="Highest", default=89, min=0, max=127)
    lane_lines: BoolProperty(name="Octave Lines", default=True)
    label_size: FloatProperty(name="Label Size", default=0.07, min=0.02, max=0.2)
    now_size: FloatProperty(name="Now Playing Size", default=0.17, min=0.05, max=0.4)
    pitch_display: EnumProperty(name="Pitch", items=[
        ("WRITTEN", "Written", "As fingered (after Transpose)"),
        ("CONCERT", "Concert", "As in the MIDI file")], default="WRITTEN")
    accidentals: EnumProperty(name="Accidentals", items=[
        ("SHARP", "Sharps", "C#"), ("FLAT", "Flats", "Db")], default="SHARP")
    naming: EnumProperty(name="Names", items=[
        ("LETTER", "Letters", "C D E"), ("SOLFEGE", "Solfège", "Dó Ré Mi")], default="LETTER")
    show_octave: BoolProperty(name="Octave Number", default=True)
    color_panel: _color("Background", core_hud.DEFAULT_COLORS["panel"])
    color_upcoming: _color("Upcoming", core_hud.DEFAULT_COLORS["upcoming"])
    color_active: _color("Playing", core_hud.DEFAULT_COLORS["active"])
    color_played: _color("Played", core_hud.DEFAULT_COLORS["played"])
    color_hitline: _color("Hit Line", core_hud.DEFAULT_COLORS["hitline"])
    output_dir: StringProperty(name="Output Folder", subtype="DIR_PATH", default="//hud/")
    output_format: EnumProperty(name="Format", items=[
        ("PNG", "PNG Sequence (alpha)", "One RGBA PNG per frame"),
        ("PRORES", "ProRes 4444 (alpha)", "PNG sequence, then a .mov encoded by Blender")], default="PNG")


class MIDIANIM_Settings(bpy.types.PropertyGroup):
    profile: EnumProperty(name="Instrument", items=_profile_items)

    midi_path: StringProperty(name="MIDI File", subtype="FILE_PATH")
    audio_path: StringProperty(name="Audio File", subtype="FILE_PATH")
    start_frame: IntProperty(name="Start Frame", default=1)
    time_offset: FloatProperty(name="Offset (s)", default=0.0, description="Shift all MIDI by this many seconds")

    performer_track: IntProperty(name="Track", default=-1, min=-1, description="-1 = all tracks")
    performer_channel: IntProperty(name="Channel", default=0, min=0, max=16, description="0 = all channels")
    transpose: IntProperty(name="Transpose", default=0, min=-48, max=48,
                           description="Semitones from the file's pitch to the written (fingered) pitch")
    tracks: CollectionProperty(type=MIDIANIM_TrackInfo)
    report: CollectionProperty(type=MIDIANIM_Line)

    rig: PointerProperty(name="Character Rig", type=bpy.types.Object, poll=_poll_armature)
    instrument: PointerProperty(name="Instrument", type=bpy.types.Object,
                                description="Key markers are created as children of this object")
    hold_strap_bone: StringProperty(name="Strap Bone", description="Bone the instrument hangs from (upper chest)")
    hold_hand_l: StringProperty(name="Left Hand", description="Left hand bone (the forearm above it gets the IK)")
    hold_hand_r: StringProperty(name="Right Hand", description="Right hand bone (the forearm above it gets the IK)")
    fingers: CollectionProperty(type=MIDIANIM_FingerBones)
    finger_index: IntProperty(default=0)
    hover: FloatProperty(name="Hover Height", default=0.012, min=0.0, unit="LENGTH",
                         description="How far above its key a lifted finger hovers")
    marker_size: FloatProperty(name="Marker Size", default=0.006, min=0.0001, unit="LENGTH")
    force_autoassign: BoolProperty(name="Overwrite Locked", default=False,
                                   description="Also regenerate poses you edited or locked")
    bend_axis: EnumProperty(
        name="Bend Axis",
        items=[
            ("X", "X", "Fingers curl with a positive rotation around their local X (Rigify)"),
            ("-X", "-X", "Fingers curl with a negative rotation around their local X"),
            ("Z", "Z", "Fingers curl with a positive rotation around their local Z"),
            ("-Z", "-Z", "Fingers curl with a negative rotation around their local Z"),
        ],
        default="X",
        description="The local axis (and direction) a finger joint curls around. Autoassign only "
                    "bends joints this way, so fingers never twist sideways or bend backwards. "
                    "Detect reads it from the rig's rest curl")
    keep_twist: BoolProperty(name="Keep Twist", default=True,
                             description="Autoassign never twists finger bones around their own "
                                         "length (locks IK on Y)")

    notes: CollectionProperty(type=MIDIANIM_NoteMapping)
    note_index: IntProperty(default=0)
    clipboard: StringProperty(default="")
    rest_pose: PointerProperty(name="Rest Pose", type=bpy.types.Action, poll=_poll_pose_asset,
                               description="Relaxed hand between phrases")

    fingering_enabled: BoolProperty(name="Bake Fingering", default=True)
    transition: FloatProperty(name="Transition (frames)", default=2.0, min=0.0, max=24.0)
    lift_lead: FloatProperty(name="Lift Lead (frames)", default=1.0, min=0.0, max=12.0,
                             description="Lifting fingers leave this many frames before pressing ones arrive")
    relax_after: FloatProperty(name="Relax After (s)", default=0.5, min=0.0,
                               description="Rests longer than this relax the hand to the Rest pose")

    effects: CollectionProperty(type=MIDIANIM_Effect)
    effect_index: IntProperty(default=0)

    keep_active_actions: BoolProperty(
        name="Keep Active Actions as Base", default=True,
        description="Move the targets' active actions (e.g. an idle) into a base NLA track under the MIDI tracks")

    hud: PointerProperty(type=MIDIANIM_Hud)


classes = (
    MIDIANIM_TrackInfo,
    MIDIANIM_Line,
    MIDIANIM_BoneRef,
    MIDIANIM_FingerBones,
    MIDIANIM_NoteMapping,
    MIDIANIM_Effect,
    MIDIANIM_Hud,
    MIDIANIM_Settings,
)
