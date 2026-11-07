# MIDI Animator — notes for Claude

A Blender 5.x extension that bakes a recorded MIDI wind performance (Roland Aerophone GO) into
character animation (per-finger fingering, cheeks, lung-driven chest) and renders a
Guitar-Hero-style note HUD for video overlay.

## Read first
- `docs/SPEC.md`: the agreed v1 design.
- `docs/decisions/`: one record per decision, with the reasons. Don't reverse a decision
  without the user. If one changes, add a new record that supersedes it.
- `docs/aerophone-guide.md`: the user-facing workflow.

## Layout
- `midi_animator/core/`: pure Python, **must never import `bpy`**. MIDI parser (`midi.py`),
  blow signal (`signal.py`), profiles + sax chart (`profiles.py`), fingering timeline
  (`fingering.py`), rig-name finger detection (`rigs.py`), HUD layout (`hud.py`), note names (`notes.py`).
- `midi_animator/blender/`: thin Blender layer: `props.py` (Scene.midi_animator), `ops.py`,
  `ui.py` (sidebar tab "MIDI"), `rig.py` (finger slots, key markers), `autoassign.py`
  (IK → pose assets, locks), `bake.py` (NLA baking), `hud_draw.py` (gpu/blf preview + export),
  `actions.py` (slotted-action / NLA helpers), `state.py` (shared helpers).
- `midi_animator/__init__.py` imports `bpy` only inside `register()`. Keep it that way so
  `core` stays testable.

## Testing
```
python -m pytest tests/core                                        # core, anywhere
blender -b --factory-startup --python tests/test_in_blender.py      # end-to-end in Blender 5.2
python tests/hud_preview.py examples/aerophone_sample.mid out/ 0.3 4.9   # HUD frames via Pillow
blender --command extension validate midi_animator                   # manifest (the e2e test doesn't check it)
```
New logic goes in `core/` with a pytest test whenever it doesn't need Blender.

## Status (2026-11-06)
- `core/`: done, 28 tests passing.
- `blender/`: `tests/test_in_blender.py` passes in Blender 5.2.3 (2026-11-07), and the built
  extension installs and enables. Still never run: HUD preview/export in `hud_draw.py` (ProRes 4444
  encode, composite scene). Those need the UI (GPU), not `-b`.
- The old single-file add-on was removed in this branch (it's still in git history on `main`).

## Conventions
- Generated finger poses: `F.<slot>.<key>.Down|Up` (pose assets). Key markers: Empties named
  `Key.<slot>.<key>` with custom props `midianim_slot` / `midianim_key`.
- Baked data: actions prefixed `MIDI_`, NLA tracks `MIDI: …`; the user's action goes to `Base: …`.
- Written pitch = file pitch + Transpose. Charts and the note map use written pitch.
