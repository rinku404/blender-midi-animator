"""Shared helpers between operators, baking, drawing and UI."""

import os

import bpy

from ..core import fingering, midi, profiles
from ..core.notes import note_name

_CACHE = {"path": None, "mtime": None, "data": None}


def settings(context=None):
    return (context or bpy.context).scene.midi_animator


def profile(s):
    return profiles.get(s.profile)


def load_midi(s):
    path = bpy.path.abspath(s.midi_path)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError("Choose a valid .mid file first")
    mtime = os.path.getmtime(path)
    if _CACHE["path"] != path or _CACHE["mtime"] != mtime:
        _CACHE.update(path=path, mtime=mtime, data=midi.parse_midi(path))
    return _CACHE["data"]


def try_load_midi(s):
    try:
        return load_midi(s)
    except Exception:
        return None


def performer_notes(s, data):
    """Notes of the performer (concert pitch, seconds), made monophonic if the profile is."""
    notes = data.notes_for(s.performer_track, s.performer_channel)
    return midi.monophonic(notes) if profile(s).monophonic else notes


def fps(scene):
    return scene.render.fps / scene.render.fps_base


def frame_of(s, scene, t):
    return s.start_frame + (t + s.time_offset) * fps(scene)


def time_of(s, scene, frame):
    return (frame - s.start_frame) / fps(scene) - s.time_offset


# -- note mapping ------------------------------------------------------------

def parse_combination(text):
    out = {}
    for part in text.split(";"):
        if "=" in part:
            slot, key = part.split("=", 1)
            if slot.strip() and key.strip():
                out[slot.strip()] = key.strip()
    return out


def format_combination(combo):
    return ";".join(f"{k}={v}" for k, v in sorted(combo.items()) if v)


def find_note(s, pitch):
    return next((m for m in s.notes if m.pitch == pitch), None)


def mapping_dict(s):
    """{written pitch: core NoteMap}."""
    return {m.pitch: fingering.NoteMap(parse_combination(m.combination), m.pose.name if m.pose else "")
            for m in s.notes}


def display_name(s, pitch, octave=None):
    """Name for UI and HUD from a written pitch, honouring the HUD naming settings."""
    h = s.hud
    p = pitch - s.transpose if h.pitch_display == "CONCERT" else pitch
    return note_name(p, flats=h.accidentals == "FLAT", solfege=h.naming == "SOLFEGE",
                     octave=h.show_octave if octave is None else octave)


def ui_name(pitch):
    return note_name(pitch)
