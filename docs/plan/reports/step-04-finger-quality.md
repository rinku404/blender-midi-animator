---
step: 4
title: "Finger quality: bend direction and an auto Rest pose"
status: done
branch: plan/step-04-finger-quality
pr: see PR description (into main)
commits: see PR
date: 2026-11-07
blender: 5.2.3 LTS, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 35 passed
tests_blender: ALL TESTS PASSED
decision_changes: none (dated notes added to ADR 0004 and ADR 0011; no new ADR)
---

# Step 4: Finger quality: bend direction and an auto Rest pose

## Summary
Autoassign now limits every finger joint's IK to a per-scene **Bend Axis** (X, -X, Z or -Z; default X, which is what
Rigify uses). Middle and end joints are hinges that only curl; the knuckle may also spread ±25°; **Keep Twist**
(on by default) locks Y. **Detect** (and Detect Fingers) reads the axis from the rest curl. The bones' own IK
settings are put back afterwards. Autoassign also builds **`F.Rest`** (each finger up over its home key, plus the
hand bones) and uses it as the Rest pose unless the user picked one. The breathing drift is gone: while the hold is
locked, the upper arms don't inherit scale, so the hand-to-target gap is 0.000 mm (it was 7.9 mm). One limit: the
limits use 0° (the rest pose) as the least curl, so a target that needs the knuckle to extend past rest isn't
reached. Autoassign now reports those misses. On Rigify's metarig with an unposed hand, about 9° of knuckle
extension would be needed (see Problems).

## Acceptance criteria
- [x] The new tests pass, and existing tests still pass: `35 passed` (3 new core tests); `test_in_blender.py` prints
      `ALL TESTS PASSED` with the new bend, Keep Twist, out-of-reach, auto Rest, manual Rest, Rest-in-bake,
      breathing-gap and inherit-scale-restore checks.
- [x] On the test rig, no joint bends against the bend axis (state the measured max): **0.000°** against the axis
      and **0.000°** on locked axes, over all 40 generated poses (Down and Up, 9 fingers). The max tip-to-target
      distance is 0.00 mm for Down and 2.28 mm for Up (both under the 4 mm limit). With Keep Twist off: 0.000° against
      and 0.001° side turn. For comparison, plain IK on the same rig bends 2.9° against the axis and 3.2° on
      locked axes (the test asserts plain IK fails the check, so the check proves something).
- [x] Hand-to-target gap while breathing < 1 mm (measured value in the report): **0.000 mm** (max over frames
      1–145, Chest effect at default `out_max` 0.04, chest scale up to 1.013). The sax world-scale error is still 0.00e+00.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/rigs.py` | `joint_curl`, `detect_bend_axis`, `ik_joint_settings`, `locked_axes` (pure math, no `bpy`) |
| `midi_animator/blender/autoassign.py` | bend-only IK limits during the solve (saved and restored), tip-miss report (> 3 mm), `build_rest` → `F.Rest`; `autoassign()` now returns a 4th item (Rest message) |
| `midi_animator/blender/rig.py` | `detect_bend_axis(s)` from the bones' rest matrices |
| `midi_animator/blender/hold.py` | Lock sets the arm IK root's `inherit_scale` to `NONE`, stores the original in `midianim_inherit_scale`; Unlock restores it |
| `midi_animator/blender/props.py` | `bend_axis`, `keep_twist` |
| `midi_animator/blender/ops.py` | `midianim.detect_bend_axis`; Detect Fingers also detects the axis; Autoassign reports the Rest result |
| `midi_animator/blender/ui.py` | Autoassign box: Bend Axis + Detect, Keep Twist, Overwrite Locked, an `F.Rest` hint |
| `tests/core/test_rigs_hud.py` | 3 tests: curl sign, axis detection (with measured Rigify numbers), IK settings |
| `tests/test_in_blender.py` | test fingers curl 8° per joint at rest (axis -X); markers within reach (keys side by side); new checks listed above |
| `tests/bend_rigify_probe.py` | new probe script (prints numbers, no pass/fail): Detect and Autoassign on Rigify's human metarig |
| `docs/aerophone-guide.md` | Bend Axis / Detect / Keep Twist, miss message, `F.Rest`, arms not scaled while locked, two troubleshooting lines |
| `docs/decisions/0004-*.md`, `0011-*.md` | dated "Note (plan step 4)" sections |
| `CLAUDE.md` | test count 35, `F.Rest` in conventions |

## Verification
```
python -m pytest tests/core -q
35 passed in 0.09s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
Info: Found all 9 fingers; Bend Axis -X
Info: 40 poses created; Rest pose: F.Rest
tip distance: down 0.0000, up 0.0099
bend: max against the axis 0.000 deg, max on locked axes 0.000 deg, max tip-to-target distance (Down and Up) 2.28 mm
plain IK for comparison: against 2.9 deg, locked axes 3.2 deg
keep twist off: against 0.000 deg, side turn 0.001 deg, tip 1.93 mm
Info: 40 poses created; F.Rest built, your Rest pose 'My Rest' is kept
tip distance with hold locked: 0.0000
max sax scale error 0.00e+00; chest scale up to 1.013; bone-parented probe 1.040
max hand-to-target gap while breathing: 0.000 mm
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/bend_rigify_probe.py
PROBE detected bend axis: ('X', [])
PROBE knuckle extension  0 deg: against 0.0 deg, locked 0.0 deg, tip off (Down, Up) mm {'LT': [4.7, 5.7], 'L1': [5.9, 9.8], 'L2': [5.8, 9.0], 'L3': [3.1, 0.6], 'L4': [0.0, 1.8], 'R1': [5.9, 9.8], 'R2': [5.8, 9.0], 'R3': [3.1, 0.6], 'R4': [0.0, 1.8]}
PROBE knuckle extension 10 deg: against 8.9 deg, locked 0.0 deg, tip off (Down, Up) mm {every finger [0.0, 0.0]}   (abbreviated)
PROBE knuckle extension 20 deg: against 8.9 deg, locked 0.0 deg, tip off (Down, Up) mm {every finger [0.0, 0.0]}   (abbreviated)
PROBE plain IK: against 16.9 deg, locked 5.3 deg, tip off (Down, Up) mm {every finger [0.0, 0.0]}   (abbreviated)
```
How the angles are measured (`tests/test_in_blender.py::joint_angles` / `bend_checks`): each joint's
`rotation_quaternion` is in bone space relative to rest. "Against" is the angle of the bone's direction around the
bend axis, on the uncurling side. For hinge joints, "locked" is Euler XYZ Y and Z (and the direction's sideways
component). For the knuckle it is the swing-twist twist around Y (the knuckle's side spread is allowed, so Euler Y
of a combined swing isn't a locked quantity).

## Deviations from the plan or spec
- **The knuckle is not fully locked to the bend axis:** the chain's root joint may spread sideways ±25° (limited, not
  locked). A real knuckle spreads, and side keys (pinky table, side keys) need it; the middle and end joints are pure
  hinges. Its twist is locked with Keep Twist.
- **Bend direction is limited too, not only the axes:** each joint may curl 0–120° from rest and no further back, which
  is what "never bends backwards" needs. That's why the setting is signed (X / -X / Z / -Z), like Rigify's own
  "bend rotation axis".
- **Keep Twist is on by default:** finger bones don't twist.
- **Detect Fingers also sets the Bend Axis** when the rest curl shows it. If the fingers are straight at rest, it
  keeps the current value and says so.
- **Added a tip-miss report** (> 3 mm, per finger, worst key) to Autoassign. Without it, a target that the limits
  make unreachable would fail without any message.
- **Test rig changed:** fingers now curl 8° per joint at rest (so Detect has something to read: −X), and the markers
  moved to where a curling finger reaches them, including the hover points (keys side by side, 3 mm apart sideways).
  The old layout put several keys back towards the palm, and reaching those needed the knuckle to lift against the
  axis. Plain IK did that by bending joints backwards.
- **Hand drift fix:** chose "arm bones don't inherit the chest's scale" (the plan's first example), applied to the IK
  chain root only, and only while locked.

## Decisions
- No new ADR: neither 0004 nor 0011 changes its decision. I added a dated note to each. 0004: IK limits during the
  solve, and `F.Rest`. 0011: the upper arm's Inherit Scale while locked, and that the 7.9 mm consequence is resolved.
- `F.Rest` contents: each finger's authored Up Pose, otherwise its Up pose over the first key in its slot (the home key,
  the same one bake uses), otherwise over any key that has one, otherwise the finger as posed now (reported). Plus
  the bones that carry the fingers (each chain's parent) and the hold's hand bones, as posed now. It uses the same
  fingerprint lock as other generated poses. If `s.rest_pose` is empty or already `F.Rest`, it is set to the new
  `F.Rest`. Any other Rest pose is left alone.
- Limits: 120° max curl per joint and ±25° knuckle spread (constants `MAX_BEND_DEG`, `ROOT_SPREAD_DEG` in `core/rigs.py`).

## Problems and risks
- **The knuckle can't extend past rest.** With the strict limits, a target that needs the knuckle to lift past its
  rest angle is missed. On Rigify's metarig with an *unposed* hand and markers 1.5 cm towards the palm and 1.5 cm back
  from each tip, Down misses up to 5.9 mm and Up up to 9.8 mm. Allowing the knuckle 10° of extension removes every
  miss, and the solver uses up to 8.9° (probe output above). Real knuckles hyperextend that much, but the plan's
  criterion says no joint against the axis, so I kept 0°. On a real rig whose hand is posed onto the instrument
  (fingers curled over the keys), targets should be within the curl range. Step 6 will tell. The miss report makes
  any case visible.
- **The legacy IK solver gives the same result whatever the starting pose** (I tried pre-curled seeds of 0–40°: same
  answer). Within the limits it sometimes curls mostly one joint (for example 62° on the end joint, 0° on the others)
  rather than spreading the curl the way real fingers do. That looks stiff, though not broken. Not addressed here.
- **Hand bones in `F.Rest`:** between phrases the Hand Poses strip now puts the hand bones back to their pose at
  Autoassign time. While the hold is locked, the IK and Copy Rotation override that. Without the hold, the user's own
  hand animation is replaced during long rests, which is what a manual Rest pose with hand bones did already.
- **Lock now changes rig data** (`Bone.inherit_scale` on each upper arm) until Unlock. If the user saves while locked,
  the setting is saved with the rig, and the original is kept in the bone's `midianim_inherit_scale` property. On
  Rigify the bone is `upper_arm_fk.*` (if Guess picks `hand_fk`). Not tried on a generated Rigify rig.
- **Rig-wide axis:** Bend Axis is one setting per scene. On rigs whose thumb rolls differently from the fingers (some
  Mixamo or VRoid exports), the thumb may need another axis. Detect lists fingers that curl another way, but the
  setting can't be per finger yet.

## Follow-ups for the planner
- Add to step 6: run Autoassign on the real rig and record every "fingertip … mm off" message. If misses come from
  the knuckle needing to extend, allow the knuckle about 10° of extension (one constant in `core/rigs.ik_joint_settings`,
  root only; measured on the Rigify metarig to remove all misses).
- Add to step 6: check the thumb's curl on the real rig. If Detect lists it as curling another way, add a per-finger
  Bend Axis override.
- Consider (polish): IK stiffness or a curl ratio so Autoassign spreads curl across the joints instead of bending mostly one.
- Add to step 6: try Lock/Unlock on a generated Rigify rig with `hand_fk` and confirm `upper_arm_fk`'s Inherit Scale
  doesn't fight Rigify's own setup.

## Questions for the user
None.
