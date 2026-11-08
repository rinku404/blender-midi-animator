# MIDI Animator — notes for Claude

A Blender 5.x extension that bakes a recorded MIDI wind performance (Roland Aerophone GO) into
character animation (per-finger fingering, cheeks, lung-driven chest) and renders a
Guitar-Hero-style note HUD for video overlay.

## Working on a plan step?
Read `docs/plan/AGENT_BRIEF.md` first and follow it: one step per branch, and a report in
`docs/plan/reports/`. The plan and status board are in `docs/plan/PLAN.md`.

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
  (IK → pose assets, locks), `hold.py` (instrument on a strap bone, hands IK-locked to it), `bake.py` (NLA baking), `hud_draw.py` (gpu/blf preview + export),
  `actions.py` (slotted-action / NLA helpers), `state.py` (shared helpers).
- `midi_animator/__init__.py` imports `bpy` only inside `register()`. Keep it that way so
  `core` stays testable.

## Testing
```
python -m pytest tests/core                                        # core, anywhere
blender -b --factory-startup --python tests/test_in_blender.py      # end-to-end in Blender 5.2
blender --factory-startup --python tests/test_hud_in_ui.py              # HUD export/ProRes/composite/preview, needs a window
python tests/hud_preview.py examples/aerophone_sample.mid out/ 0.3 4.9   # HUD frames via Pillow
blender --command extension validate midi_animator                   # manifest (the e2e test doesn't check it)
```
New logic goes in `core/` with a pytest test whenever it doesn't need Blender.

## Status (2026-11-07)
- `core/`: done, 37 tests passing.
- `blender/`: `tests/test_in_blender.py` passes in Blender 5.2.3 (2026-11-07), and the built
  extension installs and enables. The HUD (viewport preview, PNG export, ProRes 4444 with alpha,
  composite scene) passes `tests/test_hud_in_ui.py` in Blender 5.2.3 with a window (2026-11-07, step 3).
  The composite copies the scene's view transform; under AgX/Filmic the HUD colours are toned (warned).
- `main` holds v1 since PR #4 (2026-11-07); the old single-file add-on is only in git history. `v1-rewrite` is retired.

## Conventions
- Generated finger poses: `F.<slot>.<key>.Down|Up` and `F.Rest` (pose assets). Key markers: Empties named
  `Key.<slot>.<key>` with custom props `midianim_slot` / `midianim_key`.
- Baked data: actions prefixed `MIDI_`, NLA tracks `MIDI: …`; the user's action goes to `Base: …`.
- Written pitch = file pitch + Transpose. Charts and the note map use written pitch.
