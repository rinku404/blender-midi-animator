# Step 7 scope (approved by the user, 2026-11-12)

Source: the plugin issues in `docs/plan/reports/step-06-pipeline-trial.md` (P1–P9) and
`docs/plan/reports/step-12-fingering-trial.md` (P10–P17), severities confirmed by the user. The planning session should
copy this into PLAN.md's step 7; until then this note is the scope. Step 7 runs as four packages, **in this order**, one
agent at a time:

| Package | Issues | Goal |
|---|---|---|
| **7a Hold** | P1 (bad), P10 (bad), P2, P7 hold part | Lock works on any rig; the instrument's front can be set; Guess Bones finds `wrist` hands and an upper-chest strap; guide section on setting up the hold |
| **7b Breathing** | P8 (bad), P3 (bad) | Breath planner in core ("refill at every break" is the **only** rule); a Breathing section with one breath signal driving chest depth+width, belly, shoulders and torso lean, per-part sliders plus a master Intensity, live without re-bake; rig-aware scale axes; neck/shoulders don't inherit the swell |
| **7c Finger reach** | P12 (bad), P11 (bad), P13 | Index knuckle may swing along the instrument, **starting limit 15°**; thumb base may turn about the tube; misses listed per finger in panel 2 and the Info log; advice says which way to move the hand |
| **7d Polish** | P4, P5, P6, P9, P14, P15, P16, P17, P7 rest | Small UI, packaging and guide fixes |

User answers recorded with the approval:
1. Order 7a → 7b → 7c → 7d as proposed.
2. 7c: index knuckle swing along the instrument starts at 15°.
3. 7b: keep only the "refill at every break" breathing rule (no "sized" option).

Prototype material for 7b (outside the repo): `D:\3D\blender_projects\midi_trial\scripts\breath_planner.py` (rule
`every_break`), `breath_body.py` (drivers and sliders), test copy `midi_trial_breath_test.blend`.
