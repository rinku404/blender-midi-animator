---
step: 2
title: "Port \"Hold the Instrument\" to v1"
status: done
branch: plan/step-02-hold
pr: see PR description (into main)
commits: see PR
date: 2026-11-07
blender: 5.2.3 LTS, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 32 passed
tests_blender: ALL TESTS PASSED
decision_changes: ADR 0011 added (refines 0004). Deviates from the plan's preferred option (a), see Decisions.
---

# Step 2: Port "Hold the Instrument" to v1

**Flag:** the plan preferred option (a) for the breathing conflict; I implemented (b), because (a) cannot work (details under Decisions).

## Summary
The instrument now hangs from a strap bone through a scale-free Child Of constraint, and both hands are
locked to per-hand targets (children of the instrument) with a 2-bone forearm IK plus Copy Rotation, as in PR #2.
`core/rigs.py::guess_hold_bones` guesses strap and hands (Rigify, Mixamo, VRoid, Biped, plain names); the Hold box
sits at the top of panel 2 with Guess, Lock and Unlock. Locking moves nothing, the sax and hands follow a chest bend,
re-lock is idempotent, unlock cleans up, and after a bake with the Chest effect the sax world scale stays 1.0. One
limit: Blender's IK is inexact under the scaled chest, so hands sit up to 7.9 mm off their targets at peak breath.

## Acceptance criteria
- [x] All tests above pass. Bone-guess pytest covers at least 3 naming conventions: 4 new pytest tests (Rigify, Mixamo,
      VRoid + Biped, plain/empty); `32 passed`. Hold assertions in `tests/test_in_blender.py` (`hold_checks`, `hold_breath_checks`) pass.
- [x] ADR 0011 is written and indexed in `docs/decisions/README.md`.
- [x] Autoassign still passes its tip-distance test with the hold locked: `tip distance with hold locked: 0.0000` (< 4 mm required);
      the original test (without hold) still reports `down 0.0000, up 0.0120`.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/rigs.py` | `guess_hold_bones(bones)` + ranking helpers |
| `midi_animator/blender/hold.py` | new: `guess_bones`, `check`, `lock_hands`, `unlock_hands` |
| `midi_animator/blender/props.py` | `hold_strap_bone`, `hold_hand_l`, `hold_hand_r` |
| `midi_animator/blender/ops.py` | operators `guess_hold_bones`, `lock_hands`, `unlock_hands` |
| `midi_animator/blender/ui.py` | "Hold the instrument" box at the top of panel 2 |
| `tests/core/test_rigs_hud.py` | 4 bone-guess tests |
| `tests/test_in_blender.py` | test rig gains `upper_arm`/`forearm` bones (IK needs a forearm); hold checks added |
| `docs/aerophone-guide.md`, `docs/decisions/0011-*.md`, `docs/decisions/README.md`, `CLAUDE.md` | guide section, ADR, index, layout/status |

## Verification
```
python -m pytest tests/core -q
32 passed

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
tip distance: down 0.0000, up 0.0120
tip distance with hold locked: 0.0000
max sax scale error 0.00e+00; chest scale up to 1.013; bone-parented probe 1.040
max hand-to-target gap while breathing: 7.9 mm
Info: Removed 4 hold constraints
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```

## Deviations from the plan or spec
- Option (b) instead of (a), see below.
- Unlock keeps the instrument on the strap (like PR #2); the plan's "unlock cleans up" is applied to the hand constraints and targets.
- Lock keeps existing `MIDI Hold` targets instead of re-placing them, so re-locking doesn't undo a grip the user adjusted.
- The test rig got arm bones (the PR #2 rig had them; v1's had hands parented to the chest, so there was no forearm to put the IK on).
- Strap guess prefers the highest spine bone by name (`spine2` > `upperchest` > `spine.003` > `chest` > `spine`).

## Decisions
ADR 0011. Option (a) (Chest effect avoids the strap bone) fails: scale is inherited down the hierarchy, so the effect bone
would have to be neither the strap bone nor any ancestor of it, yet the upper chest is both the natural strap bone and the
natural breathing bone, and the test rig has no such bone. The test shows the conflict is real: a bone-parented probe
reaches scale 1.040 while the Child Of (scale off) instrument stays at exactly 1.0.

## Problems and risks
- **IK under a scaled chest is inexact:** hand-to-target gap up to 7.9 mm at the default Chest `out_max` 0.04 (test rig, forearm 0.25 m).
  On the real rig this could matter for fingertip-on-key accuracy; check in step 6.
- Rigify generated rigs have no plain `hand.L` (they have `hand_fk.L`, `hand_ik.L`); the guess picks `hand_fk`, but IK on the forearm
  may fight Rigify's own IK/FK switch. Untested on a real Rigify rig.
- The Child Of strips the rig object's scale too; a scaled Armature object would not scale the instrument.
- Not run in the UI: panel layout of the Hold box was not looked at (needs a window); drawn only through `-b` registration.

## Follow-ups for the planner
- Add to step 6: check hand accuracy under breathing and the Hold box on the real rig (Rigify `hand_fk`).
- Consider a step 4 task: remove the Chest-induced IK error (for example, compensate the scale or turn off arm scale inheritance).
- Decide whether the stashed `CLAUDE.md` edits should be applied; I left the stash alone.

## Questions for the user
None.
