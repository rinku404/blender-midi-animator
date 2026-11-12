---
step: 12
title: "Fingering trial: CJ playing the clarinet"
status: done
branch: plan/step-12-fingering-trial
pr: "#14"
commits: 6fd2e75..60444a0
date: 2026-11-12
blender: Blender 5.2.3 LTS (C:\Program Files\Blender Foundation\Blender 5.2\blender.exe)
tests_core: 58 passed (python -m pytest tests/core)
tests_blender: ALL TESTS PASSED (tests/test_in_blender.py, -b --factory-startup); extension validate OK
decision_changes: none
---

# Step 12: Fingering trial: CJ playing the clarinet

Walk-through log: `docs/plan/notes/fingering-trial-checklist.md`.

## Summary
The fingering pipeline works end to end on CJ and the B♭ clarinet. Detect Fingers found all 9 fingers. The user placed
16 key markers in about 10 minutes. After Autoassign, Fill This File mapped all 21 notes, the bake fingered all 111
notes, and on playback the right fingers go down, the curls look natural enough and the thumb's hole/register change is
visible (the user's judgement).
Getting there needed two kinds of setup work:
- **Hold rebuilt.** The step 6 hold was wrong for a clarinet (almost horizontal, fingers over the back). It was rebuilt
  from the user's reference photo: 22° from vertical, tone holes forward, hands round the front.
- **Left hand tuned.** The left hand was tuned by script because Autoassign left the thumb, the index on the throat
  keys and the pinky 13–50 mm off.

Nine plugin issues were confirmed with the user: three *bad* (no way to set the instrument's front in Hold, the
status bar hides most Autoassign warnings, fingers can't roll along the tube) and six *polish*. Slot sharing (step 11)
wasn't exercised on CJ: the user chose the rebuilt five-finger hands.

## Acceptance criteria
- [x] Every note in the take bakes with a mapped fingering (or the report says why not): "Baked: 111 fingered notes; Chest
  ← CC2", no unmapped notes, no missing poses; Fill This File mapped 21 notes, all matching the chart (B4 = E3 + Register,
  G4 open, A4 = L1:A).
- [x] Both tables filled in, severities confirmed by the user (below, 2026-11-12).

## Plugin issues
Severities confirmed by the user on 2026-11-12. Numbering continues step 6's P1–P9.

| # | Area | What happened | Expected | Severity | Suggested fix |
|---|---|---|---|---|---|
| P10 | Hold | Nothing says which side of the instrument faces forward. The step 6 hold had the clarinet flat with the fingers over its back. The rebuild then needed the user's photo and two turns about the tube: one from a screenshot, one measured by rendering the tube at 13 angles. | Hold knows the instrument's front (tone holes) and turns it to face away from the player | bad | A "Front" control in the Hold box (pick the front from the markers, or a roll slider), and a front-facing check before Lock. |
| P11 | Autoassign | The miss warnings go into one status-bar line, which Blender cuts in the middle: 2 shown, 8 real (thumb, index A/G#, pinky). | Every miss readable | bad | List misses per finger in panel 2 (next to each pose) and in the Info log; keep the status line short ("8 fingers miss, see panel 2"). |
| P12 | Autoassign / fingers | Fingers only curl about the Bend Axis, so the index can't roll up the tube onto the throat A/G# keys, and the thumb can't reach round to its hole. Best hand pose found: 10–15 mm off. | Fingertips on their keys (≤ 5 mm) | bad | Allow a small knuckle swing along the instrument (index) and a thumb base that can turn about the tube, both limited; or let a key carry a "reach" offset the solver aims at. |
| P13 | Autoassign | The miss advice is always "check the Bend Axis, or move the marker within reach", even when the hand is the problem. | Advice that matches the cause | polish | Say the direction and distance the hand should move when the miss is along the instrument. |
| P14 | Fingers UI | "Shares Bones With" on a right-hand finger also offers the left hand's fingers and the left thumb. | Same-hand fingers only | polish | Filter by the slot's side. |
| P15 | Fingers UI | Each bone row has two look-alike ✕ buttons: Blender's clear-field ✕ and the plugin's remove-row ✕. | One clear meaning per button | polish | Use another icon for remove (e.g. a minus). |
| P16 | Packaging | Every build is version 1.0.0. The user installed the old step-6 zip (same name, one folder up) and saw no clarinet. | The installed build is identifiable | polish | Add a build/commit id to the manifest or the panel header. |
| P17 | Note Map UI | The list summary shows a finger on its first key bare ("L4" = L4:E/B, "LT" = LT:Hole). | Key always named | polish | Always print `slot:key`. |
| – | UI | Cut-off labels at the default sidebar width ("L Thu…", "Shares Bone…", "Instrum…"). | – | (step 6 P5, polish) | – |

## Test-setup limits and setup changes
| # | Area | What | Effect on the trial |
|---|---|---|---|
| T1 | Rig (setup change) | CJ's FBX bones pointed sideways (root, pelvis, legs, spine, neck, collarbones, wrists, face). Re-pointed along the body with deformation preserved (`scripts\tidy_rig.py`, `shorten_root.py`, `fix_leaf_bones.py`; mesh moved ≤ 0.0011 mm; Lock targets turned with the wrists). The 12 unused finger bones and the stray Icosphere were deleted, and In Front turned off. Backups `midi_trial_pre_tidy/_pre_root/_pre_leaf.blend`. | Readable rig; Detect still finds 9 fingers. Spine axes now standard, so the Chest preset's Scale X+Z is width + depth on CJ. |
| T2 | Hold (setup change) | Rebuilt from the user's photo (`scripts\hold_v2.py`, params `hold_v2_params.json`, backup `midi_trial_pre_hold2.blend`). | Markers on reachable keys; see P10. |
| T3 | Instrument model | The clarinet has no key names (its Sketchfab annotations only name reed, ligature, joints and bell), and its keywork isn't a faithful Boehm layout: the thumb ring sits level with L3, and the pinky clusters don't match a real clarinet. | Throat and side keys identified by eye ("likely"), pinky keys a best guess (agent's guide page). |
| T4 | Left hand (setup change) | Left-pinky F#/C# and E/B markers moved up beside C#/G# (they were 8–12 cm below the hand). Left hand searched over 4 parameters (~350 Autoassign runs, `scripts\tune_left.py`, backup `midi_trial_pre_tune_left.blend`). | Worst miss 50 → 14.8 mm, mean 6.7 mm. |
| T5 | Extension install | The old step-6 zip was installed first. The agent renamed it `OLD_step06_…` and copied the main build in. | See P16. |

## Changes
| File | What changed |
|---|---|
| `docs/plan/notes/fingering-trial-checklist.md` | New: click-by-click checklist and the walk-through log |
| `docs/plan/reports/step-12-fingering-trial.md` | This report |

No plugin code changed. Test-file scripts live in `D:\3D\blender_projects\midi_trial\scripts\`.

## Verification
```
python -m pytest tests/core -q
58 passed
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
ALL TESTS PASSED
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --factory-startup --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```
From the trial file (headless):
- markers: 16/16, within 2 mm of the clarinet, all arrows outward;
- Autoassign: 32 poses, 0.25 s per run;
- bake: tracks `MIDI: Fingering`, `MIDI: Hand Poses`, `MIDI: Chest`; every finger moves.

## Deviations from the plan or spec
- **Slot sharing on CJ:** not exercised. The user chose the five-finger hands; step 11's own tests and its run on CJ's
  original rig cover sharing.
- **Setup work by script:** the hold, the rig tidy and the left-hand tuning were done by script at the user's request.
  The UI walk resumed after each.
- **Markers:** the user placed them with a guide page the agent built (renders of this clarinet with each key circled),
  because the model has no key labels.

## Decisions
None. All changes are to the test file.

## Problems and risks
- The left thumb, the index on A/G# and the left pinky's E/B Up pose stay 10–15 mm off (P12).
- The pinky-key identities on this model are a guess (T3).
- `midi_trial.blend` now differs a lot from the user's original file. The backups and scripts are listed in T1–T4.

## Follow-ups for the planner
- **Step 7:** fix P10, P11 and P12 (*bad*), then P13–P17. Together with step 6's P1–P9, this is the step 7 scope.
- **Guide:** add a "set up the hold" section that shows a real player's photo, the instrument's front, and the thumb behind.
- **Hold:** consider a "fit the hand to the markers" helper that does what `tune_left.py` did (search the hand pose
  against Autoassign's misses).
- **Step 8:** it can use this file and take (111 notes, 54 s) as its baseline.

## Questions for the user
None open. The user confirmed: the right fingers go down on the notes they know, the curls look natural enough, the
thumb change is visible, and every severity is as proposed.
