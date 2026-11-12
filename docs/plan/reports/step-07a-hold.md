---
step: 07a
title: "Hold works on any rig, facing the right way"
status: done
branch: plan/step-07a-hold
pr: <filled in by the closing commit>
commits: 3c305f4..<closing commit>
date: 2026-11-12
blender: Blender 5.2.3 LTS (C:\Program Files\Blender Foundation\Blender 5.2\blender.exe)
tests_core: 65 passed (python -m pytest tests/core -q)
tests_blender: ALL TESTS PASSED (tests/test_in_blender.py, -b --factory-startup); extension validate OK
decision_changes: none
---

# Step 7a: Hold works on any rig, facing the right way

Scope: `docs/plan/notes/step-07-scope.md`, package 7a (P1, P10, P2, the hold part of P7). PLAN.md has no step 7 yet;
the scope note is committed with this branch.

## Summary
Lock now works on CJ's FBX rig as imported: before building the IK it finds arm bones whose tail sits off the next joint
and moves those tails onto the joints, keeping the pose and the skin exactly (the deformation `pose · rest⁻¹` of every
bone is preserved, so the bones turn to lie along the limb and nothing else changes). On
`midi_trial_c1_oldrig.blend` the hands now move **0.001 mm** on Lock (was 389.7 mm) and the mesh 0.001 mm.
The Hold box has a **Front (keys)** setting, one of the instrument's own axes, filled by **From View** (look straight
at the keys, click) or **From Markers**; a status line says whether the front faces forward, sideways or the player;
**Turn Front Forward** rolls the instrument about its length until the keys face away from the player; and **Lock
refuses** while the front faces the player. **Guess Bones** finds hands named `wrist` and picks the upper chest (the
spine bone the arms and neck hang from) as the strap. The guide has a click-by-click **Set up the hold** section with a
real player's posture. One limitation stays: the tail fix doesn't convert animation already keyed on the fixed bones.

## Acceptance criteria
From the scope note, package 7a.
- [x] **P1: Lock works on a rig whose arm tails are off the joints.** `tests/test_in_blender.py`
  `offjoint_and_front_checks` builds a CJ-style rig (forearm tail 39 cm off the wrist, posed arms, a skinned strip of
  points): `Lock moved the hands and elbows 0.0006 mm, the skin 0.0004 mm`; a second Lock has nothing to fix.
  Real case, `midi_trial_c1_oldrig.blend` (copy, headless): off-joint before `arm left/right elbow_040` 389.7 mm,
  `arm left/right shoulder 2_039` 398.7 mm; after Lock `hand_jump_mm {"L": 0.001, "R": 0.0}`,
  `elbow_move_mm {"L": 0.0, "R": 0.0}`, `mesh_max_move_mm 0.001` (every vertex of `Object_6`), tails now 0.0 mm from the
  joints, `hands_vs_targets_mm {"L": 0.001, "R": 0.0}`, re-lock 0.0 mm.
- [x] **P10: the instrument's front can be set and is checked before Lock.** `hold_front` + From View / From Markers /
  Turn Front Forward / status line (`ui.py`), `check()` refuses "faces the player". e2e: front toward the player →
  `Lock … should fail` passes with "faces the player"; `turned 180.0 deg, now 0.00 deg from forward`; the tube's centre
  line moved < 0.1 mm; a child marker turned with it; From Markers reads the axis back. On `midi_trial.blend` (16
  markers): From Markers → `-Y`, 29° from the mean arrow, status `forward (30°)`, `check() == ""`; a front view gives
  `-Y`, a back view `+Y` → `player (150°)`.
- [x] **P2: Guess Bones finds `wrist` hands and the upper chest.** `tests/core/test_rigs_hud.py::
  test_guess_hold_bones_cj_wrists_and_upper_chest`; on both trial files Guess gives
  `("spine upper_013", "arm left wrist_041", "arm right wrist_051")`.
- [x] **P7 (hold part): guide.** `docs/aerophone-guide.md` → *Set up the hold*: posture (20–25° lean, keys forward,
  left hand upper joint, right hand lower joint, thumbs behind), which object is the Instrument (the import's top
  object), placing it, Front, posing the arms bone by bone with the keys to press, Guess Bones, the arm-bone notice,
  Lock. Two new Troubleshooting lines.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/hold.py` | New, pure: axis names and vectors, nearest axis, facing verdict (forward ≤ 60°, sideways ≤ 90°, player beyond), roll angle about an axis, player forward from the rig's −Y, tail tolerance (2 mm or 2 % of the bone), mean direction |
| `midi_animator/core/rigs.py` | Guess: `wrist` counts as a hand; among equally ranked spine bones the one with a side-named / neck child wins, then the highest in the chain |
| `midi_animator/blender/hold.py` | `off_joint_bones`, `fix_arm_tails` (Edit Mode tail move with roll kept, pose restored parents-first, constraints muted meanwhile), front: `front_world`, `player_forward`, `front_status`, `set_front_from_view/markers`, `instrument_axis` (vertex PCA), `turn_front_forward` (changes `matrix_basis` only, so parenting and the strap Child Of survive), `is_locked`; `check()` refuses a front facing the player and a hidden rig that needs fixing; `lock_hands` fixes first and reports the bones moved |
| `midi_animator/blender/props.py` | `hold_front` enum (Not Set, ±X ±Y ±Z) |
| `midi_animator/blender/ops.py` | Operators `hold_front_from_view`, `hold_front_from_markers`, `hold_turn_front` |
| `midi_animator/blender/ui.py` | Hold box: Front row, From View / From Markers, status line with Turn Front Forward, "N arm bones end off the joint … Lock fixes them" |
| `tests/core/test_hold.py`, `tests/core/test_rigs_hud.py` | 6 new tests + the CJ guess test; the old CJ assertion now expects the wrists |
| `tests/test_in_blender.py` | `build_cj_scene`, `offjoint_and_front_checks` |
| `docs/aerophone-guide.md` | *Set up the hold* section, shorter item 2, troubleshooting |
| `docs/plan/notes/step-07-scope.md` | Committed (was untracked) |
| `CLAUDE.md` | Status line |

## Verification
```
python -m pytest tests/core -q
65 passed in 0.14s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
Error: Right hand bone 'nope' not found on Rig: pick it or press Guess        (deliberate failure check)
clarinet checks passed
two-finger checks passed
Error: The instrument's front faces the player (180° from forward): click Turn Front Forward, or set Front to Not Set
front: turned 180.0 deg, now 0.00 deg from forward (forward)
off-joint rig: Lock moved the hands and elbows 0.0006 mm, the skin 0.0004 mm
off-joint rig and front checks passed
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --factory-startup --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```
Trial files (copies in the agent's scratch folder, `--factory-startup`, the repo's plugin registered by script;
the originals were not written):
- `midi_trial_c1_oldrig.blend` → `hand_jump_mm {"L": 0.001, "R": 0.0}`, `mesh_max_move_mm 0.001`, 4 tails fixed
  (389.7 / 398.7 mm), re-lock 0.0 mm. With Front `-Y` the step-6 hold reads `player (115°)`; Turn Front Forward rolls
  it 161° and the status is then `sideways (64°)` because that hold's tube points forward (the step-6 hold was almost
  horizontal), which the operator's message now says: tilt it down, then turn again.
- `midi_trial.blend` → From Markers `-Y` (29° off), `forward (30°)`; turning while locked is refused.

## Deviations from the plan or spec
- Scope came from `docs/plan/notes/step-07-scope.md` instead of PLAN.md (no step 7 there yet), as instructed.
- `CLAUDE.md`'s status line was updated (test count, step 7a); PLAN.md untouched.

## Decisions
- **P1 runs automatically on Lock, reported.** Reasons: Lock's promise is "nothing moves", and P1 is exactly the case
  where a beginner can't know a button is needed; the fix is exact (mesh and pose measured unchanged at the µm level)
  and reversible with one Ctrl+Z (Lock is an undo step); the panel announces it beforehand ("N arm bones end off the
  joint (up to 39 cm); Lock fixes them") and the status bar lists the bones moved afterwards. A button would add a step
  that only matters on FBX-style rigs and would leave the bad lock reachable. Tolerance: 2 mm or 2 % of the bone.
- **P10 mechanism: a Front axis on the instrument, set from the view or the markers, plus a one-click roll.** A roll
  slider alone gives no check (nothing says which way is right); markers alone don't exist yet when the hold is built
  (the step 12 order). An axis is stable (it rides with the object), cheap to check before every Lock and needs no
  understanding of local axes from the user: *From View* turns "look at the keys and click" into the axis. The
  player's forward is the rig object's −Y when that is horizontal, else the world's −Y (the Front view), documented in
  the guide. Thresholds: forward ≤ 60° (a sax hangs to the right), player > 90°; Lock blocks only "player", the panel
  flags "sideways". *Turn Front Forward* finds the tube by vertex PCA of the instrument's meshes and refuses while locked.
- Only the two IK-chain bones per arm are fixed (forearm and upper arm). CJ's collarbone tail is also off (20 cm) but
  the IK never aims it; leaving it alone keeps the change minimal.

## Problems and risks
- **Keyed arm animation isn't converted.** After the tail fix, an action that keys the fixed bones (an imported walk
  cycle) plays differently, because the basis now sits in a turned rest frame. Convertible by conjugating each key
  with `rest_old⁻¹ · rest_new` (a constant rotation per bone), not done here. Noted in the guide.
- `From View` needs a 3D View (`space_data.region_3d`); the button is greyed elsewhere.
- `Turn Front Forward` measures the long axis from mesh vertices (subsampled to ~4 000 per mesh); an instrument that is
  only empties can't be turned (clear error). Rolling keeps the axis line, so a mouthpiece slightly off the axis moves by
  that offset.
- The front check is skipped when Front is *Not Set*; a user who never sets it gets today's behaviour.

## Follow-ups for the planner
- Convert actions keyed on the fixed arm bones when Lock moves their tails (conjugate the keys), or offer it as a step.
- Collect the "set up the hold" renders (front/side of a correct hold) as pictures for the guide; text only for now.
- Consider setting Front automatically when the first key markers are placed (From Markers), so the check is on by default.
- 7d: the Hold box is getting tall; group Front and the arm-bone notice in a sub-box when the panel is tidied (P5).

## Questions for the user
None. Open choices were decided above (P1 automatic, P10 axis + From View/Markers + Turn).
