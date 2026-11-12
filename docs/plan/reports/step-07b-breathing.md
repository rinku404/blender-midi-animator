---
step: 7b
title: Breathing that looks real
status: done
branch: plan/step-07b-breathing
pr: pending (draft PR into main; the number is in the PR description)
commits: a64706a..b8b558c
date: 2026-11-12
blender: 5.2.3 LTS, C:\Program Files\Blender Foundation\Blender 5.2\blender.exe
tests_core: 77 passed
tests_blender: ALL TESTS PASSED (tests/test_in_blender.py, -b --factory-startup)
decision_changes: 0014 added; supersedes the Lung-mode and Chest-preset parts of 0007
---

# Step 7b: Breathing that looks real

## Summary
Lung mode is now the user's "refill at every break" breath planner (`signal.plan_breaths`, pure Python, no `sized`
rule). On the user's take it breathes 8 times, with a fitted lung size of 7.0 s and a minimum of 15.4 %, and it keeps
breathing slowly after the last note. Panel 4 (Blow) has a **Breathing** box: **Add Breathing** puts drivers on the
ribcage, belly, shoulders and torso that read one baked property (`breath_lung`) and five live sliders (Intensity,
Chest, Belly, Shoulders, Torso). The axes are read from each bone's real world orientation, so the tidied CJ rig and
the original FBX rig (spine bones pointing sideways, rolled) both breathe correctly. The neck, shoulders and the spine
bone below the ribcage stop inheriting scale: every bone except the three spine bones stays at scale 1.000 on both CJ
rigs, and the hands stay on the hold targets (0.0 mm). The old Chest preset is gone (Breathing replaces it). Nothing
here has been judged by eye by the user yet; the numbers are measured, the look is not.

## Acceptance criteria
Scope: the 7b row of `docs/plan/notes/step-07-scope.md` and the brief's six items (PLAN.md has no step 7 text yet).
- [x] **1. Core planner, Lung mode uses it, pytest.** `core/signal.py` `plan_breaths` / `blow_curve(..., spans=)`;
  `lung()` removed. Tests (`tests/core/test_signal.py`): breathes at every gap (39 breaths for 40 notes), refills toward
  full at each break, the inhale is limited by the gap length (0.48 of a lung in a 0.16 s window), legato dips breathe
  and 0.05 s gaps don't, a late first note gets a prep breath, tidal breathing after the end (0.3..0.7, never jumps),
  no notes / one sample, never under the reserve with the fitted size. The user's take, when the file is present:
  8 breaths, size 7.0 s, minimum 0.1535, never under 0.14, not frozen after the last note. `77 passed`.
- [x] **2. Breathing section in panel 4, Add Breathing, five sliders, live.** `blender/breathing.py`, `ui.py`,
  `props.py`, `ops.py` (`midianim.breathing_add`, `midianim.breathing_remove`). Intensity 0–2, parts 0–3, all default 1.
  e2e: master 0 / 1 / 2 gives ribcage depth scale +0 / +0.10 / +0.20, Chest 3 → +0.30, Chest 0 → still, all by
  setting the scene property only (its update callback wakes the rig), without a re-bake. Panel drawing is checked with a
  recording layout in the e2e test; a real-window screenshot was looked at (layout fine, one label shortened).
- [x] **3. Rig-aware axes.** `core/breathing.py` (`body_frame`, `pick_axes`, `lean_back_axis`, `lift_axis`, pytest) and
  `blender/breathing.py`. Real files, copies: `midi_trial.blend` (tidied) picked ribcage depth = local Z, width = local X;
  `midi_trial_c1_oldrig.blend` picked depth = local Z, width = local Y. World-space checks on both: shoulders rise
  0.58 cm and the head moves 3.0 cm backwards with full vs empty lungs, on both rigs. e2e: a CJ-style rig with upright
  spine and one with sideways, rolled spine bones (up to 23°): grown axes point along world Y (depth) and X (width).
  Note: the prototype's "width = local Y" was the vertical axis on the tidied rig (it stretched the bone upward).
- [x] **4. No head or arm growth; hands stay on the clarinet with Lock on.**
  `midi_trial.blend`: 74 bones other than the three spine bones, world scale 1.0000 at frames 1, 100, 514, 706, 734, 866,
  1100, 1250; hands on the hold targets 0.0 mm at all of them and at master 0 / 1 / 2. `midi_trial_c1_oldrig.blend` (after
  Guess Bones + Lock, which moved 4 arm tails as in 7a): 86 bones, same, 0.0 mm. e2e: first rig, max hand-to-target
  0.001 mm while breathing, sax scale error 6e-8; CJ-style rigs: head/arm scale error 8e-7 / 7e-7, hands 0.0006 / 0.0005 mm.
- [x] **5. Defaults:** chest depth 10 %, width 4 %, belly 6 %, shoulders 3°, torso +2° / −1° (lower half of that),
  all sliders 1 (`core/breathing.py`, asserted in the e2e test: 1.10 / 1.04 / 1.06).
- [x] **6. Guide:** `docs/aerophone-guide.md` section 5 rewritten (Breathing steps with click locations, slider table,
  limits), Hold section and Troubleshooting updated. The Chest preset is gone (see Decisions).

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/signal.py` | `plan_breaths`, `Breath`/`BreathPlan`, `spans_from_blow`; `blow_curve(spans=)`; Lung mode uses the planner; `lung()`, `lung_capacity`, `refill_time` removed |
| `midi_animator/core/breathing.py` (new) | defaults, `body_frame`, `face_the_instrument`, `pick_axes`, `lean_back_axis`, `lift_axis` |
| `midi_animator/core/profiles.py` | Chest preset removed |
| `midi_animator/blender/breathing.py` (new) | `setup` / `remove`: drivers, inherit-scale, effect, setup record |
| `midi_animator/blender/bake.py` | `effect_notes`; spans passed to the planner; Lung effects baked to the scene's end frame |
| `midi_animator/blender/props.py` | five `breath_*` scene sliders (+ update callback); `lung_capacity`/`refill_time` removed; tooltips |
| `midi_animator/blender/ops.py`, `ui.py` | Add / Remove Breathing operators; Breathing box at the top of panel 4 |
| `midi_animator/blender/hold.py` | Unlock keeps Inherit Scale off where Breathing needs it |
| `tests/core/test_signal.py`, `tests/core/test_breathing.py` | planner and geometry tests |
| `tests/test_in_blender.py` | Breathing checks on the main rig (hold locked) and on upright and sideways CJ-style rigs |
| `docs/decisions/0014-…`, `docs/aerophone-guide.md`, `docs/SPEC.md`, `CLAUDE.md`, ADR 0007 note, README | docs |

## Verification
```
python -m pytest tests/core -q                                        -> 77 passed
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
                                                                      -> ALL TESTS PASSED
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
                                                                      -> Success parsing TOML in "midi_animator"
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --factory-startup --python tests/test_hud_in_ui.py
                                                                      -> ALL HUD UI CHECKS PASSED (run before the last label change)
```
Real-file checks (copies in a scratch folder, nothing written to `D:\3D\blender_projects\midi_trial\`): a script ran
Add Breathing + Bake on both blends and measured scale, hand error, master 0/1/2 and per-part world movement; numbers above.
The user's take, via the plugin's own functions (CC2, attack 0.15 / release 0.4, 24 fps): 8 breaths at 9.5, 14.9, 21.2,
29.5, 35.5, 41.0, 45.1 and 48.4 s, lung size 7.0 s, minimum 0.1535.

## Deviations from the plan or spec
- The **Chest preset is removed**, not kept (see Decisions).
- `lung_capacity` and `refill_time` are gone from the effect settings (the planner fits its own size).
- Lung-mode effects are baked to at least the scene's end frame (the strip would freeze after the last note otherwise).
- On a rig where the shoulder bone *is* the arm's IK root (no clavicle), the shoulder lift is skipped (the IK would re-solve it).

## Decisions
- **Mechanism: drivers on one baked property, sliders in the scene** (ADR 0014). Live sliders are the user's requirement.
  Bake-time channels with NLA influence can't do it: one influence per part means one curve per part and the strength is
  fixed at bake, a scale or rotation influence doesn't scale about the user's own pose, and the master would need a
  re-bake. Drivers are simple arithmetic, so no script auto-run is needed. Cost: they override the user's own animation on
  those bones (below).
- **Chest preset removed.** Everything it did is in Breathing; it caused P3 (lowest spine bone, Rigify axes). The generic
  Bone effect with Lung mode and Scale X+Z remains for a single channel.
- Body front is read from the left and right shoulders (found from the hold hands) with a turn-round check against the
  instrument, not from the rig's −Y.
- `breath_lung` starts at 0.5 before the first bake so an unbaked rig isn't puffed up.

## Problems and risks
- Drivers override animation of the same channels (ribcage, the two spine bones below it, shoulders). Add Breathing also
  switches those bones to XYZ Euler. Not a problem on the two CJ files (nothing keyed there), but a rig with an idle that
  animates the spine loses it while Breathing is on.
- Sliders live in the scene: a rig appended into another scene needs Add Breathing again.
- Bones rolled away from the body axes scale along their own rolled axis (up to 23° off in the test); CJ's real ones are
  at most ~27° off on the ribcage, which matches what the prototype did.
- A take with no breaks at all can't breathe in: the lung size reaches its 60 s ceiling and the air just runs down.
- Short gaps (0.15–0.2 s) give 4-frame breaths; the parked "start the breath earlier" idea is not built.
- The user hasn't looked at the result on the mesh; I verified numbers and a panel screenshot only.

## Follow-ups for the planner
- Ask the user to look at the breathing on `midi_trial.blend` after Add Breathing + Bake (Intensity 1 and 2) before 7d.
- Add a "base animation on the same bones" warning to Add Breathing if 7d wants it (detect a keyed channel on those bones).
- Decide whether the parked early-breath idea (start up to 0.15 s before the gap, at least 0.3 s long) belongs in 7d.
- Consider copying the user's recording into `tests/` (it is only read from `D:\3D\blender_projects\midi_trial\src\` or `MIDI_ANIMATOR_TAKE` now, so the take test skips elsewhere).

## Questions for the user
None open. I decided the open choices myself: Chest preset removed, drivers as the mechanism.
