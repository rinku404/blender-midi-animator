---
step: 7c
title: Finger reach (P12, P11, P13)
status: partial
branch: plan/step-07c-finger-reach
pr: 17 (draft)
commits: 8cace65..HEAD
date: 2026-11-12
blender: 5.2.3, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 81 passed
tests_blender: ALL TESTS PASSED
decision_changes: ADR 0015 added (supersedes the joint-limit and miss-report part of ADR 0004's step-4 note)
---

# Step 7c: Finger reach

> **ADR 0015** supersedes part of ADR 0004's note. A finger knuckle may swing along the instrument,
> and in Up poses only it may lift (bend backwards). The thumb's base may turn about its own length.

## Summary
Autoassign has three new limited freedoms, all scene settings in panel 2. Their defaults are the
user's choices:
- **Knuckle Swing** (default **25°**, 0–45°) adds to every finger root's sideways spread, which runs
  along the tube.
- **Knuckle Lift** (default **25°**, 0–25°) lets every finger's and the thumb's root bend backwards,
  in **Up (hover) poses only**. Down poses keep the bend-only rule.
- **Thumb Turn** (default **45°**, 0–60°) lets the thumb's base turn about its own length. It is the
  only twist Keep Twist allows.

Middle and end joints still only curl.

Each pose that misses its key now stores the miss and an advice. Panel 2 lists it under the finger's
poses, the Info log gets one line per finger and one per missing pose, and the status bar stays short.
The advice says which way and how far to move the hand: up or down the tube, toward or away from the
keys, or round the tube.

On the user's file (fixed hold, 2026-11-12), **19 of the 20 left-hand poses are now within 5 mm**, up
from 4. The mean over all 32 poses is 1.5 mm, down from 7.8, and the worst is 11.7 mm (right index
Eb/Bb Down), down from 16.5. The one left pose still off is **L4 F#/C# Down at 7.2 mm**: the pinky's
knuckle sits at its 50° side limit. That is why the status is **partial**.

## Acceptance criteria
- [x] **Index roll (P12):** the knuckle swings along the instrument, as the Knuckle Swing setting.
  Evidence: L1 A Down 16.3 → 0.0 mm and L1 G# Down 16.5 → 0.0 mm. In the e2e test, a key 38° to the
  side misses by 16.9 mm at swing 0 and is reached within 0.00 mm at 25°.
- [x] **Thumb turn (P12):** the thumb's base turns about its length within ±Thumb Turn. Evidence:
  every LT pose is ≤ 0.1 mm; they were 5.2 to 15.3. The turn used goes up to 35° (Register Up). In the
  e2e test, a key needing a 28° turn misses by 3.8 mm at 0° and is reached within 0.00 mm at 45°.
- [x] **Knuckle lift (added at the user's request):** the root bends backwards by up to Knuckle Lift
  in Up poses only. Evidence: at 15° swing and 30° turn, LT Hole Up 6.0 → 0.1 mm and LT Register Up
  11.6 → 0.1 mm. No Down pose bends backwards at either set of defaults.
  - In the e2e test, an Up target needing a 20° lift misses by 15.6 mm at 0° and is reached within
    0.00 mm at 25°. Its root bends backwards in Up and 0.0° in Down.
  - `bend_checks` keeps the strict no-backwards rule for every Down pose: 0.000°.
- [x] **Keep Twist honoured:** with Keep Twist on, `bend_checks` gives 0.000° against the axis and on
  locked axes for every pose. The thumb's base twist is checked against Thumb Turn, and Up-pose root
  lift against Knuckle Lift.
- [x] **Readable misses (P11):** each missing pose shows "… mm off" and its advice in panel 2. The
  Info log gets one line per finger plus one per pose, and the status bar reads
  "32 poses; 3 fingers miss: see panel 2 (details in the Info log)". The e2e test checks the
  per-finger line, `misses()` per slot, the log lines and the status line.
- [x] **Advice (P13):** `core.rigs.miss_advice` splits the miss along the tube, found from the
  markers' principal axis and signed by slot order, and along the marker's Z. Covered by pytest
  `test_miss_advice` and `test_tube_axis`. On the user's file it says, for example,
  "L Pinky: 1 of 6 poses miss; worst F#/C# Down, 7 mm off: move the hand 6 mm down the tube, toward
  the bell (or the marker the other way)".
- [x] **Locked poses keep their behaviour:** nothing in the lock path changed. The e2e lock test passes,
  and a skipped locked pose keeps its old miss props.
- [ ] **Every left-hand pose ≤ 5 mm on the user's file:** 19 of 20. L4 F#/C# Down is 7.2 mm.
- [x] **Middle and ring not worse:** L2, L3, R2 and R3 are all 0.0 mm after; before, L2 Hole Down was
  7.1 and L3 Hole Down 8.6.

## Measurement on the user's file
I re-copied `midi_trial.blend` after the hold fix (`fix_hold3.py`) and measured a scratch copy. NLA
tracks were muted, `breath_intensity` set to 0, frame 1, and Autoassign ran with Overwrite Locked. The
script applies each generated pose and measures the tail of the chain's last bone against the marker
(Down) or the marker plus hover times its Z (Up). Script: `measure.py` in the session scratchpad,
the same idea as `tune_left.py`'s `errors()`. Markers and hand were not moved.

The columns are the stages of this PR. The last column is the shipped defaults: swing 25°, turn 45°,
lift 25°. Values are in mm.

| Pose | Before | 15°/30°, no lift | 15°/30°, lift 25° | **25°/45°, lift 25° (shipped)** |
|---|---:|---:|---:|---:|
| LT Hole Down | 5.3 | 0.0 | 0.0 | 0.0 |
| LT Hole Up | 10.5 | 6.0 | 0.1 | 0.1 |
| LT Register Down | 5.2 | 1.2 | 1.2 | 0.1 |
| LT Register Up | 15.3 | 11.6 | 0.1 | 0.0 |
| L1 A Down | 16.3 | 2.3 | 2.3 | 0.0 |
| L1 A Up | 5.5 | 0.0 | 0.0 | 0.0 |
| L1 G# Down | 16.5 | 3.7 | 3.7 | 0.0 |
| L1 G# Up | 5.6 | 0.0 | 0.0 | 0.0 |
| L1 Hole Down | 3.3 | 0.0 | 0.0 | 0.0 |
| L1 Hole Up | 0.0 | 0.0 | 0.0 | 0.0 |
| L2 Hole Down | 7.1 | 0.0 | 0.0 | 0.0 |
| L2 Hole Up | 0.0 | 0.0 | 0.0 | 0.0 |
| L3 Hole Down | 8.6 | 0.0 | 0.0 | 0.0 |
| L3 Hole Up | 0.0 | 0.0 | 0.0 | 0.0 |
| L4 C#/G# Down | 12.8 | 5.9 | 5.9 | 0.0 |
| L4 C#/G# Up | 15.6 | 7.4 | 7.4 | 0.0 |
| L4 E/B Down | 14.2 | 0.0 | 0.0 | 0.0 |
| L4 E/B Up | 8.8 | 0.0 | 0.0 | 0.0 |
| L4 F#/C# Down | 15.5 | 10.8 | 10.8 | **7.2** |
| L4 F#/C# Up | 14.4 | 6.9 | 6.9 | 1.6 |
| R1 Eb/Bb Down | 16.4 | 14.0 | 14.0 | 11.7 |
| R1 Eb/Bb Up | 11.0 | 6.1 | 6.1 | 2.6 |
| R1 Hole Down | 11.4 | 1.2 | 1.2 | 0.0 |
| R1 Hole Up | 3.4 | 0.0 | 0.0 | 0.0 |
| R2 Hole Down / Up | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| R3 Hole Down / Up | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 | 0.0 / 0.0 |
| R4 Ab/Eb Down | 0.0 | 0.0 | 0.0 | 0.0 |
| R4 Ab/Eb Up | 10.7 | 10.7 | 10.7 | 10.7 |
| R4 F/C Down | 5.8 | 4.7 | 4.7 | 4.7 |
| R4 F/C Up | 9.5 | 9.5 | 7.8 | 7.8 |

| | Before | 15°/30°, no lift | 15°/30°, lift | **Shipped** |
|---|---:|---:|---:|---:|
| Worst, all 32 poses | 16.5 (L1 G# Down) | 14.0 (R1 Eb/Bb Down) | 14.0 (R1 Eb/Bb Down) | **11.7 (R1 Eb/Bb Down)** |
| Mean, all 32 poses | 7.8 | 3.2 | 2.6 | **1.5** |
| Left worst | 16.5 | 11.6 (LT Register Up) | 10.8 (L4 F#/C# Down) | **7.2 (L4 F#/C# Down)** |
| Left poses ≤ 5 mm | 4 / 20 | 14 / 20 | 16 / 20 | **19 / 20** |

The requester measured the same at the shipped defaults: 19 of 20, mean 1.5 mm, worst 11.7 mm. They
measured the baseline mean as 9.0; I get 7.8 with breathing at 0 and the NLA muted. The worst pose,
16.5 mm, matches.

Why poses still miss at the shipped defaults:
- **L4 F#/C# Down (7.2 mm), the last left pose over 5 mm:** the pinky's knuckle turns sideways to
  its full 50° limit, the 25° spread plus the 25° swing. Its middle and end joints are at 77° and 64°,
  short of their limits. The key lies further down the tube than the pinky reaches; the advice says
  "move the hand 6 mm down the tube, toward the bell".
  - A brute-force search with no solver reaches 3.4 mm at 60° of side turn, which is a swing of 35°.
  - Fixing it needs a bigger swing, up to the setting's 45° maximum, or the hand or marker moved.
    The user chose 25°.
- **R4 Up poses (10.7 and 7.8 mm):** both hinges are fully curled at 120°, and the hover point is still
  too close to the knuckle. A brute-force search with the lift agrees: 10.7 and 7.8 mm is the best
  possible. Only moving the hand fixes them, which the advice says ("move the hand 10 mm away from the keys").
- **R1 Eb/Bb Down (11.7 mm):** outside this step's left-hand target. The advice says "move the hand
  10 mm up the tube".

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/rigs.py` | `ik_joint_settings(swing_deg, turn_deg, lift_deg)`, `locked_axes(turn_deg)`, `tube_axis`, `miss_advice`, defaults `KNUCKLE_SWING_DEG` 25, `THUMB_TURN_DEG` 45, `KNUCKLE_LIFT_DEG` 25 |
| `midi_animator/blender/props.py` | `knuckle_swing` (25°, 0–45°), `knuckle_lift` (25°, 0–25°), `thumb_turn` (45°, 0–60°) |
| `midi_animator/blender/autoassign.py` | Swing on finger roots and turn on the thumb root; lift on every root, set per pose (Up only); `_solve` returns the miss vector; per-pose `midianim_miss_mm` / `midianim_miss_advice`; one problem line per finger; `misses()`, `status_line()`, `report_lines()`, `tube_up()`; refreshes the view layer before reading markers |
| `midi_animator/blender/ops.py` | Autoassign reports every detail line to the Info log, then a short status line |
| `midi_animator/blender/ui.py` | Panel 2: Swing ° and Lift ° on one row, Thumb Turn ° below; "N of M poses miss" line; "… mm off" next to each missing pose with wrapped advice |
| `tests/core/test_rigs_hud.py` | `test_knuckle_swing_and_thumb_turn`, `test_knuckle_lift`, `test_tube_axis`, `test_miss_advice` |
| `tests/test_in_blender.py` | `reach_checks` (swing key, thumb turn key, lift-only Up target with the Down pose checked), miss-list checks; `bend_checks` allows the thumb's base twist within Thumb Turn and Up-pose root lift within Knuckle Lift, and stays strict for Down |
| `docs/decisions/0015-…md`, `0004-…md`, `README.md` | New ADR; superseded note marked |
| `docs/aerophone-guide.md`, `docs/SPEC.md`, `CLAUDE.md` | The three settings, their defaults and where they are; where misses are listed; status |

## Verification
At the shipped defaults:
```
python -m pytest tests/core -q
81 passed in 0.27s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
bend: max against the axis 0.000 deg, max on locked axes 0.000 deg, max tip-to-target distance (Down and Up) 0.00 mm
keep twist off: against 0.000 deg, side turn 1.160 deg, tip 0.00 mm
reach L1 PalmF: knuckle_swing=0 misses by 16.9 mm (move the hand 15 mm down the tube, toward the bell (or the marker the other way)); knuckle_swing=25 reaches it within 0.00 mm
reach LT Octave: thumb_turn=0 misses by 3.8 mm (move the hand 4 mm down the tube, toward the bell (or the marker the other way)); thumb_turn=45 reaches it within 0.00 mm
lift L2 A: root bend Up 17.4 deg (backwards is +), Down 0.0 deg
reach L2 A: knuckle_lift=0 misses by 15.6 mm (the fingertip ends 15 mm too deep: move the hand 15 mm away from the keys); knuckle_lift=25 reaches it within 0.00 mm
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```
On the user's file, Autoassign's own status and log at the shipped defaults (per-pose lines trimmed):
```
32 poses; 3 fingers miss: see panel 2 (details in the Info log)
L Pinky: 1 of 6 poses miss; worst F#/C# Down, 7 mm off: move the hand 6 mm down the tube, toward the bell (or the marker the other way)
R Index: 1 of 4 poses miss; worst Eb/Bb Down, 12 mm off: move the hand 10 mm up the tube, toward the mouthpiece (or the marker the other way)
R Pinky: 3 of 4 poses miss; worst Ab/Eb Up, 11 mm off: the fingertip ends 10 mm too deep: move the hand 10 mm away from the keys
```

## Deviations from the plan or spec
- The ≤ 5 mm target is met for 19 of 20 left poses, not all of them (see above).
- The defaults changed twice during the step, both by the user through the requester. The Knuckle
  Lift was added, with range 0–25° and default 25°. Then Swing went 15° → 25° and Thumb Turn 30° → 45°,
  after the user compared renders.
- ADR 0015 records the lift as the one exception to "fingers never bend backwards": root only, Up poses only.
- The thumb turns about **its own length**, not literally about the tube axis. An IK limit is per local
  axis, and this plus the existing curl and spread lets the thumb pad turn round the tube.
- Tiny fix outside the step: Autoassign now calls `view_layer.update()` before reading the markers.
  A marker moved by a script was otherwise read at its old place for the first pose. The new e2e
  miss-list check exposed it.
- With Keep Twist **off**, the e2e hinge side-turn tolerance went from 1.0° to 1.5°. The solver now
  leaves 1.16° on a hinge, where before it left 0.001°, because the lift gives it more room. With Keep
  Twist on, the default, it is still 0.000°.

## Decisions
- ADR 0015 (new): Knuckle Swing applies to **every** finger root, and Thumb Turn to the thumb's base
  only. Knuckle Lift applies to every root including the thumb, in Up poses only. The reasons are in
  the ADR.
- All three defaults are the user's: swing 25°, turn 45°, lift 25°. I proposed 15° (the user's
  starting value) and 30°.
- Advice thresholds: a component of at least 60 % of the miss names its direction; otherwise "round
  the tube".

## Problems and risks
- The tube axis comes from the markers' principal axis. With markers for only one or two keys it can be
  wrong; the advice then names a wrong direction, but the distance is still right.
- The thumb e2e case has a thin margin: 3.8 mm without the turn, against the 3 mm threshold.
- Autoassign now writes all of a chain's IK limits once per pose instead of once per chain.
  This costs a few attribute writes per pose.

## Follow-ups for the planner
- The last left miss, L4 F#/C# Down at 7.2 mm, needs about 35° of swing, or the hand or marker moved
  about 6 mm down the tube. Let the user decide when they review the render.
- The right pinky's Up poses are fully curled and can't hover 12 mm higher. Consider a per-finger
  hover height, or a hand-position helper (the step-12 follow-up "fit the hand to the markers").
- 7d: the panel's advice lines are wrapped by hand at 38 characters; check them at the default sidebar width.

## Questions for the user
- Knuckle lift (asked through the requester, 2026-11-12): **yes**, range 0–25°, default 25°, Up poses
  only, thumb and every finger. Done.
- Defaults (asked through the requester, 2026-11-12, after renders at 15°/30° and 25°/45°):
  **swing 25°, thumb turn 45°**. Done.
