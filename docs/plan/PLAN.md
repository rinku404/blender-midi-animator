# MIDI Animator v1: implementation plan

Owner of this plan: the planning session (Claude, in the "MIDI Blender" project). Agents
execute **one step each** and report back in `docs/plan/reports/`. The planner reads the reports and
updates this file: statuses, the revision log, and new or changed steps.

Every agent reads **[AGENT_BRIEF.md](AGENT_BRIEF.md)** first.

**Branches:** `main` is the working branch (v1 landed there with step 1's PR #4). Steps branch from
`origin/main` and open their PR into `main`. `v1-rewrite` is retired; don't build on it.

## Status board

| Step | Title | Depends on | Needs the user? | Status |
|---|---|---|---|---|
| 0 | Baseline: core + Blender layer | — | — | ✅ done ([report](reports/step-00-baseline.md)) |
| 1 | Reconcile `main` into `v1-rewrite` | 0 | no | ✅ done ([report](reports/step-01-reconcile.md)) |
| 2 | Port "Hold the Instrument" to v1 | 1 | no | ✅ done ([report](reports/step-02-hold.md)) |
| 3 | Verify the HUD in Blender's UI | 1 | run Blender with a window | ✅ done ([report](reports/step-03-hud-ui.md)) |
| 4 | Finger quality: bend direction and an auto Rest pose | 2 | no | ✅ done ([report](reports/step-04-finger-quality.md)) |
| 5 | Chart completion: F#6, and a check against the old chart | 1 | no | ✅ done ([report](reports/step-05-chart.md)) |
| 6 | Pipeline trial on CJ + clarinet (no fingering judgement) | 2, 3, 4, 5 | **yes** | 🔄 in progress (draft PR #10) |
| 10 | Clarinet profile (B♭ Boehm chart) | 5 | no | ✅ done ([report](reports/step-10-clarinet.md)) |
| 11 | Hands with fewer fingers (shared finger bones) | 4 | answered 2026-11-11 | 🔄 in progress |
| 12 | Fingering trial: CJ playing the clarinet | 6, 10, 11 | **yes** | ⬜ todo |
| 7 | Fixes from the trials | 6, 12 | maybe | ⬜ todo (scope set after 6 and 12) |
| 8 | Robustness and performance on long takes | 6, 12 | no | ⬜ todo |
| 9 | Release v1.0.0 | 7, 8 | approve the merge | ⬜ todo |

Statuses: ⬜ todo · 🔄 in progress · ✅ done · ⚠️ done with follow-ups · ⛔ blocked.
Steps 10 and 11 can run in parallel with each other and with step 6. Step numbers 10–12 were added after
step 9 was written; follow the **Depends on** column, not the numbers, for the order.

## Revision log

| Date | Change |
|---|---|
| 2026-11-07 | Plan created. Step 0 recorded as done. PR #2 (hold + per-finger chart on the old file) found on `main`: added steps 1–2 to reconcile and port it. |
| 2026-11-11 | Step 10 done (PR #9): B♭ Clarinet profile, written E3–C6, `default_transpose` (sax 0, clarinet +2), thumb keys `Hole` / `Register` / `RegOnly`, new `L4:C#/G#`; an independent chart from a second agent matched on all 33 pitches. The take is written E3–A5, all mapped. Review fixes: `sync_finger_slots` relabels in place (keeps step 11's new fields), fixed profile enum numbers. Step 11 started with the user's answers (recorded in step 11). Step 6 has draft PR #10. Open for the user: after an instrument switch, Fill without Overwrite keeps sax rows and Analyze counts them as mapped (step 7 warning vs. a step 12 checklist line). |
| 2026-11-10 | **Target changed** (user): the video is CJ (`carl_johnson_cj.glb`, 2 three-joint fingers per hand, no thumb, no CheekPuff) playing a **B♭ clarinet**, not a sax. Step 6 narrowed to the pipeline (fingering can't be judged on this setup yet). Added step 10 (clarinet profile), step 11 (rigs with fewer fingers) and step 12 (fingering trial). Transpose for the take is **+2** (B♭ clarinet: written = concert + 2; the take's lowest note, MIDI 50 = concert D3, is the clarinet's written E3), and the HUD shows **Concert** pitch so it displays the recorded notes. ADR 0012. Trial files: `D:\3D\blender_projects\midi_trial\` (`midi_trial.blend`, inputs in `src\`). |
| 2026-11-09 | Step 5 done (PR #8): chart Bb3–F#6 (new `R1:HighF#`), low C# corrected to the standard fingering (six fingers + left pinky C#; the earlier "intentional" note was wrong). Step 6 gains marker placement for palm/side/high F# keys and asks the user to confirm low C# and F#6. Step 7 gains an optional candidate: alternate fingerings. |
| 2026-11-08 | Step 3 done (PR #7): all four HUD paths work (24/24 checks). Fixed ProRes and composite colours (they were toned by AgX), composite offset at render % ≠ 100, and the cut-off Hold box. Composite under AgX/Filmic keeps the render exact and warns that the HUD is toned (user's choice, ADR 0009 note). Step 6 gains HUD checks in Resolve and under AgX; step 7 gains confirmed UI polish (other cut-off labels, preview hidden under the sidebar). |
| 2026-11-07 | Step 4 done (PR #6): bend-only IK limits (0.000° against the axis), auto `F.Rest`, hand drift 7.9 → 0.000 mm. Step 6 now also depends on step 5 (a real take may reach F#6) and gains checks from step 4's report: tip-miss messages and the knuckle-extension constant, thumb bend axis, Rigify `upper_arm_fk` inherit scale. Step 7 gains a polish candidate: spread curl across joints. |
| 2026-11-07 | Step 2 done (PR #5). Breathing conflict solved with option (b), a scale-free Child Of (ADR 0011), because (a) can't work. Added: step 4 task to remove the 7.9 mm hand drift under chest breathing; step 3 task to look at the Hold box in the UI; step 6 checks for hand accuracy and Rigify `hand_fk`. |
| 2026-11-07 | Step 1 done (PR #4). It was merged into `main` rather than `v1-rewrite`, so `main` now holds v1 and is the working branch; `v1-rewrite` and PR #3 are retired. Step 9 no longer merges PR #3. Step 5 gains palm-key guide text (from step 1's follow-ups). Step 2 gains a note: the user's `/init` edits to `CLAUDE.md` are in `git stash` on their machine. |

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

**Note:** the user's machine has uncommitted `CLAUDE.md` edits from `/init` in `git stash` (step 1 report).
Leave the stash alone; the user decides whether to apply it.

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
   While Blender's window is open, also screenshot panel 2's **Hold** box (added in step 2, never seen in the UI)
   and report any layout problems; fix only obvious ones.
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
4. **Hand drift under breathing** (from step 2): with the hold locked and the Chest effect at its default, the hands sit up
   to 7.9 mm off their `MIDI Hold` targets at peak breath, because the arm IK solves under a scaled chest. Remove or reduce it
   (for example, arm bones don't inherit the chest's scale, or the Chest effect scales a child bone the arms don't descend from).
   Test: max hand-to-target gap while breathing < 1 mm, and the sax scale stays 1.0.
5. Update the guide and the ADR index (new ADR only if the behaviour of 0004 or 0011 changes; a note in the ADR is enough otherwise).

**Acceptance criteria**
- [ ] The new tests pass, and existing tests still pass.
- [ ] On the test rig, no joint bends against the bend axis (state the measured max in the report).
- [ ] Hand-to-target gap while breathing < 1 mm (measured value in the report).

---

## Step 5: Chart completion: F#6, and a check against the old chart

**Goal:** the built-in chart covers the full alto/tenor range of PR #2 (to F#6), and every intentional
difference from PR #2's chart is documented.

**Tasks**
1. Add the high F# key: slot and key (`R1:HighF#` or a new slot; justify the choice in the report), with chart entry F#6 = octave + palm
   (D, Eb, F) + side E + high F#, simplified to the marker model like the other palm keys.
2. Using step 1's difference table, fix any real mistakes in `_sax_chart`, and document intentional
   differences (e.g. low C#: PR #2 uses LP, v1 uses R4:LowC + L4:LowC#) in a docstring.
3. Guide: for D6–F#6, say exactly which palm/side markers each note uses and where to place them
   (`PalmEb` = where the palm presses D+Eb together, `PalmF` = D+Eb+F, and the high F# key), from step 1's chart table.
4. pytest: the full range 58–90 is mapped, every key used exists in its slot, and the octave key is present
   from 74 up.

**Acceptance criteria**
- [ ] `max(chart) == 90`, and tests pass.
- [ ] The report lists every changed chart entry with its reason.

---

## Step 6: Pipeline trial on CJ + clarinet ⚑ user

**Status note (2026-11-10):** in progress. The target is now CJ playing a B♭ clarinet (ADR 0012). CJ's hands have two
fingers each and the plugin has no clarinet chart yet, so **this trial covers the pipeline only**. Fingering is judged
in step 12, after steps 10 and 11.

**Setup:** `D:\3D\blender_projects\midi_trial\midi_trial.blend` (24 fps, CJ + clarinet scaled to ~0.66 m). Inputs are copied
to `midi_trial\src\` (`carl_johnson_cj.glb`, `clarinet_model_with_annotations.glb`, `zelda_recorded_v1_b.mid`, `zelda_recorded_v1_B.wav`).
Originals in `D:\3D` and `D:\Music\Media` stay untouched. **Transpose +2**, HUD pitch display **Concert**.

**How:** the agent prepares `docs/plan/notes/trial-checklist.md` from the guide (one line per action, with the expected
result). The user does it in Blender's UI, and the agent records outcomes, screenshots and timings. The agent may
inspect the .blend from a script.

**Must cover:** Analyze (tracks, CC2, range, unmapped notes with the sax chart are expected and only noted), Hold:
guess and lock CJ's strap/hand bones with the clarinet at the lips, then breathing (hand accuracy against the clarinet),
the Chest effect with the real CC2 (Lung mode), CheekPuff (the user sculpts one following guide section 3, or it's logged
as a test-setup limit), Bake, playback with audio, HUD preview, export of 10 s, the HUD over the take in DaVinci Resolve,
and Make Composite Scene with the user's AgX scene. **Also record for step 11:** what Detect Fingers does on CJ's
`arm left finger 1a_045`-style bones, and which bone, if any, could act as a thumb.

**Skip (deferred to step 12):** marker placement, Autoassign quality, Fill From Chart judgement, palm/side keys, thumb bend axis, curl naturalness.

**Report:** two tables. **Plugin issues** (#, area, what happened, expected, severity blocker / bad / polish,
suggested fix) become step 7. **Test-setup limits** (things caused by the assets: two-finger hands, missing CheekPuff,
model scale, stray objects) are kept apart so they aren't mistaken for plugin bugs.

**Acceptance criteria**
- [ ] The checklist is fully walked or each skipped line has a reason.
- [ ] Both tables are filled in, and the user confirmed the severities.

---

## Step 10: Clarinet profile (B♭ Boehm)

**Goal:** a second instrument in the dropdown, **B♭ Clarinet**, with a correct fingering chart for the user's take.

**Tasks**
1. Research the standard Boehm B♭ clarinet fingering chart from **at least two published sources** (list them in the
   report). Write the chart in `core/profiles.py` as a new registered profile, keyed by **written** pitch like the sax chart.
2. Slots and keys (adjust from the sources and justify in the report; keep one finger = one marker per key):
   - `LT` left thumb: `Thumb` (the thumb hole/ring) and `Register`.
   - `L1`: `L1` (hole/ring), plus the throat keys `A` and `G#` (the side of the index presses them).
   - `L2`, `L3`: their holes/rings.
   - `L4` left pinky: `E/B`, `F/C` (and `F#/C#`, `Ab/Eb` if the sources put them on the left).
   - `R1`: `R1` hole/ring, plus side trill keys if a chart entry needs them (for example `Side4` for throat B♭ alternatives).
   - `R2`, `R3`: holes/rings.
   - `R4` right pinky: `E/B`, `F/C`, `F#/C#`, `Ab/Eb` (the standard choice per note is in the chart; one fingering per pitch).
   - The right thumb only supports the instrument (no slot), as on the sax.
3. Range: at least written **E3 (52) to C6 (84)**, plus the altissimo notes the user's take needs. Read
   `zelda_recorded_v1_b.mid` with Transpose +2 to find them, and **ask the user before going above C6** if the
   altissimo fingering choice matters to them.
4. Throat tones (written G4, G#4, A4, B♭4) and the break (B4 = E3 fingering + Register) need care. Test them
   explicitly. The clarion register is the chalumeau fingering + `Register` + 19 semitones, except where the sources differ.
5. Add a `default_transpose` to profiles (sax 0, B♭ clarinet +2), applied when the user switches instrument if Transpose
   is still at the previous profile's default. Guide: a clarinet section (markers on rings/holes, register key, throat keys).
6. pytest: the whole range mapped, every key in its slot, the register key exactly where the sources say, and the
   throat tones and break checked by value. The e2e test fills the clarinet chart on the test rig.

**Acceptance criteria**
- [ ] Sources listed, and every chart entry traceable to them (differences from a source explained).
- [ ] Every written note in the take (with Transpose +2) is mapped; tests pass.

---

## Step 11: Hands with fewer fingers (shared finger bones)

**Goal:** rigs like CJ (two three-joint fingers per hand, no clear thumb) still play convincingly. Several finger
slots can share one bone chain.

**Before coding, ask the user and record the answers:**
1. On CJ, which slots should each of the two fingers stand for? Suggested: finger 1 = index (L1/R1), finger 2 =
   middle + ring + pinky (L2–L4 / R2–R4). Thumb (LT): none, or the hand bone's own tilt?
2. When the slots sharing a chain disagree (one presses, another lifts), which wins? Suggested: **pressing wins**, and the
   chain goes to the marker of the **highest-priority pressing slot** (order: the slot listed first).

**User's answers (2026-11-11):** (1) as suggested: finger 1 = index (L1/R1), finger 2 = middle + ring + pinky
(L2–L4 / R2–R4), and the thumb (LT) is **the hand bone's own slight tilt**, not "none". (2) as suggested: pressing wins,
highest-priority pressing slot's marker. Test rig for Detect + sharing: CJ's original two-finger rig in
`D:\3D\blender_projects\midi_trial\midi_trial_before_fingers.blend` (`midi_trial.blend` now has rebuilt 4-finger hands).
Note from step 6 (P1): Lock's forearm IK targets the forearm tail, which on CJ's FBX rig sits 39 cm from the wrist.

**Tasks**
1. Data model: a finger slot can say "uses the bones of slot X" (a `shares` field). Detect Fingers handles numbered
   finger names such as `arm left finger 1a_045` (side from "left/right", order from the digit, joints from a/b/c), and
   proposes the sharing above when it finds fewer than four fingers.
2. Core (`core/fingering.py`): combine the shared slots' timelines into one timeline per bone chain with the rule from
   question 2, with pytest tests (agreeing slots, disagreeing slots, one slot pressing a different key mid-note).
3. Autoassign: solve each shared chain onto the markers of every slot that uses it (pose names stay per slot and key).
4. A slot with no bones (for example LT on CJ) is skipped silently in Bake and Autoassign, and Analyze lists it once as "not animated".
5. UI: a "Shares bones with" dropdown per finger in panel 2. Guide: a short section for low-finger rigs.
6. ADR for shared slots (supersedes nothing; refines 0003).

**Acceptance criteria**
- [ ] pytest covers the combining rule; the e2e test builds a 2-finger hand, shares slots, autoassigns and bakes.
- [ ] The user's answers are in the report.

---

## Step 12: Fingering trial: CJ playing the clarinet ⚑ user

**Goal:** the fingering part of the trial, on the real target.

**Must cover:** Detect Fingers and slot sharing on CJ, placing all clarinet markers (time it) with the clarinet held
at the lips (from step 6), Autoassign (look at every finger; record every "fingertip … mm off" message), Fill From
Chart with the clarinet profile and Transpose +2, Bake, and playback with audio. Judge: do the right fingers move on
each note, do curls look natural or bend mostly one joint, does the register key/thumb read correctly, and does the
knuckle need extension (step 4's 10° option). The user, who knows the take, confirms the fingerings of a few notes by eye.

**Report:** the same two tables as step 6 (plugin issues, test-setup limits).

**Acceptance criteria**
- [ ] Every note in the take bakes with a mapped fingering (or the report says why not).
- [ ] Both tables filled in, severities confirmed by the user.

---

## Step 7: Fixes from the trials

The scope is set by the planner after steps 6 and 12: each blocker or bad issue becomes a task here, or a step of its own if large.

Already confirmed (do regardless, from step 3): fix the remaining labels cut off in the default sidebar width
("Charact…" in panel 2, "Instrum…" in panel 1, the "Detect Fingers (or Analyze)…" hint); make the viewport HUD
preview avoid the sidebar (use the visible region width) or add a horizontal position option.
Optional: a "Standard view" toggle on Make Composite Scene.

Candidates already known (included only if the trial confirms them, or the user asks): alternate fingerings as
per-note choices (front F, side Bb/C, bis Bb; step 5); knuckle extension allowance (~10°);
per-finger Bend Axis override (thumb); spread curl across joints instead of bending mostly one (step 4 report).

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
3. Update CLAUDE.md status and mark the plan's steps done; the user approves the release PR into `main`.
4. After the merge: tag `v1.0.0` on `main` and create a GitHub release with the zip.

**Acceptance criteria**
- [ ] The zip installs and enables in a clean Blender 5.2 profile, and e2e passes on it.
- [ ] The release exists with the zip attached.
