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
    FingerSlot("R1", "R Index", "R", "index", ("F", "SideBb", "SideC", "SideE")),
    FingerSlot("R2", "R Middle", "R", "middle", ("E",)),
    FingerSlot("R3", "R Ring", "R", "ring", ("D",)),
    FingerSlot("R4", "R Pinky", "R", "pinky", ("LowEb", "LowC")),
)


def _sax_chart():
    """Standard saxophone fingerings by written pitch (Bb3 .. F6). Each entry lists only the
    fingers that press a key; every other finger is up. Palm keys are simplified to one
    marker for the left index ("PalmEb" = D+Eb palm keys together, "PalmF" = D+Eb+F)."""
    lh = {"L1": "B", "L2": "A", "L3": "G"}
    rh = {"R1": "F", "R2": "E", "R3": "D"}
    full = {**lh, **rh}
    low = {
        "Bb3": {**full, "L4": "LowBb"},
        "B3": {**full, "L4": "LowB"},
        "C4": {**full, "R4": "LowC"},
        "C#4": {**full, "R4": "LowC", "L4": "LowC#"},
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
    return chart


@register
def monophonic_wind():
    return Profile(
        id="MONO_WIND",
        name="Monophonic Wind / Brass",
        description="Saxophone-style fingering; one note at a time (Aerophone, EWI, sax, ...)",
        monophonic=True,
        slots=SAX_SLOTS,
        chart=_sax_chart(),
        presets=(
            EffectPreset("CHEEKS", "Cheeks", "SHAPE_KEY", mode="DIRECT", shape_key="CheekPuff",
                         out_min=0.0, out_max=1.0, attack=0.04, release=0.15, curve=0.8,
                         blend="REPLACE"),
            EffectPreset("CHEST", "Chest", "BONE", mode="LUNG",
                         bone_keywords=("chest", "spine2", "spine.003", "upperchest", "upper_chest",
                                        "j_bip_c_upperchest", "spine1", "spine"),
                         channel="SCALE_XZ", out_min=0.0, out_max=0.04, attack=0.15, release=0.4,
                         blend="COMBINE"),
        ),
    )
