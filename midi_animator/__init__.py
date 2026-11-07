"""MIDI Animator — Blender extension entry point.

bpy is only imported inside register()/unregister() so that the pure-Python core in
`core/` can be imported and tested outside Blender.
"""


def register():
    from .blender import register as _register
    _register()


def unregister():
    from .blender import unregister as _unregister
    _unregister()
