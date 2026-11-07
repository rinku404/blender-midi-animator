---
step: 1
title: "Reconcile `main` into `v1-rewrite`"
status: done
branch: plan/step-01-reconcile
pr: https://github.com/rinku404/blender-midi-animator/pull/4
commits: ccfce41 (merge) + the report commit
date: 2026-11-07
blender: 5.2.3 LTS, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 28 passed
tests_blender: ALL TESTS PASSED
decision_changes: none
---

# Step 1: Reconcile `main` into `v1-rewrite`

## Summary
Merged `origin/main` (PR #2, `dc74f08`) into a branch from `origin/v1-rewrite` and resolved the four
conflicts in v1's favour: `midi_animator.py` stays deleted, `tests/test_chart_and_hold.py` is removed,
and v1's `README.md`, `docs/aerophone-guide.md` and `tests/test_in_blender.py` are kept. PR #2's hold
assertions and its guide text are saved in `docs/plan/notes/` for step 2. The chart comparison below
finds one real difference in 58–89 (C#4), plus F#6 missing in v1 (step 5). All tests pass.

## Acceptance criteria
- [x] `git merge-base --is-ancestor origin/main HEAD` succeeds: printed `ancestor-ok` on the branch.
- [x] No `midi_animator.py` and no `tests/test_chart_and_hold.py`: `ls` reports both missing.
- [x] Both notes files exist and are non-empty: `docs/plan/notes/hold-tests-to-port.md` (4675 bytes),
      `docs/plan/notes/hold-guide-text.md` (1961 bytes).
- [x] Chart-difference table: below.
- [x] pytest and `test_in_blender.py` pass: see Verification.

## Changes
| File | What changed |
|---|---|
| `midi_animator.py` | stays deleted (modify/delete conflict resolved as delete) |
| `tests/test_chart_and_hold.py` | removed; hold block and `build()` rig copied to the notes file |
| `README.md`, `docs/aerophone-guide.md`, `tests/test_in_blender.py` | v1 versions kept (tree identical to `origin/v1-rewrite` for these) |
| `docs/plan/notes/hold-tests-to-port.md` | new: PR #2 hold assertions and test rig, with porting hints |
| `docs/plan/notes/hold-guide-text.md` | new: PR #2 "2b. Hold the sax like a player", troubleshooting line, replaced text |
| `docs/plan/reports/step-01-reconcile.md` | this report |

## Chart comparison (written pitch 58–90)
PR #2 (`SAX_CHART` / `chart_elements`) against `core/profiles.py::_sax_chart`. I compared them in a script,
mapping v1 slots to PR #2 elements (L4→LP, R4→RP, LT→OctaveKey, any Palm*/SideE key→Palm).
All other pitches 58–89 are identical at element level; the exceptions are the rows below.

| Pitch | PR #2 elements | v1 combination | Comment |
|---|---|---|---|
| 61 (C#4) | L1 L2 L3 R1 R2 R3 LP | L1 B, L2 A, L3 G, R1 F, R2 E, R3 D, R4 LowC, L4 LowC# | v1 presses the low C key with the right pinky *and* the low C# key with the left. That is the real fingering (both pinkies); PR #2 has only LP. Intentional. |
| 90 (F#6) | OctaveKey Palm | no entry (v1 chart stops at 89 / F6) | Real gap, step 5 adds the high F# key. |
| 86–89 (D6–F6) | OctaveKey Palm (one element) | LT Octave + L1 PalmD / PalmEb / PalmEb / PalmF, and R1 SideE for 88–89 | v1 is finer: PR #2 collapses all palm notes into one `Palm` pose. Intentional, but the guide must say which palm marker each note uses. |
| 58, 59, 61, 68 | LP | L4 with a different key each (LowBb, LowB, LowC#, G#) | Same element; v1 has distinct markers per key. Intentional. |
| 60, 63 | RP | R4 LowC / LowEb | Same. |
| <58, >90 | clamped to 58 / 90 | not mapped | v1 reports unmapped notes at Analyze/Bake; PR #2 silently clamped. Intentional per the spec ("never silent"). |

Octave notes 74–85 match exactly (same fingering + OctaveKey).

## Verification
```
python -m pytest tests/core -q
28 passed in 0.31s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
... Info: Removed 3 MIDI tracks
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"

git merge-base --is-ancestor origin/main HEAD   # exit 0
```

## Deviations from the plan or spec
None. Note: the working tree had an uncommitted `CLAUDE.md` edit (from an earlier `/init`); I stashed it
before branching and did not include it here (still in `git stash`).

## Decisions
None.

## Problems and risks
- `main` still contains the old single-file add-on, so anyone installing from `main` gets the old version until PR #3 merges.

## Follow-ups for the planner
- Add to step 5: palm notes 86–89 need guide text on which palm marker to place, and F#6 is the only missing pitch.
- Decide what to do with the stashed `CLAUDE.md` improvements (header, bake flow, single-test command).

## Questions for the user
None.
