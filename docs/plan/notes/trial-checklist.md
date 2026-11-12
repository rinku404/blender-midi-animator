# Step 6 trial checklist: pipeline on CJ + clarinet

Target (ADR 0012): CJ (`carl_johnson_cj.glb`) playing a B♭ clarinet. **Pipeline only**: marker placement, Autoassign
quality, Fill From Chart judgement, palm/side keys, thumb bend axis and curl naturalness are skipped (step 12).

Files (copies; originals untouched), project `D:\3D\blender_projects\midi_trial\`:
`midi_trial.blend`, `src\zelda_recorded_v1_b.mid`, `src\zelda_recorded_v1_B.wav`.
Settings: **Transpose +2**, **HUD pitch display: Concert**.

Each line records result (ok / issue / limit / skipped), a note, and a timing where marked ⏱.
Findings go to one of two tables: **plugin issue** or **test-setup limit**.

## A. Load and analyze (guide §2)
| # | Action | Expected |
|---|---|---|
| A1 | Open `midi_trial.blend`, enable the extension, open sidebar tab MIDI | Panels 1–6 visible |
| A2 | Instrument = Monophonic Wind / Brass; choose the .mid; **Analyze MIDI** | Tracks, 111 notes, MIDI 50–79, CC2 listed |
| A3 | Set **Transpose = +2** | Written range E3–A5 (record how many notes fall outside the sax chart Bb3–F#6; expected/noted only) |
| A4 | **Fit Scene Range**, choose the WAV, **Add Audio** | Range ≈ 54.4 s at 24 fps; audio strip present |

## B. Detect Fingers on CJ (for step 11)
| # | Action | Expected |
|---|---|---|
| B1 | Set Character Rig = CJ armature, **Detect Fingers**; record the message and which slots fill | Rebuilt hands (S5): "Found all 9 fingers; Bend Axis X", slots L1–L4, LT, R1–R4 with the `f_*` / `thumb.*` bones. The original rig found nothing (`{}`, script run; S1, step 11) |
| B2 | Clear one slot (L1) and fill it by hand, root → tip, `f_index.01.L` / `.02.L` / `.03.L`; record how the UI copes | Works |
| B3 | **Detect** Bend Axis; record the result | X |
| B4 | Which bone could act as a thumb? | Answered by the rebuild: `finger 1a-c` became the thumb (S5); the new chain is `thumb.01-03` |

## C. Hold the instrument (guide §3 step 2)
| # | Action | Expected |
|---|---|---|
| C1 | Place the clarinet at CJ's lips, pointing down and forward; pose both hands on it | – |
| C2 | Set Instrument; **Guess Bones**; record the guesses | Script prediction: strap `spine lower_011`, hands empty (names `wrist`, not `hand`) |
| C3 | Pick Strap Bone (`spine upper_013`) and the two Hand bones (wrists) by hand | – |
| C4 | **Lock** | Targets appear; hands follow when the body moves |
| C5 | Rotate/move the spine; check the hands stay on the clarinet | Hands glued |
| C6 | **Unlock**, then **Lock** again | Clean round trip |

## D. Blow (guide §5)
| # | Action | Expected |
|---|---|---|
| D1 | **Chest** preset on the chest/spine bone | Source CC2, Lung mode |
| D2 | Cheeks: sculpt a `CheekPuff` shape key on the head (guide §3) or log as a test-setup limit | – |
| D3 | Hand accuracy against the clarinet while the chest breathes (hands vs. targets, mm) | ~0 mm |

## E. Bake and playback (guide §6)
| # | Action | Expected |
|---|---|---|
| E1 | ⏱ **Bake MIDI to Animation**; record the status line (unmapped notes with the sax chart are expected) | Tracks `MIDI: …` created |
| E2 | Play with audio | Chest breath follows the real CC2 in time |
| E3 | Inspect NLA | `MIDI: …` tracks; user action under `Base: …` |

## F. HUD (guide §7)
| # | Action | Expected |
|---|---|---|
| F1 | Enable HUD preview; set pitch display **Concert**; scrub | Note names show concert pitch (lowest note D3) |
| F2 | ⏱ **Export HUD** for 10 s (PNG + ProRes 4444) | Files written; record time and warnings |
| F3 | Overlay the exported HUD on the take in DaVinci Resolve | Transparent, aligned |
| F4 | **Make Composite Scene** with the user's AgX scene | Render exact; toned-HUD warning; the user judges |

## G. Wrap-up
| # | Action |
|---|---|
| G1 | Review the **Plugin issues** table with the user; confirm severities |
| G2 | Review the **Test-setup limits** table |

## Walk-through log
Blender 5.2.3; extension built from `plan/step-06-trial` @ `378f3e9` (`midi_animator-1.0.0.zip`, validate OK) and
installed with Install from Disk; file `midi_trial.blend` = hand pass 5 (see report S5). Started 2026-11-10 23:52.

| # | Result | Note | ⏱ |
|---|---|---|---|
| A1 | ok | Panels 1–6 visible (1 Instrument & MIDI, 2 Fingers & Keys, 3 Note Map, 4 Blow, 5 Note HUD with enable box, 6 Bake). The file opened with state saved in it: MIDI `D:\Music\…_v1_a.mid` (track A, the original folder), audio `…_v1.wav` (both tracks), Character `Object_3`, Hold instrument and key-marker instrument `Clarinet`, all 9 finger slots filled with the rebuilt bones, Bend X. At the default sidebar width many labels are cut (`Instrum…`, `Charact…`, `Ho… 0.012 m`, `Bend…`, `Overwrite Loc…`, `Preview… 0.50`, `Label … 0.07`, `Now Pl… 0.17`, `Output …`, and the hint lines). HUD output `//hud/` is drawn red. | 13 min wall, mostly building/installing the zip and restoring the viewport (Local View) |
| A2 | ok | Analyze: "111 notes, 54.4 s, 1 tracks"; performer "0: Track 0 · ch 1 · 111 notes · D3–G5" (= MIDI 50–79); controllers CC2 (2765), CC11 (2…); a warning "Unmapped notes…, D5, E5, F#5, G5" (Note Map still empty). The HUD preview appears in the viewport right away (G4 at 0.0 s). The summary lines are cut at the default sidebar width (`written D3–…`, `CC11 (2…`, `Unmapped notes…`), so the full controller and unmapped lists can't be read. "1 tracks" (plural). | – |
| A3 | issue | Setting Transpose = +2 updates the HUD preview right away (G4 → A4, D4 → E4), but the text summary stays stale (`written D3–…`, `Unmapped notes… D5, E5, F#5, G5`) until **Analyze MIDI** is clicked again. After re-analyzing: "Performer: 111 notes, written E3–A5" and "Unmapped notes…E5, F#5, G#5, A5" (performer line stays concert "D3–G5"). Both MIDI and audio paths remain pointed at `D:\Music\…_v1_b.mid` and `…_v1_B.wav` (originals, read-only). | – |
| A4 | ok | Fit Scene Range: End 1331 (Start 1). The MIDI is 54.417 s, so the music ends at frame 1307 at 24 fps; the operator adds a 1 s (24-frame) tail. Add Audio: status bar "Added MIDI Audio"; playing from frame 1, the clarinet is heard. Audio is `D:\Music\…_v1_B.wav` (original, read-only). | – |
| B1 | ok | Rig `Object_3`; **Detect Fingers** reports all fingers found (the user read "found all fingers"; the Bend Axis part of the message and the slot contents were not read back; B2 and B3 cover them). On the original rig Detect finds nothing (script run, S1; step 11). | – |
| B2 | ok | L Index cleared with the X buttons and refilled with **Add Bone** + the bone search: `f_index.01.L`, `.02.L`, `.03.L`, root → tip. The user: "everything works as expected"; nothing awkward reported. | – |
| B3 | ok | **Detect** (Bend Axis): field stays X; the user didn't read back the message. The headless run gives "Bend Axis X" with no fingers on another axis. Side note: the Key markers **Instrument** and the Hold **Instrument** are one property; the user asked which object to pick, because the list also shows the import's in-between empty `10373_Clarinet…` and CJ's `CarlJohnson-GTASA.FBX`. Answer: `Clarinet` (the root). | – |
| B4 | skipped | Answered by the hand rebuild (S5). | – |
| C1 | ok (partly by script) | The user placed the clarinet by hand: mouthpiece at the lips, pointing down and forward, about 26° below horizontal. Then the user asked for the arms to be posed by script (`scripts\pose_arms.py`): upper arm and forearm by a two-bone solve, wrist turned so the palm faces the clarinet, left hand at 30% of the length and right hand at 58%, fingers left straight. Saved into `midi_trial.blend`; the clarinet-only state is kept as `midi_trial_c1_before.blend`. Along the way the user pressed **Autoassign** (0 poses + warning, as expected with no key markers) and asked which object goes in the **Instrument** field. Both point to guide gaps: the guide doesn't say how to pose the arms, or that Autoassign needs markers first. | not representative (arms by script) |

From here the user asked the agent to go on alone. C2–F2 ran headlessly (Blender 5.2.3, `-b`) with the plugin's own
operators from `plan/step-06-trial` code: script `scripts\trial_c_to_f.py`, raw numbers in `scripts\trial_c_to_f.json`,
operator messages in `scripts\trial_c_to_f.log`. Because of that, these lines say nothing about the UI. The saved file had
Transpose 0, so the script set it back to +2.

| # | Result | Note | ⏱ |
|---|---|---|---|
| C2 | ok (as predicted) | "Not found, pick by hand: left hand, right hand". Strap guessed `spine lower_011` (the lowest spine bone, not the upper chest). | – |
| C3 | ok | Strap `spine upper_013`, hands `arm left wrist_041` / `arm right wrist_051`. | – |
| C4 | **issue → setup fix S8** | On CJ's rig as imported, **Lock moves both hands 389.7 mm** off the clarinet. The forearm IK puts the forearm bone's *tail* on the target (0.0 mm), but CJ's FBX bone tails point sideways and end 39 cm from the wrist. Moving the IK onto the hand bone (`use_tail` off) gives the same 389.7 mm, because Blender's IK still treats the forearm tail as the joint. After S8 (arm bone tails moved onto the next joint), Lock moves the hands 0.0 mm, targets 0.0 mm / 0.0°, clarinet 0.0 mm. Lock 0.014 s. | – |
| C5 | ok (after S8) | Spine middle +15° X, spine lower +20° Z, hips +10° Y: the hands stay on their targets at 0.0 mm while the clarinet moves 174 / 46 / 111 mm with the body. Before S8 the hands were 389.7 mm off throughout. | – |
| C6 | ok | Unlock: "Removed 4 hold constraints", targets deleted, hands back to the pre-Lock pose (0.0 mm), clarinet stays on its strap. Lock again: 0.0 mm. | – |
| D1 | ok, 1 remark | Chest preset: CC2, Lung, Scale XZ 0–0.04, Combine, but on bone `spine lower_011` (the "spine" keyword fallback takes the lowest spine bone), so the whole upper body, head included, swells by up to 4 %. Status "uses CC2". | – |
| D2 | limit (S2) | No mesh in the file has shape keys, so no `CheekPuff`. Not sculpted. | – |
| D3 | ok | Over the whole take (every 3rd frame) with the chest breathing: hands vs targets at most 0.8 mm (L) / 0.9 mm (R), 0.0°. Chest scale 1.00–1.04. | – |
| E1 | ok | "Baked: 0 fingered notes; Chest ← CC2 \| unmapped notes: E3, G3, G#3, A3, B3, D4, D#4, E4, F4, F#4, G4, G#4, A4, B4, C5, C#5, D5, E5, F#5, G#5, A5" (Note Map empty: expected). | 0.02 s |
| E2 | **issue (P8)** | The user: "it moves, but I don't think it's realistic". Measured: Lung mode inhales only when the blow falls under 2 %, which happens **once** in this take (9.6 s, 0.33 s). From 24.5 s the lungs sit empty for the remaining **31 s**, so the chest stops moving. The take has 7 note gaps > 0.15 s (up to 0.65 s) that a player would breathe in. The user suggests a breath model that refills according to the air the phrases need and follows a breathing pattern. | – |
| E3 | ok | `Object_3` NLA: track `MIDI: Chest` (strip Chest, Combine, frames 1–1332). No `Base: …` track because CJ had no active action. | – |
| F1 | ok (script) | Pitch display Concert: the lowest note shows **D3** (written E3). The viewport preview itself still needs a look in the UI. | – |
| F2 | ok | Export 10 s (frames 1–240) as ProRes 4444: 240 RGBA PNGs 1920×360 + `hud.mov` (36.6 MB) in `midi_trial\hud\`. Headless export needs `gpu.init()` first (a script matter, not a user one). | 19.9 s |
| F3 | skipped | The user edits video in Blender (Make Composite Scene, F4), not in an external editor. | – |
| F4 | ok (simulated; the user judges the look) | The user chose a simulation: a copy `midi_trial_f4_agx.blend` with the AgX view transform (script `scripts\f4_composite.py`, Workbench, 50 %, frame 120; the file has no camera, so the script added one). AgX: "Created scene 'Scene + HUD'. The HUD colours are toned by this scene's view transform 'AgX'. For exact colours, overlay the exported PNGs or ProRes on your render in a video editor". Outside the HUD band, the composite matches the scene rendered alone to 1/255. The HUD sits at the bottom with its translucent panel. Control under Standard: no warning, same 1/255 match. | – |
| F1 (preview) | ok | The user checked it in the UI: "it's all correct" (Concert, letters, sharps, default sizes). The `//hud/` Output field is drawn red although the folder exists; Blender's own path display, not the plugin (cosmetic, unexplained). | – |
| G1 | ok | The user confirmed every severity as proposed: P1, P3, P8 *bad*; P2, P4–P7, P9 *polish*. | – |
| F4 (UI) | ok | The user ran it in the UI on `midi_trial_f4_agx.blend`: added a camera, Make Composite Scene, F12 on frame 120 of `Scene + HUD`. The first renders were black: the file has no World and no lights (S11), not a plugin problem. With a World and a sun: CJ renders, the HUD sits at the bottom, CJ shows through its panel; AgX tones the HUD slightly, as warned. | – |
| G2 | ok | Test-setup limits S1–S11 reviewed in the report. | – |

## Skipped (step 12)
Marker placement, Autoassign, Fill From Chart judgement, palm/side keys, thumb bend axis, curl naturalness, sax F#6/C# checks.
