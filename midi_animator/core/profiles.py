"""Instrument profiles.

A profile describes one family of instruments: which finger slots exist, which keys each
finger can press, the built-in fingering chart and the blow-effect presets. Profiles are
plain classes registered with @register; the Blender layer shows them in a dropdown.
"""

from dataclasses import dataclass, field

from .notes import parse_note_name

UP = None  # a finger that is not pressing anything


@dataclass(frozen=True)
class FingerSlot:
    id: str             # short id used in pose names, e.g. "L1"
    label: str          # shown in the UI
    side: str           # "L" or "R"
    finger: str         # "thumb", "index", "middle", "ring", "pinky"
    keys: tuple         # key names this finger can press; keys[0] is its home key


@dataclass(frozen=True)
class EffectPreset:
    id: str
    label: str
    target_type: str            # "SHAPE_KEY", "BONE", "PROPERTY"
    mode: str = "DIRECT"        # "DIRECT" or "LUNG"
    shape_key: str = ""
    bone_keywords: tuple = ()   # bone name guesses for BONE targets
    channel: str = "ROT_X"
    out_min: float = 0.0
    out_max: float = 1.0
    attack: float = 0.04
    release: float = 0.15
    curve: float = 1.0
    blend: str = "REPLACE"


@dataclass
class Profile:
    id: str = ""
    name: str = ""
    description: str = ""
    monophonic: bool = True
    slots: tuple = ()
    chart: dict = field(default_factory=dict)    # written pitch -> {slot_id: key}
    presets: tuple = ()
    default_transpose: int = 0                   # semitones from the file's (concert) pitch to written

    def slot(self, slot_id):
        return next((s for s in self.slots if s.id == slot_id), None)

    def combination_for(self, pitch):
        """Built-in chart entry for a written pitch, or None if the chart has no entry."""
        c = self.chart.get(pitch)
        return dict(c) if c is not None else None


REGISTRY = {}


def register(factory):
    p = factory()
    REGISTRY[p.id] = p
    return factory


def get(profile_id):
    return REGISTRY.get(profile_id) or next(iter(REGISTRY.values()))


# ---------------------------------------------------------------------------
# Monophonic wind / brass — saxophone fingering (also the Aerophone default)
# ---------------------------------------------------------------------------

SAX_SLOTS = (
    FingerSlot("LT", "L Thumb (octave)", "L", "thumb", ("Octave",)),
    FingerSlot("L1", "L Index", "L", "index", ("B", "FrontF", "PalmD", "PalmEb", "PalmF")),
    FingerSlot("L2", "L Middle", "L", "middle", ("A",)),
    FingerSlot("L3", "L Ring", "L", "ring", ("G",)),
    FingerSlot("L4", "L Pinky", "L", "pinky", ("G#", "LowC#", "LowB", "LowBb")),
    FingerSlot("R1", "R Index", "R", "index", ("F", "SideBb", "SideC", "SideE", "HighF#")),
    FingerSlot("R2", "R Middle", "R", "middle", ("E",)),
    FingerSlot("R3", "R Ring", "R", "ring", ("D",)),
    FingerSlot("R4", "R Pinky", "R", "pinky", ("LowEb", "LowC")),
)


def _sax_chart():
    """Standard saxophone fingerings by written pitch, Bb3 .. F#6 (58 .. 90). Each entry lists
    only the fingers that press a key; every other finger is up.

    One finger presses one marker, so keys that a hand presses together are one marker:
    - left palm keys (left index): "PalmD" = palm D, "PalmEb" = palm D + Eb together,
      "PalmF" = palm D + Eb + F together;
    - right side keys (right index): "SideE" = the high E side key, "HighF#" = side E + the
      high F# key together.

    Intentional differences from the old single-file add-on's chart (PR #2, plan step 1):
    - Bb3, B3, C#4, G#4 use distinct left-pinky keys (LowBb, LowB, LowC#, G#) where the old chart
      had one "LP" element; C4 and D#4 likewise use LowC / LowEb for "RP".
    - D6 .. F#6 say which palm / side keys are pressed (old chart: one "Palm" element for all).
    - Pitches outside 58 .. 90 are not mapped, so Analyze and Bake report them; the old chart
      clamped them silently to the nearest end.
    """
    lh = {"L1": "B", "L2": "A", "L3": "G"}
    rh = {"R1": "F", "R2": "E", "R3": "D"}
    full = {**lh, **rh}
    low = {
        "Bb3": {**full, "L4": "LowBb"},
        "B3": {**full, "L4": "LowB"},
        "C4": {**full, "R4": "LowC"},
        "C#4": {**full, "L4": "LowC#"},
        "D4": dict(full),
        "D#4": {**full, "R4": "LowEb"},
        "E4": {**lh, "R1": "F", "R2": "E"},
        "F4": {**lh, "R1": "F"},
        "F#4": {**lh, "R2": "E"},
        "G4": dict(lh),
        "G#4": {**lh, "L4": "G#"},
        "A4": {"L1": "B", "L2": "A"},
        "A#4": {"L1": "B", "R1": "F"},
        "B4": {"L1": "B"},
        "C5": {"L2": "A"},
        "C#5": {},
    }
    chart = {parse_note_name(k): v for k, v in low.items()}
    # Second octave: same fingering + octave key (written D5 .. C#6)
    for name in ["D4", "D#4", "E4", "F4", "F#4", "G4", "G#4", "A4", "A#4", "B4", "C5", "C#5"]:
        p = parse_note_name(name)
        chart[p + 12] = {**chart[p], "LT": "Octave"}
    # Palm keys
    chart[parse_note_name("D6")] = {"LT": "Octave", "L1": "PalmD"}
    chart[parse_note_name("D#6")] = {"LT": "Octave", "L1": "PalmEb"}
    chart[parse_note_name("E6")] = {"LT": "Octave", "L1": "PalmEb", "R1": "SideE"}
    chart[parse_note_name("F6")] = {"LT": "Octave", "L1": "PalmF", "R1": "SideE"}
    chart[parse_note_name("F#6")] = {"LT": "Octave", "L1": "PalmF", "R1": "HighF#"}
    return chart


WIND_PRESETS = (
    EffectPreset("CHEEKS", "Cheeks", "SHAPE_KEY", mode="DIRECT", shape_key="CheekPuff",
                 out_min=0.0, out_max=1.0, attack=0.04, release=0.15, curve=0.8,
                 blend="REPLACE"),
    EffectPreset("CHEST", "Chest", "BONE", mode="LUNG",
                 bone_keywords=("chest", "spine2", "spine.003", "upperchest", "upper_chest",
                                "j_bip_c_upperchest", "spine1", "spine"),
                 channel="SCALE_XZ", out_min=0.0, out_max=0.04, attack=0.15, release=0.4,
                 blend="COMBINE"),
)


@register
def monophonic_wind():
    return Profile(
        id="MONO_WIND",
        name="Monophonic Wind / Brass",
        description="Saxophone-style fingering; one note at a time (Aerophone, EWI, sax, ...)",
        monophonic=True,
        slots=SAX_SLOTS,
        chart=_sax_chart(),
        presets=WIND_PRESETS,
    )


# ---------------------------------------------------------------------------
# B♭ clarinet — Boehm system (17 keys, 6 rings)
# ---------------------------------------------------------------------------

CLARINET_SLOTS = (
    FingerSlot("LT", "L Thumb (register)", "L", "thumb", ("Hole", "Register", "RegOnly")),
    FingerSlot("L1", "L Index", "L", "index", ("Hole", "A", "G#")),
    FingerSlot("L2", "L Middle", "L", "middle", ("Hole",)),
    FingerSlot("L3", "L Ring", "L", "ring", ("Hole",)),
    FingerSlot("L4", "L Pinky", "L", "pinky", ("E/B", "F/C", "F#/C#", "C#/G#")),
    FingerSlot("R1", "R Index", "R", "index", ("Hole", "Eb/Bb")),
    FingerSlot("R2", "R Middle", "R", "middle", ("Hole",)),
    FingerSlot("R3", "R Ring", "R", "ring", ("Hole",)),
    FingerSlot("R4", "R Pinky", "R", "pinky", ("F/C", "E/B", "F#/C#", "Ab/Eb")),
)


def _clarinet_chart():
    """Boehm B♭ clarinet fingerings by written pitch, E3 .. C6 (52 .. 84). Each entry lists
    only the fingers that press a key; every other finger is up.

    One fingering per pitch: the first ("Basic") fingering of the Woodwind Fingering Guide's
    Boehm chart (wfg.woodwind.org/clarinet), which agrees with J. M. Izen's chromatic chart and
    with Powell's little-finger key chart (Oxford University Press, ch. 34).

    Keys:
    - "Hole" is the tone hole or ring a finger closes.
    - Left thumb: "Register" = the thumb closes its hole *and* presses the register key (every
      clarion note); "RegOnly" = the register key with the thumb hole open (throat A#4 only).
    - Left index: "A" and "G#" are the throat keys (rolled onto with the index).
    - Right index: "Eb/Bb" is the lowest side key (D#4, A#5), pressed with the side of the finger.
    - Little fingers: E/B, F/C and F#/C# exist on both hands. The chart uses E/B and F#/C# on
      the left and F/C on the right, as the guide lists them first, so B4 - C5 - C#5 alternates
      hands. C#/G# is left only, Ab/Eb right only (standard 17-key instrument).
    """
    th = {"LT": "Hole"}
    lh = {**th, "L1": "Hole", "L2": "Hole", "L3": "Hole"}
    full = {**lh, "R1": "Hole", "R2": "Hole", "R3": "Hole"}
    low = {
        "E3": {**full, "L4": "E/B"},
        "F3": {**full, "R4": "F/C"},
        "F#3": {**full, "L4": "F#/C#"},
        "G3": dict(full),
        "G#3": {**full, "R4": "Ab/Eb"},
        "A3": {**lh, "R1": "Hole", "R2": "Hole"},
        "A#3": {**lh, "R1": "Hole"},
        "B3": {**lh, "R2": "Hole"},
        "C4": dict(lh),
        "C#4": {**lh, "L4": "C#/G#"},
        "D4": {**th, "L1": "Hole", "L2": "Hole"},
        "D#4": {**th, "L1": "Hole", "L2": "Hole", "R1": "Eb/Bb"},
        "E4": {**th, "L1": "Hole"},
        "F4": dict(th),
        # The thumb leaves its hole from F#4 up to the break (F#4 and the throat tones G4 .. A#4)
        "F#4": {"L1": "Hole"},
        "G4": {},
        "G#4": {"L1": "G#"},
        "A4": {"L1": "A"},
        "A#4": {"LT": "RegOnly", "L1": "A"},
    }
    chart = {parse_note_name(k): v for k, v in low.items()}
    # Clarion: the register key overblows a twelfth, so written B4 .. C6 is E3 .. F4 plus the
    # register key (the thumb stays on its hole), 19 semitones up. B4 is the break.
    for p in range(parse_note_name("E3"), parse_note_name("F4") + 1):
        chart[p + 19] = {**chart[p], "LT": "Register"}
    return chart


@register
def clarinet_bb():
    return Profile(
        id="CLARINET_BB",
        name="B♭ Clarinet",
        description="Boehm-system B♭ clarinet fingering; written pitch = concert + 2",
        monophonic=True,
        slots=CLARINET_SLOTS,
        chart=_clarinet_chart(),
        presets=WIND_PRESETS,
        default_transpose=2,
    )
