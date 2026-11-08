---
step: 5
title: "Chart completion: F#6, and a check against the old chart"
status: done
branch: plan/step-05-chart
pr: (set after the PR is opened)
commits: ad40820..(report commit)
date: 2026-11-08
blender: 5.2.3 LTS, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 39 passed
tests_blender: ALL TESTS PASSED
decision_changes: none
---

# Step 5: Chart completion: F#6, and a check against the old chart

> **Flag for the planner:** the plan lists low C# (`R4:LowC` + `L4:LowC#`) as an *intentional*
> difference, following step 1's report. I think that's a mistake in v1 and **fixed it**: the standard
> low C# fingering is the six main fingers plus the left pinky's C# key alone. The keywork closes the
> low C pad by itself. PR #2 had the same thing (`LP` only). Revert the one line in `_sax_chart` if the user disagrees.

## Summary
The built-in sax chart now covers written Bb3–F#6 (58–90). F#6 = octave + `L1:PalmF` + `R1:HighF#`.
`HighF#` is a new key on the right index (R1), and its marker sits where the right hand presses
side E and high F# together, the same simplification as the palm keys. I compared the chart with PR #2's
`chart_elements` in a script. All 33 pitches match at element level now that low C# is fixed (it was the
only real mistake). The remaining differences are finer key detail and no clamping, which
`_sax_chart`'s docstring describes. The guide has a D6–F#6 table and says where to put each palm and side
marker. New pytest checks cover the full range, slot keys and the octave key from 74 up. The e2e test fills
the whole chart and checks that the `HighF#` poses get generated.

## Acceptance criteria
- [x] `max(chart) == 90`, and tests pass: `test_sax_chart_basics` asserts `max(SAX.chart) == n("F#6") == 90`.
      `test_sax_chart_full_range` asserts `sorted(SAX.chart) == list(range(58, 91))`. pytest: 39 passed.
      `test_in_blender.py`: ALL TESTS PASSED. Validate: success. (See Verification.)
- [x] The report lists every changed chart entry with its reason: see *Chart changes* below.

## Chart changes
| Pitch | Before | After | Reason |
|---|---|---|---|
| 90 (F#6) | no entry | `LT:Octave`, `L1:PalmF`, `R1:HighF#` | New: completes PR #2's range. Palm D+Eb+F, side E and high F#. The two right-hand side keys are one marker (`HighF#`). |
| 61 (C#4) | six fingers + `R4:LowC` + `L4:LowC#` | six fingers + `L4:LowC#` | Fix: the standard low C# fingering doesn't use the right pinky. Pressing the C# key closes the low C pad mechanically. This now matches PR #2 (`LP` only). |

No other entry changed. Slot change: R1's keys are now `F, SideBb, SideC, SideE, HighF#`. The new key
goes last, so R1's home key (`F`), `F.Rest` and existing markers and poses don't change.

### Why `R1:HighF#` and not a new slot
- The high F# key sits with the right-hand side keys, and the side of the right index presses it with side E.
  R1 already owns the side keys (`SideBb`, `SideC`, `SideE`).
- In the marker model one finger presses one marker. Keys pressed together are one marker
  (`PalmEb` = D+Eb, `PalmF` = D+Eb+F). `HighF#` = side E + high F# follows that rule.
- A new slot would need its own bone chain. Detect Fingers, Autoassign, `F.Rest` and the
  bake all work per finger chain, and there's no "palm" chain to drive. It would also show a 10th finger
  row in the UI for one note.

### Intentional differences from PR #2 (now in `_sax_chart`'s docstring)
Compared at element level (L4→LP, R4→RP, LT→OctaveKey, palm/side/high keys→Palm), 58–90: **0 differences**.
At key level, v1 is finer:
- Bb3, B3, C#4, G#4 use different left-pinky keys (`LowBb`, `LowB`, `LowC#`, `G#`). C4 and D#4 use `LowC` and `LowEb`.
- D6–F#6 name the palm and side keys pressed (PR #2 had one `Palm` element).
- Pitches outside 58–90 aren't mapped, so Analyze and Bake report them. PR #2 clamped them silently.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/profiles.py` | R1 gains the `HighF#` key. F#6 entry added. C#4 drops `R4:LowC`. The docstring describes the combined markers and the intentional differences from PR #2. |
| `tests/core/test_fingering.py` | `max == 90`. New `test_sax_chart_full_range` (58–90 all mapped, every key in its slot, octave key iff pitch ≥ 74). New `test_sax_chart_palm_and_side_keys` (D6–F#6 exact, C#4, R1 home key unchanged). |
| `tests/test_in_blender.py` | After Fill: This File, Fill: Whole Chart gives 33 rows, 58–90. F#6's combination is checked, and `F.R1.HighF#.Down/Up` must exist after Autoassign. |
| `docs/aerophone-guide.md` | "Whole Chart maps Bb3–F#6". New *High notes* table (D6–F#6: L1 and R1 markers) with where to place `PalmD`, `PalmEb`, `PalmF`, `SideE` and `HighF#`. |
| `CLAUDE.md` | Status: 39 core tests, chart to F#6. |

## Verification
```
python -m pytest tests/core -q
39 passed in 0.19s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
Info: 42 poses created; Rest pose: F.Rest
bend: max against the axis 0.000 deg, max on locked axes 0.000 deg, max tip-to-target distance (Down and Up) 2.28 mm
...
Info: Filled 14 notes
Info: Filled 19 notes
...
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"

python compare.py old_chart.py      # PR #2's SAX_CHART/chart_elements (git show dc74f08) vs _sax_chart
pitches 58-90 compared: 33 differences at element level: 0
```
Autoassign now makes 42 poses on the test rig (40 before: +Down/Up for `R1:HighF#`). The bend and
tip numbers are the same as step 4's (0.000°, 2.28 mm max), so the fifth R1 marker, 12 mm to the side,
is reachable. 14 + 19 = 33 rows = the whole chart.

## Deviations from the plan or spec
- Low C#: the plan calls the v1 combination intentional. I treated it as a real mistake and fixed it (see the flag at the top).
- Small extra: the e2e test also runs Fill: Whole Chart and checks the `HighF#` poses. The plan only asked for pytest.

## Decisions
- Slot for high F#: `R1`, key `HighF#` (reasons above). No ADR. This is profile data inside ADR 0002/0003.

## Problems and risks
- On the real horn, the high F# key and the side keys sit in slightly different places on alto and tenor. One combined
  marker is an approximation like the palm markers, so the user places it by eye in step 6.
- Saved `.blend` files that already have a C#4 note-map row from Fill keep the old combination
  (Fill doesn't overwrite unless *Overwrite Existing* is ticked). That only matters for the user's own files.
- `git stash` still holds the old `/init` `CLAUDE.md` edits (stash@{0}, from step 1). I left it alone.

## Follow-ups for the planner
- Add to step 6's checklist: place `HighF#` (and the palm markers) on the real sax using the guide's table, and check that the R1 reach and pose look right.
- Ask the user in step 6 to confirm the low C# fix and the F#6 fingering (they play the instrument).
- Consider for step 7: alternate fingerings (front F for F6 and F#6, side Bb/C, bis Bb) as optional per-note choices. The chart only has one fingering per pitch, and `L1:FrontF` / `R1:SideBb` / `R1:SideC` are slot keys the chart never uses.

## Questions for the user
None asked. The low C# fix is a judgement call; see the flag at the top.
