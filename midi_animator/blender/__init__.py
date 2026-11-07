"""Blender layer: registration."""

import bpy
from bpy.props import PointerProperty

from . import hud_draw, ops, props, ui

_classes = props.classes + ops.classes + ui.classes


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.midi_animator = PointerProperty(type=props.MIDIANIM_Settings)
    hud_draw.enable_preview()


def unregister():
    hud_draw.disable_preview()
    del bpy.types.Scene.midi_animator
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
