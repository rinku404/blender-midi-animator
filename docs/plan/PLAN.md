# MIDI Animator v1: implementation plan

Owner of this plan: the planning session (Claude, in the "MIDI Blender" project). Agents
execute **one step each** and report back in `docs/plan/reports/`. The planner reads the reports and
updates this file: statuses, the revision log, and new or changed steps.

Every agent reads **[AGENT_BRIEF.md](AGENT_BRIEF.md)** first.

## Status board

| Step | Title | Depends on | Needs the user? | Status |
|---|---|---|---|---|
| 0 | Baseline: core + Blender layer | — | — | ✅ done ([report](reports/step-00-baseline.md)) |
| 1 | Reconcile `main` into `v1-rewrite` | 0 | no | ⬜ todo |
| 2 | Port "Hold the Instrument" to v1 | 1 | no | ⬜ todo |
| 3 | Verify the HUD in Blender's UI | 1 | run Blender with a window | ⬜ todo |
| 4 | Finger quality: bend direction and an auto Rest pose | 2 | no | ⬜ todo |
| 5 | Chart completion: F#6, and a check against the old chart | 1 | no | ⬜ todo |
| 6 | Real-rig trial with the user's character and take | 2, 3, 4 | **yes** | ⬜ todo |
| 7 | Fixes from the trial | 6 | maybe | ⬜ todo (scope set after 6) |
| 8 | Robustness and performance on long takes | 6 | no | ⬜ todo |
| 9 | Release v1.0.0 | 7, 8 | approve the merge | ⬜ todo |

Statuses: ⬜ todo · 🔄 in progress · ✅ done · ⚠️ done with follow-ups · ⛔ blocked.
Steps 3 and 5 can run in parallel with 2 (each on its own branch).

## Revision log

| Date | Change |
|---|---|
| 2026-11-07 | Plan created. Step 0 recorded as done. PR #2 (hold + per-finger chart on the old file) found on `main`: added steps 1–2 to reconcile and port it. |

---

## Step 0: Baseline (done)

Core (`midi_animator/core/`, 28 pytest tests) and the Blender layer are written; `tests/test_in_blender.py`
passes in Blender 5.2.3 and the extension installs (commit `d871b70`). Never run: HUD preview,
export, ProRes, composite scene. See [reports/step-00-baseline.md](reports/step-00-baseline.md).

---

## Step 1: Reconcile `main` into `v1-rewrite`

**Goal:** PR #3 merges cleanly, with nothing from PR #2 silently lost.

**Why:** PR #2 (`dc74f08`, merged into `main` on 2026-11-06) changed the old single-file add-on,
which `v1-rewrite` deletes, so PR #3 now conflicts.

**Tasks**
1. Branch `plan/step-01-reconcile` from `origin/v1-rewrite`, then `git merge origin/main`.
2. Resolve the conflicts:
   - `midi_animator.py`: keep it **deleted**.
   - `tests/test_chart_and_hold.py`: **remove**, but first copy its hold assertions into
     `docs/plan/notes/hold-tests-to-port.md` for step 2. Don't port the per-finger chart tests:
     v1's chart is tested in `tests/core/test_fingering.py`.
   - `README.md`, `docs/aerophone-guide.md`, `tests/test_in_blender.py`: keep v1's versions. Save
     PR #2's "hold the sax like a player" guide text in `docs/plan/notes/hold-guide-text.md` for step 2.
3. Compare PR #2's chart (`SAX_CHART` / `chart_elements` on `main`) with
   `core/profiles.py::_sax_chart` for written 58–90, and list every difference in the report (it is input for step 5).
4. Run all tests, then open the PR into `v1-rewrite`.

**Acceptance criteria**
- [ ] `git merge-base --is-ancestor origin/main HEAD` succeeds on the branch.
- [ ] No `midi_animator.py` and no `tests/test_chart_and_hold.py` in the tree.
- [ ] Both notes files exist and are non-empty.
- [ ] The report has a chart-difference table (pitch, PR #2 elements, v1 combination, comment).
- [ ] pytest and `test_in_blender.py` pass.

---

## Step 2: Port "Hold the Instrument" to v1

**Goal:** the instrument hangs from a strap/chest bone and both hands stay locked to it with IK,
as in PR #2, rebuilt on v1's structure and without the breathing scaling the instrument.

**Background:** PR #2's `MIDIANIM_OT_lock_hands` / `unlock_hands` (see `git show origin/main:midi_animator.py`,
around line 1075) parents the instrument to a strap bone, keeping its world transform. It creates `MIDI Hold L/R` empties
as children of the instrument at each hand, adds a 2-bone IK on each forearm to the target and a
Copy Rotation on each hand. Unlock removes the constraints and targets.

**Tasks**
1. `core/rigs.py`: a pure function that guesses strap, hand.L and hand.R bones from `(name, parent)`
   lists (Rigify, Mixamo, VRoid, Biped; skip twist, finger, ORG/DEF/MCH), with pytest tests.
2. `blender/hold.py`: `lock_hands(context, s)` / `unlock_hands(context, s)` with the same behaviour
   as PR #2. Re-locking must be idempotent. Settings: `hold_strap_bone`, `hold_hand_l`, `hold_hand_r`
   (the instrument is `s.instrument`).
3. **Breathing conflict:** if the instrument hangs from the bone the Chest effect scales, the sax
   would grow with each breath. Fix it, and record the choice in an ADR. Options: (a) Chest preset avoids the
   strap bone (picks a different bone, and Analyze warns if they're the same); (b) parent the instrument
   through a non-scaling Child Of constraint instead of bone parenting. Pick (a) unless a test shows it can't work.
4. UI: a "Hold" box at the top of panel 2 (Fingers & Keys): instrument, three bone pickers, Guess,
   Lock, Unlock, plus a one-line hint ("pose the hold first").
5. Guide: add the hold section from `docs/plan/notes/hold-guide-text.md`, adapted to v1 panels.
6. ADR `docs/decisions/0011-hold-the-instrument.md`. It refines 0004: the instrument hangs from the strap
   bone and the hands follow it, so markers stay put relative to the hands.
7. Tests in `tests/test_in_blender.py` (port from `docs/plan/notes/hold-tests-to-port.md`): locking moves
   neither the sax, the hands nor the elbows; the sax and hands follow a chest bend; re-lock is idempotent; unlock
   cleans up; after a bake with the Chest effect, the instrument's world scale stays constant (±1e-4).

**Acceptance criteria**
- [ ] All tests above pass. Bone-guess pytest covers at least 3 naming conventions.
- [ ] ADR 0011 is written and indexed in `docs/decisions/README.md`.
- [ ] Autoassign still passes its existing tip-distance test with the hold locked.

---

## Step 3: Verify the HUD in Blender's UI

**Goal:** the HUD preview, PNG export, ProRes export and composite scene actually work in Blender 5.2.

**Why:** these need a GPU context, so `blender -b` can't run them. They have never been executed.

**Tasks**
1. `tests/test_hud_in_ui.py`, run **with a window**:
   `blender --factory-startup --python tests/test_hud_in_ui.py`. The script does its work from a
   timer (`bpy.app.timers`), writes results to `tests/out/hud_ui_result.json`, and quits Blender.
   - Export frames 1–30 of `examples/aerophone_sample.mid` to `tests/out/hud/`. Check there are 30 RGBA PNGs of the
     configured size, fully transparent outside the panel, and that at least one frame has "active" gold pixels near the hit line.
   - Compare one frame with `tests/hud_preview.py`'s Pillow render at the same time: same bars (position within ±3 px).
     Text can differ.
   - ProRes: encode and check that `hud.mov` exists and is over 0 bytes. If Blender's ffmpeg has no ProRes 4444 + alpha,
     the operator must report that clearly instead of failing obscurely. Fix it if needed.
   - Composite scene: create it, then check its strips (scene strip + HUD image strip, ALPHA_OVER, offset puts the HUD at the bottom).
     Render one frame to `tests/out/comp.png`.
   - Viewport preview: enable it, redraw a 3D view, and check there are no Python errors in the draw handler.
2. Fix whatever breaks in `blender/hud_draw.py`.
3. Attach two exported frames and the composite frame to the report (paths in the repo, not committed if large).

**Acceptance criteria**
- [ ] `hud_ui_result.json` shows every check passing (paste it into the report).
- [ ] Any fix comes with a reason in the report. CLAUDE.md "Status" is updated.

---

## Step 4: Finger quality: bend direction and an auto Rest pose

**Goal:** Autoassign poses look like real fingers, and the user doesn't have to author Rest by hand.

**Why:** plain IK may twist fingers sideways or bend joints backwards. Rest is currently a manual step.

**Tasks**
1. Bend control: before solving, set IK limits on the chain's bones (`lock_ik_*` / `use_ik_limit_*`)
   from a per-rig **Bend Axis** setting (X by default, with a "Detect" that picks the axis from the finger's rest curl),
   and restore the bones' IK settings afterwards. Add an option "Keep Twist" (lock Y).
2. Add a test: after Autoassign, every chain joint's rotation is ≈ zero on the locked axes
   (quaternion → Euler in bone space, ±1°), and the tip distance is still < 4 mm.
3. Auto Rest: Autoassign also builds `F.Rest`: every finger at Up over its home key, plus the current hand
   bones. If `s.rest_pose` is empty, it uses it. A manual Rest pose still wins.
4. Update the guide and the ADR index (new ADR only if the behaviour of 0004 changes; a note in 0004 is enough otherwise).

**Acceptance criteria**
- [ ] The new tests pass, and existing tests still pass.
- [ ] On the test rig, no joint bends against the bend axis (state the measured max in the report).

---

## Step 5: Chart completion: F#6, and a check against the old chart

**Goal:** the built-in chart covers the full alto/tenor range of PR #2 (to F#6), and every intentional
difference from PR #2's chart is documented.

**Tasks**
1. Add the high F# key: slot and key (`R1:HighF#` or a new slot; justify the choice in the report), with chart entry F#6 = octave + palm
   (D, Eb, F) + side E + high F#, simplified to the marker model like the other palm keys.
2. Using step 1's difference table, fix any real mistakes in `_sax_chart`, and document intentional
   differences (e.g. low C#: PR #2 uses LP, v1 uses R4:LowC + L4:LowC#) in a docstring.
3. pytest: the full range 58–90 is mapped, every key used exists in its slot, and the octave key is present
   from 74 up.

**Acceptance criteria**
- [ ] `max(chart) == 90`, and tests pass.
- [ ] The report lists every changed chart entry with its reason.

---

## Step 6: Real-rig trial with the user's character and take ⚑ user

**Goal:** run the whole workflow on the user's real character, instrument and Aerophone take, and collect
everything that's wrong or awkward.

**How:** the agent drives and the user does the hands-on parts. The agent prepares
`docs/plan/notes/trial-checklist.md` from `docs/aerophone-guide.md` (one line per action, with an
expected result). The user goes through it in Blender's UI. The agent records the outcomes, screenshots
and timings. The agent may also inspect the user's .blend from a script (bone names, marker count, poses).

**Must cover:** Detect Fingers on the real rig, Hold lock, placing all markers (time it), Autoassign
(look at every finger), Fill From Chart, blow effects with the real take's CC2, Bake, playback with audio,
HUD preview, and export of 10 s.

**Report:** an issue table with columns #, area, what happened, expected, severity (blocker / bad / polish), and
suggested fix. Severity ratings are needed because the planner turns this table into step 7.

**Acceptance criteria**
- [ ] The checklist is fully walked or each skipped line has a reason.
- [ ] The issue table is filled in, and the user confirmed the severities.

---

## Step 7: Fixes from the trial

The scope is set by the planner after step 6: each blocker or bad issue becomes a task here, or a step of its own if large.

---

## Step 8: Robustness and performance on long takes

**Goal:** a 10-minute take bakes and exports in reasonable time, and bad input fails with clear messages.

**Tasks**
1. `tests/make_sample_midi.py`: add a generated 10-minute take (about 3,000 notes, dense CC2, tempo changes).
2. Measure bake time and HUD export time per frame, and record them in the report. Targets: bake < 20 s, blow keys
   reduced (drop keys that a linear interpolation reproduces within 0.5% of the range) without visible change (test the max error).
3. Robustness: MIDI with no notes, only drums on channel 10, overlapping notes, a note-off before its note-on, files with
   SMPTE timing, a missing rig/bones/markers. Each gives a clear report message, not a traceback. Add pytest
   and in-Blender cases.
4. Undo: Bake, Autoassign and Lock are one undo step each (check they're `UNDO` operators and don't leave temporary objects).

**Acceptance criteria**
- [ ] Timings are in the report and meet the targets, or there's a profile and a plan to meet them.
- [ ] Every robustness case is tested and passes.

---

## Step 9: Release v1.0.0 ⚑ user approves the merge

**Tasks**
1. `blender --command extension validate` and `build`, then install the built zip in a clean profile and run the
   e2e test against the installed copy.
2. `CHANGELOG.md`, README screenshots (panels and HUD), and the version stays 1.0.0 (bump if anything changed after a build was shared).
3. Update CLAUDE.md status, mark the plan's steps done, and ask the user to merge PR #3 into `main`.
4. After the merge: tag `v1.0.0` and create a GitHub release with the zip.

**Acceptance criteria**
- [ ] The zip installs and enables in a clean Blender 5.2 profile, and e2e passes on it.
- [ ] The release exists with the zip attached.
