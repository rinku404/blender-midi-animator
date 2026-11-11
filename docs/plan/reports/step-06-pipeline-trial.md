---
step: 06
title: Pipeline trial on CJ + clarinet
status: partial          # in progress: the checklist walk is not finished
branch: plan/step-06-trial
pr: pending
commits: pending
date: 2026-11-10
blender: Blender 5.2.3 LTS (C:\Program Files\Blender Foundation\Blender 5.2\blender.exe)
tests_core: pending
tests_blender: pending
decision_changes: none
---

# Step 6: Pipeline trial on CJ + clarinet (report in progress)

Walk-through log lives in `docs/plan/notes/trial-checklist.md`. This file is filled in as the trial proceeds.

## Plugin issues
| # | Area | What happened | Expected | Severity | Suggested fix |
|---|---|---|---|---|---|
| (none recorded yet) | | | | | |

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

## Pending
Checklist sections A–G, plugin issues table, severities with the user, verification commands, PR.
