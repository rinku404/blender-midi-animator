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
| S5 | **Setup change (2026-11-10): CJ's hands rebuilt with real fingers** | See the section below. Done by script on `midi_trial.blend`; the file as the user left it is kept as `midi_trial_before_fingers.blend`. | Detect Fingers now fills all 9 slots (the old two-finger result is recorded in the checklist, B1, from the script prediction `{}`). |
| S6 | Mesh | Body mesh `Object_6` is not exactly symmetric: the right half equals the mirror of the left plus (0.0712, -0.0047, -0.1032) in mesh units. | New right-hand geometry and right bones use the same offset so they sit on the right hand. |
| S7 | File | `midi_trial.blend` was saved with `Object_6` in Edit Mode, and contains no test cube (the user's cube was not saved). | Script switched the object to Object Mode before editing. Nothing to delete. |

### S5: hand rebuild (setup change)
Backup: `D:\3D\blender_projects\midi_trial\midi_trial_before_fingers.blend` (the file exactly as given).
Rebuilt by script (no Blender MCP was connected). Everything is in the one body mesh `Object_6`.

- **Measured (left, mesh units; 1 unit = 0.0254 m):** wrist bone x = 29.170, knuckle rim x = 32.555 (back of hand 3.385), rim width y −2.182..0.677 (2.858), finger thickness 0.715 (a quarter of the rim width).
- **Fingers:** 4 per hand, 8 vertices per ring, 3 segments (4 rings + closed ends = 32 vertices each). Lengths from the knuckle: index 3.216 (95 %), middle 3.385 (100 %), ring 3.216 (95 %), pinky 2.539 (75 %). Tip ring tapers to 80 %. Base ring sits 0.35 inside the rim. Rest curl 8° per joint toward the palm (−Z). Material index 0 (`body_upper`), smooth shading, UVs set to a skin sample of the hand (u,v = 0.335, 0.308), the body's custom normals preserved, new loops get vertex normals.
- **Right hand:** 81 faces deleted (no left twin by position, after the 0.0712/−0.0047/−0.1032 offset), the fingers mirrored with the same offset, normals recalculated. Two left triangles at the palm base have no right twin (different triangulation there); both were kept.
- **Thumb:** the existing prong was split by weights, not rebuilt: vertices weighted to the old `1a/1b/1c` bones (≥ 0.5, |x| ≥ 29.5) were assigned to `thumb.01/02/03` by projection onto the new bones (L 5/9/13 vertices, R 6/9/13).
- **Bones:** `f_<finger>.01..03.<L|R>` and `thumb.01..03.<L|R>`, parented to `arm left wrist_041` / `arm right wrist_051`, `.02` and `.03` connected. Roll puts the curl on local X (left fingers X = +Y, right fingers X = −Y; thumb X along the thumb's own rest-bend axis). Old finger bones kept, with no weights.
- **Weights:** each new vertex has exactly one group at 1.0 (311 weighted vertices checked, 0 bad, 0 unweighted vertices in the hand region); rings 0–1 → segment 1, ring 2 → segment 2, ring 3 and cap → segment 3. Old finger groups hold 0 vertices; 42 leftover rim/seam vertices went to the wrist bone.
- **Pose test:** each of the 30 new bones rotated 30° in Pose Mode: only its own vertices and those of the later segments moved (0 unexpected vertices), pose reset afterwards. Finger tips move toward −Z (the palm); the thumb tip moves +0.116 in Z (the thumb curls around another axis: step 12).
- **Screenshots:** `D:\3D\blender_projects\midi_trial\screenshots\` (`sheet_rest.png`, `sheet_curl30.png`, plus the 12 single views).
- **Detect Fingers (plugin, headless run on the rebuilt file):** "Found all 9 fingers; Bend Axis X"; the 9 slots (LT, L1–L4, R1–R4) filled with the new bones; the separate Detect (Bend Axis) also gives X, no finger on another axis.

## Pending
Checklist sections A–G, plugin issues table, severities with the user, verification commands, PR.
