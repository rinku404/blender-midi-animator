# Step 12 trial checklist: CJ playing the clarinet (fingering)

Target: CJ with his **rebuilt five-finger hands** (step 6, S5) playing a B♭ clarinet, take
`zelda_recorded_v1_b.mid`. The user chose the rebuilt hands over CJ's original two-finger hands, so slot
sharing (step 11) isn't exercised on CJ here: step 11's own tests and its run on the original rig cover it.

File: `D:\3D\blender_projects\midi_trial\midi_trial.blend`. It holds the hold pose from step 6 (clarinet at
the lips, hands locked) and the rig tidy of 2026-11-12: 12 unused finger bones deleted, body bones pointed
along the body, In Front off, Icosphere deleted. The mesh is unchanged (0.001 mm). Backup:
`midi_trial_pre_tidy.blend`. Settings: **Transpose +2**, instrument **B♭ Clarinet**.

Each line records result (ok / issue / limit / skipped), a note, and a timing where marked ⏱.
Findings go to one of two tables in the report: **plugin issue** or **test-setup limit**.

## How to read the click instructions
The user is new to Blender, so every step says where to click. Screen areas (default *Layout* workspace):

| Name used here | Where on screen |
|---|---|
| **3D viewport** | the big area in the middle, where CJ is |
| **Viewport header** | the row of menus along the top of the 3D viewport: mode dropdown (e.g. *Object Mode*), *View · Select · Add · Object* |
| **Toolbar** | the column of tool icons down the left edge of the 3D viewport |
| **Sidebar / MIDI tab** | press **N** with the mouse over the 3D viewport; tabs run down its right edge; click **MIDI** |
| **Outliner** | top-right corner: the list of object names (Camera, Clarinet, Sketchfab_model …) |
| **Properties editor** | right side below the Outliner, with a column of tab icons down its left edge |
| **Timeline** | bottom strip: current frame box, Start, End, play controls |
| **Status bar** | the thin bar at the very bottom of the window; operator messages appear there |

## A. Setup
| # | Action (where to click) | Expected |
|---|---|---|
| A1 | **Update the extension.** Top menu bar **Edit → Preferences** → left column **Get Extensions** → find **MIDI Animator** in the list → its **▾** menu (right end of its row) → **Uninstall**. Then the **▾** at the top right of that page → **Install from Disk…** → pick `D:\3D\blender_projects\midi_trial\extension_main\midi_animator-1.0.0.zip` → **Install from Disk**. Close Preferences and **restart Blender**. | MIDI Animator listed and ticked |
| A2 | Open the file: top menu **File → Open…** → `D:\3D\blender_projects\midi_trial\midi_trial.blend`. Hover the 3D viewport, press **Z**, choose **Material Preview** to see textures. | CJ holding the clarinet, bones pointing along the body |
| A3 | Sidebar **MIDI** tab → panel **1. Instrument & MIDI** → **Instrument** dropdown (first row) → **B♭ Clarinet**. Check **Transpose** (under *Performer*) still reads **2**. | Transpose stays +2 |
| A4 | Same panel: click **Analyze MIDI**. Read the summary lines under it (widen the sidebar by dragging its left edge if they're cut off). | 111 notes, written E3–A5; "Unmapped notes" lists all 21 written notes (the Note Map is still empty) |

## B. Fingers
| # | Action (where to click) | Expected |
|---|---|---|
| B1 | Panel **2. Fingers & Keys** → **Detect Fingers** (hand icon, below the *Hold the instrument* box). Read the status bar. | "Found all 9 fingers; Bend Axis X". No sharing proposed |
| B2 | In the finger list (same panel), click **L Thumb (register)**. In the box below, check its bones and **Press Tilt (°)**. | Bones `thumb.01.L` → `thumb.03.L`; Press Tilt **0** (a real thumb, so no tilt) |
| B3 | Click **R Pinky** in the list and check **Shares Bones With**. | Empty (no sharing on five-finger hands) |

## C. Key markers ⏱ (16 markers)
The take uses **16** of the clarinet's keys. Only these need markers (from `core/profiles.py` and the take with
Transpose +2):

| Finger (list name) | Keys to place | Where on the clarinet (guide, *Clarinet keys*) |
|---|---|---|
| L Thumb (register) | `Hole`, `Register` | `Hole`: thumb ring at the **back**, where the thumb pad closes it. `Register`: near (lower) edge of the register key just above it |
| L Index | `Hole`, `A`, `G#` | `Hole`: first (top) front ring. `A`: throat A key above it. `G#`: throat G# key beside it |
| L Middle | `Hole` | second front ring |
| L Ring | `Hole` | third front ring |
| L Pinky | `E/B`, `F#/C#`, `C#/G#` | left little-finger keys of those names (`C#/G#` is the top one) |
| R Index | `Hole`, `Eb/Bb` | fourth ring; `Eb/Bb`: lowest side key, where the side of the right index presses it |
| R Middle | `Hole` | fifth ring |
| R Ring | `Hole` | sixth ring |
| R Pinky | `F/C`, `Ab/Eb` | right little-finger keys of those names (`Ab/Eb` is the top one) |

Not needed for this take: `RegOnly` (thumb), `F/C` (left pinky), `E/B`, `F#/C#` (right pinky).

**Get CJ out of the way first** (his hands cover the holes):
1. In the **Outliner**, find **Sketchfab_model** (CJ's top-level item).
2. Hold **Shift** and click its **eye icon** (right end of its row). Shift hides everything inside it too. Only
   the clarinet stays visible.

**Set up the Cursor tool once:**
1. In the **Toolbar** (left edge of the 3D viewport), click the **second icon from the top**: a circle with a
   crosshair (the *Cursor* tool).
2. A settings row appears along the top of the 3D viewport. Keep **Surface Project** ticked and set the **Orientation** dropdown to
   **Geometry** (Blender 5.2's name; older versions call it *Surface*). Now a click puts the 3D cursor on whatever
   you click, facing straight out of that surface. With *View*, every arrow would point at the camera instead.

**Place one marker** (repeat for each key in the table):
1. Zoom and turn the view until the key is big on screen: mouse wheel to zoom, middle-mouse drag to orbit,
   Shift + middle-mouse drag to pan.
2. **Left-click** on the key or ring. The red-and-white 3D cursor jumps there.
3. In the **MIDI** tab → panel **2. Fingers & Keys** → click the finger in the list (e.g. *L Index*).
4. In the **Key markers** box below, click **Place** on the key's row (e.g. `A`). The dot turns into a ✓ and
   the button now says **Move**. An arrow appears on the key, pointing out of it.
5. Wrong spot? Click again on the right spot, then **Move** on that row.

When all 16 are placed: click the **Select** tool (top icon of the Toolbar) to leave the Cursor tool, and
**Shift + click** the eye of **Sketchfab_model** again to bring CJ back.

| # | Action | Expected |
|---|---|---|
| C1 | ⏱ Place the 16 markers above; note the time and anything hard (keys hidden, arrow direction, picking the right key) | 16 rows show ✓ |
| C2 | Check the arrows from the side: each points **out** of its key, toward where the finger lifts | All out of their keys |

## D. Autoassign
| # | Action (where to click) | Expected |
|---|---|---|
| D1 | Panel **2** → **Bend Axis** row: should read **X**. ⏱ Click **Autoassign Finger Poses** (big button). Read the status bar and copy every "fingertip … mm off" message. | Poses created for every placed key, plus `F.Rest`; few or no "mm off" messages |
| D2 | For **each** finger: click it in the finger list; under the Autoassign box its poses are listed (`F.L1.A.Down`, `F.L1.A.Up` …). Click the **eye** icon of each **Down** pose and look at the hand. | The fingertip sits on its key; the finger curls naturally (not just one joint bent); no sideways twist |
| D3 | Note any finger that bends mostly at one joint, misses its key, or would need the knuckle to extend backwards (step 4's 10° knuckle option) | Recorded per finger |

## E. Note map
| # | Action (where to click) | Expected |
|---|---|---|
| E1 | Panel **3. Note Map** → **Fill: This File**. If the map had rows from the sax before, open the small **operator panel** that appears at the bottom-left corner of the 3D viewport, tick **Overwrite Existing**. | 21 notes listed, E3–A5 written |
| E2 | Click **B4** in the list: the finger grid shows its keys. | E3's fingering + `LT: Register` (the break) |
| E3 | Click **G4**: | every finger `up` (open G) |
| E4 | Click **A4**: | only `L1: A` |

## F. Bake and playback
| # | Action (where to click) | Expected |
|---|---|---|
| F1 | ⏱ Panel **6. Bake** → **Bake MIDI to Animation**. Copy the status bar message. | "Baked: 111 fingered notes; Chest ← CC2", no unmapped notes, no missing poses |
| F2 | In the **Timeline**, click the current-frame box, type `1`, Enter. Press **Space** (mouse over the 3D viewport) to play with audio; Space again to stop. | Fingers move with the notes |
| F3 | Watch a few notes you know (suggestions: E4 played 22×, A4 15×, F4 14×, G4 open, B4 across the break). Do the right fingers go down on each? | The user confirms by eye |
| F4 | Judge: natural curls or one-joint bends? Does the thumb read (hole vs register)? Does the knuckle need extension? | Recorded |

## G. Wrap-up
| # | Action |
|---|---|
| G1 | Review the **Plugin issues** table with the user; confirm severities (blocker / bad / polish) |
| G2 | Review the **Test-setup limits** table |

## Walk-through log
Blender 5.2.3; extension built from `main` @ `aa0c0e7` (`extension_main\midi_animator-1.0.0.zip`).

| # | Result | Note | ⏱ |
|---|---|---|---|
| A1 | issue → fixed | Installed and ticked, but at A3 the Instrument list had no clarinet: the **old** step 6 zip had been picked. Both builds are named `midi_animator-1.0.0.zip`, one folder apart (`midi_trial\` and `midi_trial\extension_main\`). The agent renamed the old one `OLD_step06_midi_animator-1.0.0.zip` and copied the main build into the user extensions folder; the user restarted Blender. Observation for step 7: every build has the same version, so Blender can't tell them apart, and Install from Disk never says which build is installed. | – |
| A2 | ok | File opens with CJ holding the clarinet. The user still saw sideways bones, so two more rig fixes were made (setup change, mesh unchanged): the root bone shortened to a 15 cm stub (`scripts\shorten_root.py`, max move 0.0011 mm, backup `midi_trial_pre_root.blend`), and the wrist bones pointed into the hands (Lock targets turned by the same rest change) with the 22 face bones pointed out of the face (`scripts\fix_leaf_bones.py`, max move 0.0007 mm, hands on targets 0.000 mm, backup `midi_trial_pre_leaf.blend`). The user: "the bones look right now". | – |
| A3 | ok | **B♭ Clarinet** offered and selected (after the A1 fix). Transpose is checked through A4's written range. | – |
| A4 | ok | Transpose 2. "111 notes, 54.4 s, 1 tracks"; "Performer: 111 notes, written E3–A5"; controllers CC2 (2765), CC11 (2…); "Unmapped notes…E5, F#5, G#5, A5" (cut at the default width, as in step 6 P5). | – |
| B1 | ok | "Found all 9 fingers; Bend Axis X". | – |
| B2 | ok, 1 remark | L Thumb (register): Own bones, `thumb.01.L` → `thumb.03.L`, Press Tilt 0.0. Remark: each bone row has **two ✕ buttons** side by side: Blender's own "clear field" ✕ inside the search box, then the plugin's "remove bone" ✕. They look the same and do different things (polish: drop the field's clear button or give remove another icon). | – |
| B3 | ok, 2 remarks | R Pinky: **Shares Bones With = "Own bones"** (the checklist said "empty"; "Own bones" is the UI's word for it), bones `f_pinky.01–03.R`. Remarks: (1) the dropdown offers every slot, the **other hand's fingers and the left thumb too**, for a right pinky; sharing across hands makes no sense (polish: list only same-hand slots). (2) Cut-off labels again at the default width: "Shares Bone…", "R Pinky: bon…", the bone names (step 6 P5). | – |
| C0 | setup change | Starting C, the user rotated the clarinet because the keys seemed to face the floor. The hold from step 6 was wrong for a clarinet: almost horizontal (26° below level) with the fingers over the back. Rebuilt from the user's reference photo by `scripts\hold_v2.py` (backup `midi_trial_pre_hold2.blend`): clarinet turned about the mouthpiece tip to **22° from vertical**, with the side the keys stick out on (measured from the mesh) facing forward; arms re-posed with the left hand on the upper joint and the right on the lower, palms beside the tube a little behind it, fingers round the front; a 25° preview curl on the fingers (Autoassign replaces it); **Lock** again (hands on targets 0.0 mm). Front and side renders next to the photo shown to the user. The tone holes then faced CJ's left side: the protrusion-based "keys side" was wrong (the side levers dominate it). Corrected in two turns about the tube axis: a quarter turn from the user's screenshot, then +90° found by measurement (front-on renders of the clarinet alone at −90…+90° in 15° steps; at +90° the tone holes run down the middle of the front). Final params in `scripts\hold_v2_params.json`. Hands re-posed toward true forward, Lock 0.0 mm. Observation for step 7: Hold has no way to say which side of the instrument faces forward; markers and Autoassign depend on it. | – |
| C1 | ok | 16 markers placed with the Cursor tool (Orientation **Geometry**; the checklist said *Surface*, Blender 5.2's name is Geometry) and the agent's marker guide page. Checked from the saved file: all 16 present, within 2 mm of the clarinet, every arrow pointing out. The user's first A / G# picks were re-placed after the guide. | 10 min |
| D1 | issue → tuned | **Autoassign**: "32 poses created; Rest pose: F.Rest", warnings cut in the middle of the status bar (only the first and last show; the full list needed a script). Measured every pose: middle/ring fingers 0–2 mm, but L Pinky E/B / F#/C# 33–50 mm (markers 8–12 cm below the hand, out of reach), L Thumb 13–29 mm, L Index A / G# 17–26 mm, index holes ~10 mm. Fixes by script (`scripts\tune_left.py`, backup `midi_trial_pre_tune_left.blend`): the two left-pinky markers moved up beside C#/G#; the left hand searched over grip height, how far round toward the back, wrist twist and tilt (≈350 Autoassign runs at 0.25 s), best kept. Result: worst 50 → **14.8 mm**, mean 6.7 mm; remaining ≥ 10 mm: thumb hole 14–15, A Down 14, G# Down 12, Register Up 12, pinky E/B Up 12. Findings for step 7: the status bar hides the middle of a long warning list; fingers that only curl can't roll up along the tube to the throat keys; the guide's "check the Bend Axis" isn't the cause when the hand is out of place. | 0.25 s per Autoassign |
| E1 | ok | **Fill: This File**: 21 notes, E3–A5. E3 = LT L1 L2 L3 L4(E/B) / R1 R2 R3, R4 up. Rest Pose = F.Rest. Cut-off labels in the finger grid ("L Thu…", "L Pi…", step 6 P5). | – |
| E2–E4 | ok, 1 remark | With the list enlarged, its summary column shows every fingering: B4 = "LT:Register L1 L2 L3 L4 \| R1 R2 R3" (the break), G4 = "open", A4 = "L1:A", G#4 = "L1:G#", D#4 adds "R1:Eb/Bb", C#5 "L4:F#/C#", G#5 "L4:C#/G#". All match the chart. Remark: a finger on its first key is shown bare ("L4" = L4:E/B, "LT" = LT:Hole), so the default key can't be read from the list. | – |
| F1 | ok | "Baked: 111 fingered notes; Chest ← CC2" (no unmapped notes, no missing poses). From the saved file: tracks `MIDI: Fingering`, `MIDI: Hand Poses`, `MIDI: Chest` on CJ's rig; every finger's base joint moves over the take; the thumb moves at `thumb.02`/`.03` (812° / 1214° summed), not at its base joint. | – |
| F2–F4 | ok (the user judges) | Played with audio. The user: the right fingers go down on the notes they know, the curls look natural enough, the thumb change (hole ↔ register) is visible. | – |
| G1 | ok | Severities confirmed with the user: **bad**: Hold can't say which side of the instrument faces forward; the status bar hides the middle of long warning lists; fingers can't roll along the tube (throat A/G#, thumb round the back). **polish**: miss advice always says "check the Bend Axis"; the Shares dropdown offers the other hand; two look-alike ✕ per bone row; every build is 1.0.0; the note list doesn't name a finger's first key. Cut-off labels = step 6 P5. | – |
| G2 | ok | Test-setup limits reviewed in the report. | – |
