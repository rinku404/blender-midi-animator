---
step: 06
title: Pipeline trial on CJ + clarinet
status: done
branch: plan/step-06-trial
pr: "#10 (merged), closing PR: plan/step-06-close"
commits: bd535de..7b2b9ec
date: 2026-11-10
blender: Blender 5.2.3 LTS (C:\Program Files\Blender Foundation\Blender 5.2\blender.exe)
tests_core: 39 passed (python -m pytest tests/core, 2026-11-11)
tests_blender: ALL TESTS PASSED (tests/test_in_blender.py, -b --factory-startup); extension validate OK
decision_changes: none
---

# Step 6: Pipeline trial on CJ + clarinet

Walk-through log lives in `docs/plan/notes/trial-checklist.md`.

## Summary
The pipeline runs end to end on CJ + clarinet: Analyze, Fit Scene Range, Add Audio, Detect Fingers, Hold (guess, Lock,
Unlock), the Chest blow effect on the real CC2, Bake, HUD export (PNG + ProRes 4444) and Make Composite Scene under AgX.
Getting there took two test-setup fixes to CJ: rebuilt hands (S5), and arm bone tails moved onto the joints (S8)
because **Lock threw the hands 39 cm off** on the rig as imported (P1).
The user judged the breathing **unrealistic** (E2). Today's Lung mode breathes once in the take and is empty for the
last 31 s (P8), and the Chest preset swells the whole upper body, head included (P3). A breathing prototype built with
the user (below) is the proposed fix for step 7.
Nine plugin issues are recorded; the user confirmed the severities on 2026-11-12: P1, P3, P8 *bad*, the rest *polish*.
F1 (viewport HUD preview) is ok; F3 (Resolve) is skipped because the user edits in Blender; F4 (Make Composite Scene
under AgX) passed in the user's own UI run.

## Plugin issues
Severities confirmed by the user on 2026-11-12 (G1).

| # | Area | What happened | Expected | Severity | Suggested fix |
|---|---|---|---|---|---|
| P1 | Hold / Lock | On rigs whose bone tails don't sit on the next joint (CJ's FBX import: forearm tail 39 cm from the wrist), **Lock moves the hands 389.7 mm** off the instrument and holds them there. The forearm IK targets the forearm's tail. | Hands stay where they were posed (0 mm) | bad | Lock compares the forearm tail with the hand head. If they are apart, it offers to move the arm bones' tails onto the next joint (what S8 did by script), or at least warns before locking. |
| P8 | Blow / Lung mode | Lung mode only inhales when the blow drops under 2 %. On this take that happens once (9.6 s); from 24.5 s the lungs stay empty for 31 s and the chest freezes. Breaths also always refill to full. | The player breathes at phrase gaps, as much as the next phrase needs, and never runs dry | bad | A breath planner (the user's idea): find breath points (note gaps, blow dips), inhale where the air left won't last to the next point, sized to the coming phrase and limited by the gap length, eased in and out; a prep breath before the first note; slow, small tidal breathing in long rests. Pairs with P3 (drive the chest/shoulders, not the lowest spine). **User feedback on the prototype (2026-11-11):** a fixed maximum, refilled quickly at *every* break (rule `every_break` in `scripts\breath_planner.py`: 8 breaths, lung fitted at 7 s); a stronger default swell (0.04 felt imperceptible; trying 0.10); and a torso tilt with the breath (trying `spine middle_012` ROT_Y, −1° empty to +2° full). Comparison copies: `midi_trial_breath_test.blend` / `_current.blend`. Then the user asked for **the whole body to breathe, with intensity control**. Prototype (`scripts\breath_body.py`): the plugin bakes one breath signal (a Property effect in Lung mode on `["breath_lung"]`); drivers move ribcage depth/width, belly, shoulder lift and a torso lean from it. Each part has a slider (`breath_chest`, `breath_belly`, `breath_shoulders`, `breath_torso`) plus a master `breath_intensity`, all live without a re-bake. Hands stay locked (0.0 mm); head and arm scale stay at 1.000. Proposed shape for step 7: a "Breathing" section in the Blow panel with these sliders. |
| P9 | Analyze / Add Audio | **Add Audio** adds a new strip on every click. The file already had a `MIDI Audio` strip with the two-track mix (`zelda_recorded_v1.wav`), so after A4 both strips played and track B was heard twice. | One MIDI audio strip, replaced when the file changes | polish | Replace (or update) the existing `MIDI Audio` strip instead of adding another; report "Replaced". |
| P2 | Hold / Guess Bones | Hands not found when the rig names them `wrist` (CJ: `arm left wrist_041`); strap guessed as the lowest spine bone `spine lower_011`. | Wrist bones found; strap on the upper chest | polish | Add `wrist` to the hand keywords; prefer the highest `spine` bone in the chain for the strap. |
| P3 | Blow / Chest preset | The Chest preset's "spine" fallback picks `spine lower_011`, so the whole upper body, head included, swells by up to 4 %. | Chest bone only | bad | Prefer the Strap bone if set, else the highest `spine` bone. Also: **Scale X+Z** assumes Rigify axes (Y along the bone). On CJ the spine's local X is *up*, so it stretched the torso's height and depth, not width and depth. Pick the axes from the bone's world orientation (front-back and side-side), and set the chest bone's children (neck, shoulders) to not inherit scale, so the head and arms don't grow. Tried in `midi_trial_breath_test.blend`: `spine upper_013` Scale Z 0.10 (depth) + Scale Y 0.04 (width); head and arm scale stay at 1.000. |
| P4 | Analyze / Transpose | After changing Transpose, the HUD updates but the text summary (written range, unmapped notes) stays stale until Analyze is clicked again. | Summary follows Transpose | polish | Re-run the summary on the Transpose update, or show "re-analyze" in the panel. |
| P5 | UI | At the default sidebar width many labels and summary lines are cut off (`Instrum…`, `Charact…`, `Ho… 0.012 m`, `written D3–…`, `Unmapped notes…`). | Readable at default width | polish | Explicit label splits / two-line summaries, as already done for the Hold box. |
| P6 | UI text | "1 tracks". | "1 track" | polish | Plural only for ≠ 1. |
| P7 | Guide | The user asked how to pose the arms for the hold, which object to pick as Instrument (the import has `Clarinet`, an in-between empty and the meshes), and pressed Autoassign before any markers existed (0 poses + warning). | The guide answers these before the user hits them | polish | Guide §3: arm posing for the hold, "pick the instrument's top object", and "Autoassign needs key markers". |

## Test-setup limits
Things caused by the assets or the test file, not by the plugin.

| # | Area | What | Effect on the trial |
|---|---|---|---|
| S1 | Rig | CJ's original hands have 2 three-joint fingers each and no clear thumb (`arm left finger 1a_045`-style bones). | Detect Fingers finds nothing on the original rig (names have no thumb/index/… words); see step 11. |
| S2 | Face | The head mesh has no shape keys, so no `CheekPuff`. | Cheeks preset can't run until a key is sculpted (checklist D2). |
| S3 | Scale | The clarinet glTF is 64 units long; scaled to 0.0103 (≈0.66 m) and placed in front of the chest. | Needs positioning at the lips for the Hold step. |
| S4 | Scene | A stray `Icosphere` (2 units) arrives with the imports. | Left in place. |
| S5 | **Setup change (2026-11-10): CJ's hands rebuilt with real fingers** | See the section below. Done by script on `midi_trial.blend`; the file as the user left it is kept as `midi_trial_before_fingers.blend`, the pass-2 result as `midi_trial_pass2.blend`. | Detect Fingers now fills all 9 slots. On the original two-finger rig it found nothing (`{}`, script run of the core detector); step 11 still matters for rigs like the original. |
| S6 | Mesh | Body mesh `Object_6` is not exactly symmetric: the right half equals the mirror of the left plus (0.0712, -0.0047, -0.1032) in mesh units. | New right-hand geometry and right bones use the same offset so they sit on the right hand. |
| S7 | File | `midi_trial.blend` was saved with `Object_6` in Edit Mode, and contains no test cube (the user's cube was not saved). | Script switched the object to Object Mode before editing. Nothing to delete. |
| S8 | **Setup change (2026-11-11): arm bone tails** | CJ's imported arm bones end beside the limb, not on the next joint (the forearm tail is 39 cm from the wrist), which breaks Lock (P1). `scripts\fix_arm_tails.py` moves the tails of `arm * shoulder 2` and `arm * elbow` onto the next joint (roll kept), then the hold pose is re-applied by `scripts\pose_arms.py`. The mesh is unchanged. Backups: `midi_trial_c1_before.blend` (the clarinet at the lips, T-pose) and `midi_trial_c1_oldrig.blend` (the arms posed on the original bones). | Lock and breathing pass (C4–C6, D3). |
| S9 | Hold pose | The user placed the clarinet at the lips; the arms were posed by script at the user's request (C1). | C1 timing not representative. |
| S10 | Scene | `midi_trial.blend` has no camera. | The user added one for F4. |
| S11 | Scene | `midi_trial.blend` has no World and no lights (the viewport's Material Preview hides that). A render is black. | The user added a World and a sun for F4; the stray Icosphere hid CJ's legs in renders. |

### S5: hand rebuild (setup change)
Backup: `D:\3D\blender_projects\midi_trial\midi_trial_before_fingers.blend` (the file exactly as given).
Rebuilt by script in background Blender 5.2.3 (no Blender MCP was connected), always starting from the backup, so
the result is reproducible. The scripts and the final parameters are kept in `D:\3D\blender_projects\midi_trial\scripts\`
(`build.py`, `verify.py`, `rh.py`, `sheet.py`, `detect.py`, `final_params.json`; the pass-2 versions in `scripts\pass2\`).
Everything is in the one body mesh `Object_6`. Passes 1 and 2 below describe the earlier build; pass 3 replaces its fingers and thumb.

**Pass 1 (fingers, bones, weights):**
- **Measured (left, mesh units; 1 unit = 0.0254 m):** wrist bone x = 29.170, knuckle rim x = 32.555 (back of hand 3.385),
  rim width y −2.182..0.677 (2.858), finger thickness 0.715 (a quarter of the rim width).
- **Fingers:** 4 per hand, 8 vertices per ring, 3 segments (4 rings + closed ends = 32 vertices each). Lengths from the
  rim: index 3.216 (95 %), middle 3.385 (100 %), ring 3.216 (95 %), pinky 2.539 (75 %). Tip ring tapers to 80 %. Rest curl
  8° per joint toward the palm (−Z). Material index 0 (`body_upper`), UVs set to a skin sample of the hand (u,v = 0.335, 0.308).
  The body's own custom normals are kept.
- **Right hand:** 81 faces deleted (no left twin by position, after the S6 offset), the new geometry mirrored with the same
  offset, normals recalculated. Two left triangles at the palm base have no right twin (different triangulation there); both kept.
- **Thumb:** the existing prong was split by weights, not rebuilt: vertices weighted to the old `1a/1b/1c` bones (≥ 0.5,
  |x| ≥ 29.5) were assigned to `thumb.01/02/03` by projection onto the new bones (L 5/9/13 vertices, R 6/9/13). The thumb
  bones follow the old `1a/1b/1c` heads, the last tail at the prong's tip.
- **Bones:** `f_<finger>.01..03.<L|R>` and `thumb.01..03.<L|R>`, parented to `arm left wrist_041` / `arm right wrist_051`,
  `.02` and `.03` connected. Roll puts the curl on local X (left fingers X = +Y, right fingers X = −Y; thumb X along the
  thumb's own rest-bend axis). Old finger bones kept, with no weights.
- **Weights:** each new vertex in exactly one group at 1.0; old finger groups emptied; 42 leftover rim/seam vertices that
  still carried old finger weights went to the wrist bone.

**Pass 2 (polish, user request after looking at the pass-1 sheets):**
- **Palm closed:** the hand is two open skin sheets (back and palm) that meet at the sides but not at the knuckles. The
  opening between the back's rim edge (7 vertices) and the palm's lower edge (6) is now capped with 9 flat triangles per hand,
  from the pinky corner to the thumb base, using the existing rim vertices (no new vertices). They are wrist-weighted except
  the two at the thumb base, which stay with `thumb.02/.03` so the cap doesn't tear when the thumb moves. The side views
  show a closed knuckle wall instead of the hollow.
- **Pivot inside the hand (user chose option 1):** bone `.01` now starts 15 % of the finger length inside the hand and ends
  where it did; `.02`/`.03` unchanged. Only 5 % of the finger length of skin stays behind the pivot (user follow-up), so
  nothing behind the joint swings up through the back of the hand.
- **Flat shading** on the new fingers (and the cap), to match CJ's low-poly look. The body keeps its original shading.
- **Small fit adjustments** to keep the pinky inside the back of the hand (at rest it touched the slanted pinky side of
  the hand): finger row moved 0.1 toward the thumb, spacing 95 % of the thickness, pinky 85 % thick (0.607) and 0.05 lower.
  Final centres (left): index y −1.871, middle −1.192, ring −0.513, pinky 0.166.

Pass-2 checks (superseded): no finger crossed the back of the hand at 0–90°; curled fingers crossed the palm flap
(30°: 4–6 faces each); the thumb curled around the wrong axis. Pass-2 sheets are in `screenshots\pass2\`.

**Pass 3 (user review of the pass-2 hand):** the fingers came out from under a ledge (tops 0.4 below the back of the hand),
read as round pencils, the thumb was still CJ's flat paddle, and the thumb end of the cap looked dark.
- **Skin sheets welded:** the hand's back, palm and thumb sheets met at coincident but separate vertices; 48 were merged
  (both hands), so the openings are clean loops. Two 6-vertex slits at the wrist seam (vertices 0.07 apart, not
  coincident) are in the original and stay.
- **Fingers:** flat octagon tubes (flats, not corners, on top and sides), 0.765 wide × 0.60 tall (pinky 0.64 × 0.50),
  overlapping 3 % at the base, filling y −2.38..0.40. Each knuckle ring sits 0.03 under the knuckle edge of the back of the
  hand at its own y, and rolls with the edge's sideways slope (index −7°, ring +8°, pinky +17°), so the tops continue
  the back of the hand. Rest angle 4°, then 9° per joint. Rings: behind the pivot (70 % size, so it stays inside when it
  swings up), knuckle, middle joint (92 %), end joint (86 %), bevelled tip. Lengths, segment split, the pivot 15 % inside
  and the 5 % of skin behind it are as in pass 2.
- **Sloped knuckle row:** the palm's front edge (4 vertices per hand) moved up 0.37–0.64 and back 0.16–0.38, to 0.12
  under the finger undersides, so the wall under the fingers slopes into them instead of standing ~1.0 tall. This
  changes CJ's palm shape; `palm_lift: 0` in `final_params.json` keeps the palm as it was.
- **Thumb:** the paddle is cut 0.5 past the old `1b` joint along its axis (18 faces and 8 vertices per hand), the
  4-vertex stump hole is capped, and a 3-segment tube is added: 0.88 × 0.75, base joint at the stump, length 2.55 split
  55 / 45 %, tip where the paddle's tip was, last segment tilted 10° toward the palm. Bones `thumb.01` (old `1a` head to
  the stump), `.02`, `.03`, rolled so +X curls the tip toward the palm. The stump moves with `thumb.01` (7 vertices L,
  8 R); one palm-centre vertex that the old thumb bone carried goes to the wrist.
- **Caps:** the knuckle cap (9 triangles) and the stump cap (2) take the winding of the faces around them; all of them
  face outward (knuckle: dot with +X ≥ 0.31; stump: dot with the thumb axis 0.82).
- **Shading:** original faces keep their custom normals, the moved palm faces included; the new faces are flat.

**Checks (pass 3, `verify.py` → `scripts\verify.json`; L and R give the same numbers):**
- Weights: 479 finger/thumb vertices, each in exactly one group at 1.0; 0 unweighted vertices in the hand; old finger groups empty.
- Winding: 1,034 hand edges shared by two faces, 0 run the same way by both (caps, stump, tubes and the original skin).
- Per-bone test: each of the 30 new bones rotated 30° alone moves only its own segment and the later ones (0 unexpected).
- Curl direction at 30°: every finger tip moves down (dot 0.74 with −Z), both thumb tips toward the palm (0.99). The
  pass-2 thumb's wrong axis is fixed.
- Skin test, every joint at once: at rest nothing crosses anything except where a tube goes into the knuckle or stump
  cap. No finger crosses the **back** of the hand at 0°, 30°, 60° or 90°. Palm side, faces crossed: 30° index 10,
  middle 6, ring 4, pinky 4, thumb 0; 60° index 13, middle 14, ring 12, pinky 10, thumb 16. Neighbouring fingers touch at
  the base (the 3 % overlap).
- With `thumb.01` (the thumb's base joint) at 60°, a thin fold shows on the back of the hand near the thumb: the stump
  skin folds. It does not show at 30°, nor when only `.02`/`.03` curl. A real thumb base flexes ~15–20°; noted for step 12.
- Detect Fingers (plugin, headless): "Found all 9 fingers; Bend Axis X"; slots LT, L1–L4, R1–R4 filled with the new
  bones; Detect (Bend Axis) also X, no finger on another axis.
- Pass-3 sheets are in `screenshots\pass3\`, the file in `midi_trial_pass3.blend`, the scripts in `scripts\pass3\`.

**Pass 4 (user review: "a huge gap between where the first of the four fingers should be placed and where it really is"):**
pass 3 put the four fingers on the pinky-side 2.78 of the 3.9-wide knuckle edge, leaving ~0.9 bare at the thumb side.
Two agents (Claude Opus and Antigravity/Gemini) each made a variant in `variants\`; the user left the choice to us and
the Claude variant is installed (finger tops closer to the edge, no fingers touching at rest, fewer crossings at 30°).
- **Finger row** y −3.21..0.49 (3.69 wide, was 2.78): the index's outer side is at the thumb-side corner. Fingers
  0.94 × 0.73 (pinky 0.79 × 0.62), was 0.75 × 0.58; a small gap between them (`spacing` 1.03). Lengths unchanged.
- **Roll sign bug fixed:** pass 3 rolled each knuckle ring against the slope of the knuckle edge (`-atan`); it is now
  `+atan(slope) × 0.9`, so the fingers fan along the knuckle arch. Finger tops sit 0.03–0.06 under the edge (pass 3:
  up to 0.33 at the pinky). Rolls: index 28°, middle 5°, ring −12°, pinky −33°, back to 0 by the end joint.
- **Thumb** unchanged (`thumb_w` 0.858 is now absolute, so it no longer grows with the finger width).
- **Texture bug fixed:** every new face maps to one skin texel. Passes 1–3 used the average of the hand's UVs, which
  falls between texture islands on **black** (0, 0, 0), so the new fingers would have rendered black in Material
  Preview. Now it is the hand UV whose colour is closest to the hand's average: new faces (0.27, 0.18, 0.13) vs original
  hand skin (0.27, 0.16, 0.12). All five images are packed in the .blend.

**Checks (pass 4; L and R the same):** weights 0 bad / 0 unweighted; winding 0 inconsistent of 1,034 edges; per-bone
test 0 unexpected; curl direction 0.74–0.75 (fingers), 0.98 (thumbs); rest: nothing crossed except the caps, no fingers
touching; back of the hand never crossed at 0–90°. Palm side at 30°: index 2, middle 7, ring 4, pinky 4, thumb 4; at 60°:
3 / 14 / 12 / 10 / 16. Detect Fingers: "Found all 9 fingers; Bend Axis X", 9 slots, no other-axis fingers.
Still off, for step 12: the index sits ~0.43 lower and ~0.2 further back than the middle finger because CJ's knuckle
edge curves back and down at the thumb-side corner (seen by the user from above); the thumb runs under the palm,
parallel to the fingers; in a 60° fist the knuckle cap shows as a sawtooth between the wider fingers.
- Pass-4 sheets are in `screenshots\pass4\`, the file in `midi_trial_pass4.blend`, the scripts in `scripts\pass4\`.

**Pass 5 (user decision: straight knuckle line, thumb off the side of the hand at ~35°):** made by one agent
(Antigravity, Gemini 4 Argon) in `variants\antigravity`, checked and installed.
- **Thumb-side corner reshaped** (CJ's mesh, approved): the corner of the knuckle edge moves (+0.37, 0, +0.63) to
  (32.45, −3.248, 58.38), level with the middle knuckles; the back-of-hand vertex behind it moves (0, −0.26, +0.49) so
  the index root stays inside; one thenar-edge vertex moves (−0.17, +0.27, −0.09). The thumb web vertex stays, so the
  hand's side slopes from the index knuckle down to the web.
- **Index level with the middle finger:** knuckle X 32.459 vs 32.477, top Z 58.359 vs 58.395, roll 0.9° (was 28°);
  `top_gap_max` ≤ 0.055 for all four.
- **Thumb rebuilt from the side of the hand:** the whole old paddle on the thumb side is removed (21 faces, 9 vertices
  per hand), the 5-vertex hole on the side of the hand is capped (3 triangles), and a tube 0.95 × 0.78 (not narrower than
  the index, 0.94) runs from the base joint (30.55, −3.38, 56.15) at 35° outward from +X and 10° down, length 2.40
  (1.30 + 1.10), tip (32.58, −4.58, 55.79), well below the knuckle line. Bone `thumb.01` starts at (29.80, −2.70, 56.40).

**Checks (pass 5, rebuilt and re-run here; L and R the same):** weights 0 bad / 0 unweighted; winding 0 inconsistent of
1,028 edges; per-bone test 0 unexpected; curl direction 0.74–0.75 (fingers), 0.98 (thumbs); rest: nothing crossed but
the caps, nothing touching (the thumb included); back of the hand never crossed at 0–90°. Palm side at 30°: index 4,
middle 8, ring 4, pinky 4, thumb 0 (pass 4: 2 / 7 / 4 / 4 / 4); 60°: 2 / 13 / 9 / 10 / 21 (pass 4: 3 / 14 / 12 / 10 / 16).
Texture: new faces (0.27, 0.18, 0.13) vs hand (0.27, 0.16, 0.12). Detect Fingers: "Found all 9 fingers; Bend Axis X",
9 slots, no other-axis fingers. Still off: the side-of-hand cap where the thumb leaves is a flat light facet in the front
views; the knuckle cap still shows as a sawtooth in a 60° fist.
- Screenshots: `D:\3D\blender_projects\midi_trial\screenshots\` `sheet_rest.png`, `sheet_curl30.png`, `sheet_curl60.png`
  (front, top, side and 3/4 of both hands), `sheet_textured.png` (top and 3/4 with the skin texture),
  `user_view_pass4_vs_pass5.png` (the user's view), plus the single views.

## Acceptance criteria
- [x] The checklist is fully walked or each skipped line has a reason. A1–C1 in the UI with the user; C2–F2 and F4 run
  headlessly with the plugin's operators at the user's request; B4 answered by the hand rebuild; key markers, Autoassign
  and fingering skipped (step 12). E2 judged by the user (it led to P8), F1 ok in the UI, F4 run by the user in the UI,
  F3 skipped (the user edits video in Blender, so the external-editor path isn't theirs).
- [x] Both tables are filled in, and the user confirmed the severities: P1–P9 (P1, P3, P8 *bad*; the rest *polish*),
  S1–S11.

## Verification
| Check | Result |
|---|---|
| `python -m pytest tests/core` | 39 passed |
| `blender -b --factory-startup --python tests/test_in_blender.py` | ALL TESTS PASSED (the "bone 'nope'" error line is one of its deliberate failure checks) |
| `blender --command extension validate midi_animator` | OK; built `midi_animator-1.0.0.zip` and installed it with Install from Disk for the UI part |
| Trial scripts | `D:\3D\blender_projects\midi_trial\scripts\`: `trial_c_to_f.py` (+ `.json`, `.log`), `fix_arm_tails.py`, `pose_arms.py`, `f4_composite.py`, `breath_planner.py`, `bake_breath_test.py`, `breath_body.py` |

No plugin code changed in this step; the branch holds the checklist and this report.

## Breathing prototype (input for step 7, P3 + P8)
Built with the user after E2. Chart: Traycer artifact "Breath Planner Prototype". Files: `midi_trial_breath_test.blend`
(planned breathing, whole upper body) and `midi_trial_breath_current.blend` (today's Lung mode, chest on the lowest spine
bone, for reference).
- **Breath signal:** the user's rule `every_break`. At every breath point (note gaps ≥ 0.10 s and blow dips inside
  legato, merged), inhale quickly toward a fixed maximum, at 3 lungs per second, eased. The lung size is fitted per
  take so it never falls under a 15 % reserve between breaks (7 s of full blow for this take). On this take: 8 breaths;
  today's Lung mode breathes once and is empty for the last 31 s. The earlier `sized` rule (breathe only where needed, as
  much as the next phrase needs) is kept in the script.
- **Body:** one baked signal (`["breath_lung"]`, a Property effect in Lung mode) drives, through drivers, ribcage depth
  10 % and width 4 %, belly 6 %, a 3° shoulder lift, and a torso lean of +2° / −1° (half that on the lower back). The
  neck, shoulders and middle spine don't inherit the swell. Sliders on the rig: `breath_intensity` (master),
  `breath_chest`, `breath_belly`, `breath_shoulders`, `breath_torso`, all live without a re-bake.
- **Measured:** hands on the clarinet 0.0 mm, head and upper-arm scale 1.000 at every checked frame, master 0 / 1 / 2
  gives still / default / double.
- **Open:** quick breaths in 0.15–0.2 s gaps last only 4 frames (Blender can drop them in Sync to Audio playback). The
  idea: start breaths up to 0.15 s before the gap, at least 0.3 s long. The user parked it.

## Deviations from the plan
- The plan has the user doing every line in the UI. From C2 on, the agent ran the lines headlessly with the plugin's own
  operators, at the user's request; the UI findings stop at C1.
- Two test-setup changes to CJ: the hands (S5) and the arm bone tails (S8). Both are reproducible from the scripts, with
  backups.

## Follow-ups for the planner
- **Step 7:** P1 (Lock on rigs with off-joint bone tails), P8 + P3 (breathing: the planner, a whole-body breathing
  section with sliders, rig-aware scale axes), P9 (Add Audio stacking strips), P2, P4, P5, P6, P7.
- **Step 11:** Detect Fingers finds nothing on CJ's original `finger 1a_045`-style bones (S1).
- **Step 12:** key markers, Autoassign, fingering judgement, thumb bend axis, and the hand-mesh limits listed under S5.

## Questions for the user
None open. The user's answers: severities as proposed; F1 ok; F3 not used (edits in Blender); F4 ok.
