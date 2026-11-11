---
step: 11
title: "Hands with fewer fingers (shared finger bones)"
status: done
branch: plan/step-11-shared-fingers
pr: "#12"
commits: c88e774..6a92721 (plus this report fix)
date: 2026-11-11
blender: 5.2.3 LTS, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 58 passed
tests_blender: ALL TESTS PASSED
decision_changes: ADR 0013 added (refines 0003 and 0004; supersedes nothing)
---

# Step 11: Hands with fewer fingers (shared finger bones)

## Summary
A finger slot can now **share** another slot's bone chain (`FingerBones.shares`), and **Detect Fingers** reads
numbered finger names (`arm left finger 1a_045`: side from *left*/*right*, finger from the digit, joints from the
hierarchy). On CJ's original two-finger rig it proposes exactly the user's mapping: finger 1 = index, finger 2 =
middle + ring + pinky, and the left thumb as the **hand bone's Press Tilt** (3° around the Bend Axis towards the keys,
editable per finger). Autoassign solves a shared chain onto every sharing slot's own markers (pose names stay per slot
and key), Bake merges the slots of one chain with **pressing wins** (the slot listed first has priority), F.Rest takes
each chain once, and a slot with no bones is skipped silently and listed once by Analyze as *Not animated*. The tilt
works with **Lock on**: the hand's rotation is copied from `MIDI Hold L`, so Bake keys the tilt on that target too
(measured 3.000° around the hand's X, wrist 0.000 mm off its target). Everything is verified by 9 new core tests and a
new e2e section that builds its own two-finger hand; the real CJ file was checked read-only (proposal below).

## The user's answers (plan questions)
1. **Slot mapping on CJ:** finger 1 = index (L1/R1); finger 2 = middle + ring + pinky (L2–L4 / R2–R4). The left thumb
   slot **LT = the hand bone's own slight tilt** (chosen over "not animated"). Implemented as above; the default angle
   is 3°, per-finger editable (`Press Tilt`), sign follows the Bend Axis, justified under *Decisions*.
2. **Disagreeing slots on one chain:** **pressing wins**, and the chain goes to the marker of the **highest-priority
   pressing slot, the slot listed first**. Implemented in `core/fingering.merge_shared`.

## Acceptance criteria
- [x] pytest covers the combining rule; the e2e test builds a 2-finger hand, shares slots, autoassigns and bakes:
      `tests/core/test_fingering.py` has 5 `merge_*` tests (pass-through, agreeing slots, pressing wins over lifting,
      a higher-priority slot keeps the chain when another presses a different key mid-note, Rest/override unanimous);
      `tests/core/test_rigs_hud.py` has 4 new tests (CJ's names, the 2-finger proposal, 3/4/5 numbered fingers and a
      named hand missing one finger, `tilt_rotation`). `python -m pytest tests/core -q` → `58 passed`.
      `tests/test_in_blender.py::two_finger_checks` builds a hand with `arm left finger 1a_044`-style bones, runs
      Detect Fingers (shares + tilt proposed, Bend Axis -X), both sync paths, markers, Autoassign (tip on L3's key
      0.00 mm with L2's bones), Analyze, Bake (G4 remapped to L1+L3: the chain is at `F.L3.G.Down`; A4: `F.L2.A.Down`;
      D5: the hand tilted; C#5: back), then Lock + Bake (tilt on the target) → `two-finger checks passed`,
      `ALL TESTS PASSED`.
- [x] The user's answers are in the report: section above.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/rigs.py` | `_finger` reads numbered fingers (`#n`); `_numbered_to_named` (≥5: 1 = thumb; fewer: 1 = index, no thumb; named fingers win per side); `assign_slots` → `SlotAssignment(chains, shares, tilt_hands)`; `tilt_rotation`; `THUMB_TILT_DEG = 3`; `FINGER_ORDER`. `chains_for_slots` unchanged for callers. |
| `midi_animator/core/fingering.py` | `merge_shared(keys, groups)` → `{owner: [(frame, slot, state)]}`: pressing wins, first listed wins, hovers over the key left last; keeps the chosen slot's own keys and a key on both sides of a switch so transitions keep their timing. |
| `midi_animator/blender/props.py` | `FingerBones.shares` (hidden string), `shares_ui` (dynamic enum view of it: "Own bones" + slots with their own bones), `tilt` (degrees). |
| `midi_animator/blender/rig.py` | `sync_finger_slots` saves `shares` and `tilt` on rebuild; `detect_fingers` applies the assignment (found → bones; missing → shares; thumb → hand bone + default tilt, keeping a user-set tilt) and returns `(missing, assignment)`; `share_owner`, `finger_bones` (sharing slots resolve to the owner's chain), `share_groups`, `tilt_slots`; `detect_bend_axis` counts a shared chain once. |
| `midi_animator/blender/actions.py` | `rotation_channels(owner, base_path, tilt)` for a pose bone or an object, optionally turned around its own axis (Euler and Quaternion; Axis Angle refused with a message). |
| `midi_animator/blender/autoassign.py` | No-bones slots skipped silently; tilt slots get `_tilt_poses` (Down = bone turned, Up = as posed, rotation only, no markers, lock-aware); `build_rest` takes each chain once; `_hand_bones` doesn't add a tilt slot's parent (the forearm). |
| `midi_animator/blender/bake.py` | Timelines merged per chain; the bake loop runs on `(frame, slot, state)`; `tilt_targets` + `_bake_tilt_on_target` key the hold target's rotation while Lock is on (`MIDI_Tilt L` action, `MIDI: Fingering` track on the target; cleared on re-bake and by Clear); `bake_fingering` returns warnings as a 4th item. |
| `midi_animator/blender/hold.py` | `rotation_target(arm, bone)`: the hold target whose rotation the bone copies, if locked. |
| `midi_animator/blender/ops.py` | Detect Fingers reports the sharing and tilt proposal; Analyze: "Not animated (no bones): …" once, and tilt slots need no markers. |
| `midi_animator/blender/ui.py` | Finger list rows show `→ L Middle` / `tilt 3°`; the finger box has **Shares Bones With**, hides the bone picker when sharing, and **Press Tilt (°)** otherwise. |
| `tests/core/test_fingering.py`, `tests/core/test_rigs_hud.py` | 9 new tests (see acceptance). |
| `tests/test_in_blender.py` | `build_scene(fingers, bone_name)`; `place_markers` skips tilt slots and offsets sharing slots' keys; `two_finger_checks()`. |
| `docs/decisions/0013-shared-finger-slots.md`, `docs/decisions/README.md` | New ADR. |
| `docs/aerophone-guide.md` | Numbered names in step 3.1; new **Hands with fewer fingers** section; two troubleshooting lines. |
| `docs/SPEC.md`, `README.md`, `CLAUDE.md` | Shared slots and tilt mentioned; status 58 tests, 2026-11-11. |

## Verification
```
python -m pytest tests/core -q
58 passed in 0.18s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
bend: max against the axis 0.000 deg, max on locked axes 0.000 deg, max tip-to-target distance (Down and Up) 2.28 mm
clarinet bend: against 0.000 deg, locked axes 0.024 deg, tip 0.40 mm
clarinet checks passed
Info: Found 4 fingers; L Middle also plays L Ring, L Pinky; R Middle also plays R Ring, R Pinky; L Thumb (octave) = tilt of hand.L (3°); Bend Axis -X
Info: 42 poses created; Rest pose: F.Rest
shared chain tip distance: on L3's key 0.00 mm, on L2's key 0.00 mm
locked thumb tilt: 3.000 deg around (-1.0, 0.0, 0.0), hand moved 0.000 mm
two-finger checks passed
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```
The sax and clarinet numbers are unchanged from step 10.

**Real-rig check (read-only):** `midi_trial_before_fingers.blend` copied to my scratch folder, opened with `-b`, the
extension registered, `Object_3` set as the rig, Detect Fingers run for both profiles (nothing saved):
```
Info: Found 4 fingers; L Middle also plays L Ring, L Pinky; R Middle also plays R Ring, R Pinky;
      L Thumb (octave) = tilt of arm left wrist_041 (3°); fingers straight at rest, Bend Axis kept at X
CHAINS L1 = arm left finger 1a_045, 1b_046, 1c_047; L2 = arm left finger 2a_042, 2b_043, 2c_044 (R1/R2 likewise)
SHARES {'L3': 'L2', 'L4': 'L2', 'R3': 'R2', 'R4': 'R2'}   TILT {'LT': 'arm left wrist_041'}   missing: []
```
Same result with the clarinet profile (label "L Thumb (register)"). CJ's fingers are straight at rest, so the Bend
Axis stays at the current value; the finger bones' local X is the sideways axis at rest (probe), so X or -X is the
likely answer in step 12 (check in Pose Mode as the guide says).

## Deviations from the plan or spec
- **Sharing is proposed whenever a finger is missing on a side that has any finger**, not only below four: a named
  rig that lacks (or hides the name of) one finger now gets "L Ring → L Middle" instead of "Not found". The status
  bar says so, and the dropdown undoes it. The two-finger result is the plan's.
- **Numbered fingers:** five or more → 1 is the thumb; fewer → 1 is the index and there is no thumb. A four-finger
  cartoon hand numbered 1–4 (thumb + three) would therefore come out as index…pinky; documented in the guide, fixable
  in the dropdown. The plan didn't define this case.
- **The thumb tilt is a new per-finger field** (`tilt`, degrees), not a special case of "no bones": the slot's bones
  are the hand bone. Analyze and Autoassign treat a tilt slot as needing no markers.
- `autoassign()` no longer reports "no bones" as a problem (plan task 4: skip silently; Analyze lists it).
- `bake_fingering` returns a fourth item (warnings) and `rig.detect_fingers` returns a pair; both callers updated.

## Decisions
- **ADR 0013** (new, refines 0003/0004): sharing, pressing wins, numbered names, the thumb tilt, no-bones slots.
- **Tilt: 3°, around the Bend Axis, towards the keys.** Reason: the fingers are children of the hand, so any hand
  rotation moves the fingertips by angle × distance (about 4 mm at 3° for an 8 cm finger). Turning towards the keys
  sinks Down fingers slightly into their keys (hidden) and lowers hovering ones from 12 to about 8 mm; turning the
  other way or around another axis would lift fingers off their keys or slide them along the instrument. 3° is visible
  as a squeeze without reading as a wrist motion; the user can set any angle (negative flips it, 0 makes it a normal
  IK slot again). Default in `core/rigs.THUMB_TILT_DEG`.
- **Lock on:** no constraint setting layers a local tilt after Copy Rotation (the *Before/After* mix modes compose
  with the bone's world rotation, which includes the IK-driven forearm), so Bake keys the tilt on `MIDI Hold L`'s
  rotation (its local axes equal the hand's at lock time). The hand bone is keyed too, so Unlock keeps the motion.
  Measured: 3.000° around the hand's own X, wrist 0.000 mm off the target, re-bake replaces the track, Clear removes it.
- **While no slot presses, a shared chain hovers over the key it left last** (the slot that pressed last), consistent
  with ADR 0003's "a lifted finger hovers over the last key it pressed". When one slot lifts (lift lead) while
  another presses the same chain at the next onset, the chain lifts and then drops on the new key; when the pressing
  slot's hold key comes first, it moves key to key directly.
- Priority = the finger list order (profile order), not the owner of the bones.

## Problems and risks
- **Fingertips move with the tilt:** by design (see above), but on a rig with long fingers or a bigger tilt the Down
  fingers push through the keys. Step 12 should look at it on CJ with the clarinet held; lower the angle if it shows.
- **Hand X vs finger X:** the tilt sign follows the Bend Axis, read from the fingers. On CJ the wrist bone's local X is
  not the fingers' X (probe: wrist X ≈ (0.86, −0.39, −0.33), finger 1a X ≈ (0.65, −0.69, −0.30) in armature space,
  close but not equal), so the tilt may need its sign flipped or may not be exactly "towards the keys". The guide says
  to negate the angle. A per-finger tilt axis would be the fix if it matters.
- **A tilt slot bakes the hand bone's rotation** into `MIDI: Fingering` (Replace). Without Lock, that overrides the
  user's own hand rotation during the whole take (location and scale are left alone). Same class of effect as F.Rest's
  hand bones (step 4), now for the whole take. With Lock on it is harmless (the constraint wins).
- **Three thumb keys on the clarinet** (`Hole`, `Register`, `RegOnly`) all get the same tilt, so B♭4 and the clarion
  notes look alike on CJ; on a thumbless hand that is unavoidable.
- `shares_ui` is a dynamic enum over `fingers`; the stored value is the string `shares`, so saved files don't depend on
  item order. Blender's dynamic-enum string lifetime caveat is handled with a module-level list.
- Step 6's P1 (forearm tails off the wrist on CJ's FBX import) is untouched; it affects Lock, not this step.

## Follow-ups for the planner
- Add to step 12: run Detect Fingers on CJ (expect the proposal above), pick the Bend Axis by hand (fingers straight at
  rest), check the tilt direction on the wrist bone and flip the sign if needed, and judge 3° by eye.
- Add to step 7 (if step 12 asks): a per-finger tilt axis, or read the sign from the hand bone instead of the fingers.
- Add to step 7: Analyze warns when a note-map row uses a slot that shares a chain with another pressed slot of the same
  row (the second press is silently dropped; the chart never does this, hand edits can).
- Consider: the tilt slot's hand-bone channels could use an "Add" strip instead of Replace, so the user's hand
  animation survives without Lock.
- Step 6's P2 (`wrist` not a hand keyword for Guess Bones) still stands; the tilt proposal finds the wrist through the
  finger chain's parent, so it doesn't depend on it.

## Questions for the user
Both plan questions were answered before the step (see *The user's answers*). None added.
