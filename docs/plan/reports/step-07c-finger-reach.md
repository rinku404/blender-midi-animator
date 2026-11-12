---
step: 7c
title: Finger reach (P12, P11, P13)
status: partial
branch: plan/step-07c-finger-reach
pr: 17 (draft)
commits: 8cace65..HEAD
date: 2026-11-12
blender: 5.2.3, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 80 passed
tests_blender: ALL TESTS PASSED
decision_changes: ADR 0015 added (supersedes the joint-limit and miss-report part of ADR 0004's step-4 note)
---

# Step 7c: Finger reach

> **ADR 0015** supersedes part of ADR 0004's note: a finger knuckle may swing along the instrument,
> and the thumb's base may turn about its own length.

## Summary
Autoassign has two new limited freedoms, both scene settings. **Knuckle Swing** (default 15°) adds to
every finger root's sideways spread, which runs along the tube. **Thumb Turn** (default 30°) lets the
thumb's base joint turn about its own length; it is the only twist Keep Twist allows. Middle and end
joints still only curl.

Each pose that misses its key now stores the miss and an advice. Panel 2 lists it under the finger's
poses, the Info log gets one line per finger and one per missing pose, and the status bar stays short.
The advice says which way and how far to move the hand: up or down the tube, toward or away from the
keys, or round the tube.

On the user's file (fixed hold, 2026-11-12), 14 of the 20 left-hand poses are now within 5 mm, up from 4.
The left worst is 11.6 mm, down from 16.5, and the mean over all 32 poses is 3.2 mm, down from 7.8.
Every index, middle and ring pose is ≤ 3.7 mm.
**Six left poses stay over 5 mm** (thumb Up poses, pinky C#/G# and F#/C#), so the ≤ 5 mm target is
**partial**. Larger settings close most of them (Swing 25°, Thumb 45°: 18 of 20 within 5 mm), but I
kept the user's 15° and an anatomical 30°; see Decisions.

## Acceptance criteria
- [x] **Index roll (P12):** the knuckle swings along the instrument, as the Knuckle Swing setting
  (default 15°, 0–45°). Middle and end joints stay bend-only. Evidence: L1 A Down 16.3 → 2.3 mm and
  L1 G# Down 16.5 → 3.7 mm on the user's file. In the e2e test, a key 38° to the side misses by
  16.1 mm at swing 0 and is reached within 0.00 mm at 15°.
- [x] **Thumb turn (P12):** the thumb's base turns about its length within ±Thumb Turn (default 30°,
  0–60°). Evidence: LT Hole Down 5.3 → 0.0 and LT Register Down 5.2 → 1.2 mm. In the e2e test, a key
  needing a 28° turn misses by 3.8 mm at 0° and is reached within 0.00 mm at 30°.
- [x] **Keep Twist honoured:** `bend_checks` in the e2e test still gives under 1° against the bend
  axis and on locked axes for every pose. The thumb's base twist is checked against Thumb Turn instead.
- [x] **Readable misses (P11):** each missing pose shows "… mm off" and its advice in panel 2. The
  Info log gets one line per finger plus one per pose, and the status bar reads
  "32 poses; 5 fingers miss: see panel 2 (details in the Info log)". The e2e test checks the
  per-finger line, `misses()` per slot, the log lines and the status line.
- [x] **Advice (P13):** `core.rigs.miss_advice` splits the miss along the tube, found from the
  markers' principal axis and signed by slot order, and along the marker's Z. Covered by pytest
  `test_miss_advice` and `test_tube_axis`. On the user's file it says, for example, "F.L4.F#/C#.Down:
  11 mm off; move the hand 10 mm down the tube, toward the bell (or the marker the other way)".
- [x] **Locked poses keep their behaviour:** nothing in the lock path changed. The e2e lock test passes,
  and a skipped locked pose keeps its old miss props.
- [ ] **Every left-hand pose ≤ 5 mm on the user's file:** 14 of 20. The six that still miss are listed below.
- [x] **Middle and ring not worse:** L2, L3, R2 and R3 are all 0.0 mm after; before, L2 Hole Down was
  7.1 and L3 Hole Down 8.6.

## Measurement on the user's file
I re-copied `midi_trial.blend` after the hold fix (`fix_hold3.py`) and measured a scratch copy. NLA
tracks were muted, `breath_intensity` set to 0, frame 1, and Autoassign ran with Overwrite Locked. The
script applies each generated pose and measures the tail of the chain's last bone against the marker
(Down) or the marker plus hover times its Z (Up). Script: `measure.py` in the session scratchpad,
the same idea as `tune_left.py`'s `errors()`. Markers and hand were not moved.

The last column is not shipped; it shows what larger settings give.

| Pose | Before | After (Swing 15°, Thumb 30°) | Swing 25°, Thumb 45° |
|---|---:|---:|---:|
| LT Hole Down | 5.3 | 0.0 | 0.0 |
| LT Hole Up | 10.5 | **6.0** | 0.7 |
| LT Register Down | 5.2 | 1.2 | 0.1 |
| LT Register Up | 15.3 | **11.6** | 7.8 |
| L1 A Down | 16.3 | 2.3 | 0.0 |
| L1 A Up | 5.5 | 0.0 | 0.0 |
| L1 G# Down | 16.5 | 3.7 | 0.0 |
| L1 G# Up | 5.6 | 0.0 | 0.0 |
| L1 Hole Down | 3.3 | 0.0 | 0.0 |
| L1 Hole Up | 0.0 | 0.0 | 0.0 |
| L2 Hole Down | 7.1 | 0.0 | 0.0 |
| L2 Hole Up | 0.0 | 0.0 | 0.0 |
| L3 Hole Down | 8.6 | 0.0 | 0.0 |
| L3 Hole Up | 0.0 | 0.0 | 0.0 |
| L4 C#/G# Down | 12.8 | **5.9** | 0.0 |
| L4 C#/G# Up | 15.6 | **7.4** | 0.0 |
| L4 E/B Down | 14.2 | 0.0 | 0.0 |
| L4 E/B Up | 8.8 | 0.0 | 0.0 |
| L4 F#/C# Down | 15.5 | **10.8** | 7.2 |
| L4 F#/C# Up | 14.4 | **6.9** | 1.5 |
| R1 Eb/Bb Down | 16.4 | 14.0 | 11.7 |
| R1 Eb/Bb Up | 11.0 | 6.1 | 2.5 |
| R1 Hole Down | 11.4 | 1.2 | 0.0 |
| R1 Hole Up | 3.4 | 0.0 | 0.0 |
| R2 Hole Down / Up | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| R3 Hole Down / Up | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| R4 Ab/Eb Down | 0.0 | 0.0 | 0.0 |
| R4 Ab/Eb Up | 10.7 | 10.7 | 10.7 |
| R4 F/C Down | 5.8 | 4.7 | 4.7 |
| R4 F/C Up | 9.5 | 9.5 | 9.5 |

| | Before | After | Swing 25°, Thumb 45° |
|---|---:|---:|---:|
| Worst, all 32 poses | 16.5 (L1 G# Down) | 14.0 (R1 Eb/Bb Down) | 11.7 (R1 Eb/Bb Down) |
| Mean, all 32 poses | 7.8 | 3.2 | 1.8 |
| Left worst | 16.5 | 11.6 | 7.8 |
| Left poses ≤ 5 mm | 4 / 20 | 14 / 20 | 18 / 20 |

The requester measured a mean of 9.0 for the new baseline; I get 7.8 with breathing at 0 and the NLA
muted. The worst pose, 16.5 mm, matches.

Why the six left misses remain:
- **Pinky C#/G# and F#/C# (5.9 to 10.8 mm):** the root swing hits its 40° limit. A brute-force search
  with no solver reaches C#/G# Up within 0.1 mm and F#/C# Down within 3.4 mm at about 56–60° of side
  turn. That needs a swing of about 35°.
- **Thumb Register Up 11.6 and Hole Up 6.0 mm:** the thumb uses the full 30° turn, its root curl is at
  0 and a hinge at 0 or 120, so the thumb would need to lift. The brute-force search reaches them
  within 2.8 and 0.2 mm with a turn of 60° and about 47°.
- In the step-12 file, the misses I asked about were L1 G# Up (knuckle lift) and L4 E/B Up (out of
  reach). Both are 0.0 mm in the fixed file, so the knuckle lift isn't needed there. The thumb Up poses
  show the same pattern, curl at its limit, and could use it.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/rigs.py` | `ik_joint_settings(swing_deg, turn_deg)`, `locked_axes(turn_deg)`, `tube_axis`, `miss_advice`, defaults `KNUCKLE_SWING_DEG`, `THUMB_TURN_DEG` |
| `midi_animator/blender/props.py` | `knuckle_swing` (15°), `thumb_turn` (30°) |
| `midi_animator/blender/autoassign.py` | Swing on finger roots and turn on the thumb root; `_solve` returns the miss vector; per-pose `midianim_miss_mm` / `midianim_miss_advice`; one problem line per finger; `misses()`, `status_line()`, `report_lines()`, `tube_up()`; refreshes the view layer before reading markers |
| `midi_animator/blender/ops.py` | Autoassign reports every detail line to the Info log, then a short status line |
| `midi_animator/blender/ui.py` | Panel 2: Swing ° and Thumb ° fields; "N of M poses miss" line; "… mm off" next to each missing pose with wrapped advice |
| `tests/core/test_rigs_hud.py` | `test_knuckle_swing_and_thumb_turn`, `test_tube_axis`, `test_miss_advice` |
| `tests/test_in_blender.py` | `reach_checks` (index swing key, thumb turn key), miss-list checks, thumb twist allowed in `bend_checks` |
| `docs/decisions/0015-…md`, `0004-…md`, `README.md` | New ADR; superseded note marked |
| `docs/aerophone-guide.md`, `docs/SPEC.md`, `CLAUDE.md` | Swing/Thumb settings, where misses are listed, status |

## Verification
```
python -m pytest tests/core -q
80 passed in 0.27s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
reach L1 PalmF: knuckle_swing=0 misses by 16.1 mm (move the hand 15 mm down the tube, toward the bell (or the marker the other way)); knuckle_swing=15 reaches it within 0.00 mm
reach LT Octave: thumb_turn=0 misses by 3.8 mm (move the hand 4 mm down the tube, toward the bell (or the marker the other way)); thumb_turn=30 reaches it within 0.00 mm
miss list: 2 poses; 1 finger misses: see panel 2 (details in the Info log) | R Middle: 2 of 2 poses miss; worst E Up, 183 mm off: … / F.R2.E.Down: 171 mm off; … / F.R2.E.Up: 183 mm off; …
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```
On the user's file, Autoassign's own status and log were:
```
32 poses; 5 fingers miss: see panel 2 (details in the Info log)
L Thumb (register): 2 of 4 poses miss; worst Register Up, 12 mm off: move the hand 7 mm up the tube, toward the mouthpiece (or the marker the other way)
    F.LT.Hole.Up: 6 mm off; move the hand 5 mm up the tube, toward the mouthpiece (or the marker the other way)
L Index: 1 of 6 poses miss; worst G# Down, 4 mm off: the finger ends 4 mm short of the key: move the hand that far toward the keys
L Pinky: 4 of 6 poses miss; worst F#/C# Down, 11 mm off: move the hand 10 mm down the tube, toward the bell (or the marker the other way)
R Index: 2 of 4 poses miss; worst Eb/Bb Down, 14 mm off: move the hand 13 mm up the tube, toward the mouthpiece (or the marker the other way)
R Pinky: 3 of 4 poses miss; worst Ab/Eb Up, 11 mm off: the fingertip ends 10 mm too deep: move the hand 10 mm away from the keys
```
This run used the earlier wording for misses along the key's Z. The shipped wording is "the fingertip
ends 4 mm too far out: move the hand 4 mm toward the keys". Most per-pose lines are trimmed here.

## Deviations from the plan or spec
- The ≤ 5 mm target is met for 14 of 20 left poses, not all of them (see above). I kept the defaults
  the user chose (15°) and an anatomical 30° for the thumb, and recorded what larger settings give.
- The thumb's turn is about **its own length**, not literally about the tube axis. An IK limit is per
  local axis, and this plus the existing curl and spread lets the thumb pad turn round the tube.
- Tiny fix outside the step: Autoassign now calls `view_layer.update()` before reading the markers.
  A marker moved by a script was otherwise read at its old place for the first pose. The new e2e
  miss-list check exposed it.

## Decisions
- ADR 0015 (new): Knuckle Swing applies to **every** finger root, Thumb Turn to the thumb's base
  only, no knuckle lift. Reasons are in the ADR: one joint type, IK only uses it when needed, and
  middle and ring are unchanged on the user's file.
- Thumb Turn default **30°**, range 0–60°: a moderate share of the thumb base's natural roll in
  opposition. On the user's file it fixes both thumb Down poses; 45° would also fix Hole Up.
- Advice thresholds: a component of at least 60 % of the miss names its direction; otherwise "round
  the tube".

## Problems and risks
- The tube axis comes from the markers' principal axis. With markers for only one or two keys it can be
  wrong; the advice then names a wrong direction, but the distance is still right.
- The thumb e2e case has a thin margin: 3.8 mm without the turn, against the 3 mm threshold.
- R1 Eb/Bb Down (14.0) and R4's Up poses (10.7, 9.5) are right-hand misses outside this step's target.
  R4's Up poses are fully curled and can't lift; that is the same knuckle-lift question.

## Follow-ups for the planner
- Ask the user whether to raise the defaults to Swing 25° and Thumb 45°: left poses ≤ 5 mm go from
  14 to 18 of 20, mean 1.8 mm. Measured above.
- Decide "knuckle lift up to about 25°, Up poses only, as a setting". It would help the thumb's Up
  poses and R4's Up poses, which sit at a curl limit.
- 7d: the panel's advice lines are wrapped by hand at 38 characters; check them at the default sidebar width.

## Questions for the user
- Knuckle lift (asked through the requester, 2026-11-12): the answer so far is to keep bend-only and
  record it as a follow-up. The question is with the user.
