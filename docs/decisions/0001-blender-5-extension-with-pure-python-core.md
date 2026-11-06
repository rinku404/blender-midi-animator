# 0001. Blender 5.x extension with a pure-Python core

Status: accepted (2026-11-06)

## Context

The v0.2 add-on was one 1,572-line file using `bl_info`, and none of its logic could be tested without Blender.

## Decision

Ship as a Blender **5.x Extension** (`blender_manifest.toml`, minimum 5.0). Split the code into:
- `midi_animator/core/`: pure Python with **no `bpy` imports** (MIDI parsing, blow signal, profiles, fingering timeline, rig-name detection, HUD layout). Tested with plain pytest.
- `midi_animator/blender/`: a thin layer (properties, operators, baking, drawing, panels).

`midi_animator/__init__.py` only imports `bpy` inside `register()`, so `core` stays importable outside Blender.

## Consequences

Most logic is tested in milliseconds. Blender-only behaviour is covered by one end-to-end script (`tests/test_in_blender.py`). Supporting Blender 3.x/4.x is out of scope.
