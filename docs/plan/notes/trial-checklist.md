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
| A3 | Set **Transpose = +2** | Written range E3–G6 (record how many notes fall outside the sax chart Bb3–F#6; expected/noted only) |
| A4 | **Fit Scene Range**, choose the WAV, **Add Audio** | Range ≈ 54.4 s at 24 fps; audio strip present |

## B. Detect Fingers on CJ (for step 11)
| # | Action | Expected |
|---|---|---|
| B1 | Set Character Rig = CJ armature, **Detect Fingers**; record the message and which slots fill | Script prediction: nothing found (names `finger 1a_045` contain no thumb/index/… words) |
| B2 | Fill one finger by hand (root → tip) from `arm left finger 2a/2b/2c`; record how the UI copes | Works |
| B3 | **Detect** Bend Axis; record the result | – |
| B4 | Which bone could act as a thumb? | `finger 1a-c` leaves the wrist toward -Y/-Z (thumb-like); `finger 2a-c` runs along the hand. Confirm by eye |

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

## Skipped (step 12)
Marker placement, Autoassign, Fill From Chart judgement, palm/side keys, thumb bend axis, curl naturalness, sax F#6/C# checks.
