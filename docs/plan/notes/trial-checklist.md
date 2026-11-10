# Step 6 trial checklist

Walk one line at a time in Blender's UI. For each line the agent records **result** (ok / issue / skipped),
a note, and a timing where marked ⏱. Expected results come from `docs/aerophone-guide.md`.
Sections follow the guide.

Files: character .blend, MIDI take, audio take (paths are recorded in the report).

## A. Load and analyze (guide §2)
| # | Action | Expected |
|---|---|---|
| A1 | Open the character .blend; enable the extension if needed; open sidebar tab MIDI | Panels 1–6 visible |
| A2 | Instrument = Monophonic Wind / Brass; choose the .mid; **Analyze MIDI** | Report lists tracks, note range, controllers incl. CC2 |
| A3 | Pick the played track (dot) if several | Note count matches the take |
| A4 | Note the lowest and highest written pitch in the report | Inside Bb3–F#6; if not, Transpose is needed |
| A5 | **Fit Scene Range**, choose the WAV, **Add Audio** | Range matches the take; audio strip present |

## B. Fingers (guide §3, steps 1)
| # | Action | Expected |
|---|---|---|
| B1 | Set Character Rig, **Detect Fingers** | All 10 fingers found (thumbs included); list the slots that are wrong |
| B2 | Rig family: Rigify / Mixamo / VRoid / other? Record bone names for one finger | – |
| B3 | Bend Axis after Detect; is the thumb's curl axis different from the fingers'? | One axis for four fingers; thumb may need a per-finger override (step 4 follow-up) |

## C. Hold the instrument (guide §3, step 2)
| # | Action | Expected |
|---|---|---|
| C1 | Place the sax at the lips, angled down/right; pose both hands on it | Left hand on top, right below |
| C2 | Set Instrument; **Guess Bones** | Strap bone = upper chest; hands = `hand_fk` on Rigify. Record what it guessed |
| C3 | **Lock** | Targets `MIDI Hold L/R` appear; hands follow wherever the body moves |
| C4 | Rigify only: toggle IK/FK switch on the arms | Lock does not fight the switch; record behaviour |
| C5 | Rigify only: check `upper_arm_fk` Inherit Scale = None while locked; **Unlock** restores it | As described |
| C6 | Hand accuracy: with Chest breathing active, measure/inspect drift of the hands vs. the sax | ~0 mm (step 4 measured 0.000 mm on the test rig) |
| C7 | **Unlock**, then **Lock** again | Clean round trip |

## D. Key markers (guide §3, step 3–4)
| # | Action | Expected |
|---|---|---|
| D1 | ⏱ Place all markers for the keys the take uses (record count and total minutes) | One click per key; arrow points out of the key |
| D2 | Place `HighF#`, `PalmD`, `PalmEb`, `PalmF`, `SideE` using the guide's table (if the take reaches them) | Markers exist for D6–F#6 |
| D3 | Set Hover Height | Lifted fingers float at a believable height |

## E. Autoassign (guide §3, step 5–7)
| # | Action | Expected |
|---|---|---|
| E1 | ⏱ **Autoassign Finger Poses** | Poses `F.<slot>.<key>.Down/Up` and `F.Rest` created; time recorded |
| E2 | Record every status-bar message "fingertip … mm off" (finger, key, mm) | Ideally none; if misses, is the cause the knuckle needing to extend past rest (step 7 can allow ~10°)? |
| E3 | Look at **every finger** (eye button on each Down and Up pose) | Fingertip on the key; no sideways twist; no backward bend |
| E4 | Do curls look natural, or does only one joint bend? | Spread over joints; note if mostly one joint (step 7 polish candidate) |
| E5 | F.Rest looks right (fingers hovering over home keys) | Becomes the Rest Pose |

## F. Note map (guide §4)
| # | Action | Expected |
|---|---|---|
| F1 | **Fill: This File**; click a few notes | Fingers/keys per row look right |
| F2 | The player confirms: low C#4 fingering | Fixed in step 5 (was wrong in v1) |
| F3 | The player confirms: F#6 (left `PalmF`, right `HighF#`) and D6–F6 | Matches the player's real fingering |
| F4 | Fill: Whole Chart | Bb3–F#6 mapped |

## G. Blow (guide §5)
| # | Action | Expected |
|---|---|---|
| G1 | Select face mesh; **Cheeks** | `CheekPuff` shape key found (or message says why not) |
| G2 | **Chest** | Chest bone found |
| G3 | Source shows CC2 from the real take | No Use Velocity/Turn Off prompt |
| G4 | Tune Attack / Release / Lung Capacity if needed (record values) | – |

## H. Bake and playback (guide §6)
| # | Action | Expected |
|---|---|---|
| H1 | ⏱ **Bake MIDI to Animation** | Status lists baked items and anything missing; record time |
| H2 | Play the timeline with audio | Fingers match the notes in time with the sound |
| H3 | Inspect NLA | `MIDI: …` tracks; your previous action under `Base: …` |
| H4 | Cheeks puff and chest breathes with the blow | Visible, in time, not extreme |
| H5 | Hands stay on the sax during the whole take | No drift |

## I. HUD (guide §7)
| # | Action | Expected |
|---|---|---|
| I1 | Enable HUD preview, scrub | Notes scroll; names correct (written vs concert) |
| I2 | ⏱ **Export HUD** for 10 s (PNG, ProRes 4444) | Files written; record time and any warning |
| I3 | Overlay the exported HUD on the real take in DaVinci Resolve | Transparent, correct colours, aligned |
| I4 | **Make Composite Scene** with the user's own scene (AgX) | Render exact; warning about toned HUD; the user judges the look |

## J. Overall
| # | Question |
|---|---|
| J1 | Anything awkward or confusing in the UI or the guide? |
| J2 | Rate each issue found: blocker / bad / polish (the user confirms) |
