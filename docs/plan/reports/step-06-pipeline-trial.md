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
| S5 | **Setup change (2026-11-10): CJ's hands rebuilt with real fingers** | See the section below. Done by script on `midi_trial.blend`; the file as the user left it is kept as `midi_trial_before_fingers.blend`. | Detect Fingers now fills all 9 slots. On the original two-finger rig it found nothing (`{}`, script run of the core detector); step 11 still matters for rigs like the original. |
| S6 | Mesh | Body mesh `Object_6` is not exactly symmetric: the right half equals the mirror of the left plus (0.0712, -0.0047, -0.1032) in mesh units. | New right-hand geometry and right bones use the same offset so they sit on the right hand. |
| S7 | File | `midi_trial.blend` was saved with `Object_6` in Edit Mode, and contains no test cube (the user's cube was not saved). | Script switched the object to Object Mode before editing. Nothing to delete. |

### S5: hand rebuild (setup change)
Backup: `D:\3D\blender_projects\midi_trial\midi_trial_before_fingers.blend` (the file exactly as given).
Rebuilt by script in background Blender 5.2.3 (no Blender MCP was connected), always starting from the backup, so
the result is reproducible. The scripts and the final parameters are kept in `D:\3D\blender_projects\midi_trial\scripts\`
(`build.py`, `verify.py`, `rh.py`, `detect.py`, `final_params.json`). Everything is in the one body mesh `Object_6`.

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

**Checks (pass 2, `verify.py`):**
- Weights: 311 finger/thumb vertices, each in exactly one group at 1.0; 0 unweighted vertices in the hand region; old finger groups empty.
- Per-bone test: each of the 30 new bones rotated 30° alone: only its own segment and the later ones moved (0 unexpected).
- Full curl, every finger and thumb joint at 0°, 30°, 60° (and 90°): no finger surface crosses the **back** of the hand at
  any of them (measured with face-overlap tests between each finger and the hand skin). The fingers do cross the **palm
  sheet** when curled (30°: 4–6 faces per finger; 60°: 7–12), because the palm sheet sticks out ~0.4 past the knuckle wall
  and the curled fingers bend down through that flap. At 60° the middle finger leaves the knuckle wall entirely and comes
  out of the palm underside instead. The cap is closed, so no hole shows; it reads as a fist. Fine for clarinet playing
  (curls well under 60°), noted for step 12.
- Detect Fingers (plugin, headless): "Found all 9 fingers; Bend Axis X"; slots LT, L1–L4, R1–R4 filled with the new bones;
  Detect (Bend Axis) also X, no finger on another axis. The thumb tip moves +Z when curled around its X: it curls around
  another axis, a step 12 topic.
- Screenshots: `D:\3D\blender_projects\midi_trial\screenshots\` `sheet_rest.png`, `sheet_curl30.png`, `sheet_curl60.png`
  (front, top and side of both hands), plus the single views.

## Pending
Checklist sections A–G, plugin issues table, severities with the user, verification commands, PR.
