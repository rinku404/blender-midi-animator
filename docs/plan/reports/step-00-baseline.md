---
step: 0
title: "Baseline: core + Blender layer"
status: done
branch: v1-rewrite
pr: https://github.com/rinku404/blender-midi-animator/pull/3
commits: 6e2eff0..d871b70
date: 2026-11-07
blender: 5.2.3 (run by the user's Claude Code, per d871b70)
tests_core: 28 passed
tests_blender: ALL TESTS PASSED
decision_changes: ADRs 0001–0010 created
---

# Step 0: Baseline

## Summary
The v1 rewrite from the 2026-11-06 design session. The pure-Python core and the Blender layer are written,
and the extension validates, installs and enables in Blender 5.2.3. The end-to-end test covers finger
detection, markers, Autoassign (tip on marker < 4 mm, Up above it), pose locking, Fill From Chart, Cheeks and
Chest (Lung) effects, the missing-CC flow, bake, re-bake and clear. The HUD has only been checked as layout (Pillow
preview). Its Blender drawing, export, ProRes and composite code have never run.

## Acceptance criteria
- [x] Core tested: `python -m pytest tests/core` → 28 passed.
- [x] Blender e2e: `test_in_blender.py` passes in 5.2.3 (commit d871b70 message).
- [x] Manifest valid: tagline shortened to under 64 characters (d871b70).
- [ ] HUD in Blender: not run (needs the UI). Moved to step 3.

## Changes
See PR #3. Layout is in CLAUDE.md.

## Deviations from the plan or spec
- The palm keys are simplified to one marker per combination (PalmD, PalmEb, PalmF).
- The chart stops at F6. PR #2's chart goes to F#6 (step 5).

## Problems and risks
- PR #2 was merged into `main` after v1 branched. It adds a hand lock and a different per-finger chart to the old
  file, and PR #3 now conflicts (steps 1–2).
- The Chest effect scales a chest bone. If the instrument hangs from that bone (PR #2's hold), it will scale too (step 2).
- IK can bend fingers sideways or backwards on real rigs; the test rig is too simple to show it (step 4).

## Follow-ups for the planner
- Reconcile `main` into `v1-rewrite` before any more work lands on either.
- Port the hand lock and guard against chest scaling.
- Verify the HUD in the UI.
- Add F#6 and compare with PR #2's chart.

## Questions for the user
None.
