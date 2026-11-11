---
step: 10
title: "Clarinet profile (B♭ Boehm)"
status: done
branch: plan/step-10-clarinet
pr: (set after opening)
commits: 8f9c9ad..(this report)
date: 2026-11-10
blender: 5.2.3 LTS, "C:\Program Files\Blender Foundation\Blender 5.2\blender.exe"
tests_core: 49 passed
tests_blender: ALL TESTS PASSED
decision_changes: none
---

# Step 10: Clarinet profile (B♭ Boehm)

## Summary
The Instrument dropdown now has **B♭ Clarinet** (`CLARINET_BB`) next to the sax. Its Boehm chart covers
written E3–C6 (52–84), one fingering per note. Each entry is the first ("Basic") fingering in the Woodwind
Fingering Guide, and it agrees with Izen's chromatic chart and with Powell's little-finger key chart. The
clarion register is the low fingering plus `LT:Register`, 19 semitones up, for every note B4–C6. The thumb has
three keys (hole, hole + register, register alone), so throat B♭4 differs from the clarion notes. Profiles have a
`default_transpose` (sax 0, clarinet +2). Switching instrument applies it if Transpose is still at the previous
instrument's default. The user's take is written E3–A5 with Transpose +2, all 21 pitches are mapped, and nothing
goes above C6, so there was no altissimo question. The independent (Gemini) cross-check gives the same fingering for
all 33 pitches; only key names differ (see *Cross-check*).

## Acceptance criteria
- [x] Sources listed, and every chart entry traceable to them (differences from a source explained): see
      *Sources* and *Chart*. `test_matches_source_table` parses the Woodwind Fingering Guide's notation for all
      33 pitches and asserts it equals the chart. Izen and Powell were checked by eye (images). The one difference
      from a source (Izen lists E3/B4 and F#3/C#5 first with the right pinky also holding F/C) is explained under *Chart*.
- [x] Every written note in the take (with Transpose +2) is mapped; tests pass: the take
      (`zelda_recorded_v1_b.mid`, 111 notes, read only) is written E3–A5, 21 pitches, all in the chart
      (`test_users_take_is_in_chart`). pytest: 49 passed. `test_in_blender.py`: ALL TESTS PASSED, including Fill,
      Autoassign and Bake on the clarinet. Validate: success.

## Sources
1. **Woodwind Fingering Guide** (T. Reichard), Boehm clarinet: key legend
   [cl_fing](https://www.wfg.woodwind.org/clarinet/cl_fing.html), basic charts
   [chalumeau E3–B♭4](https://www.wfg.woodwind.org/clarinet/cl_bas_1.html) and
   [clarion B4–C6](https://www.wfg.woodwind.org/clarinet/cl_bas_2.html). The primary source: it gives every
   fingering as text and marks the "Basic" one.
2. **J. M. Izen, *Clarinet Fingering Guide by Key***, chromatic fingering charts, © 1995
   ([mirror](https://dannychesnut.com/Music/Clarinet/Fingerings/Fingerings.html), `chart1.gif` chalumeau,
   `chart2.gif` clarion). Graphical, all notes E3–F6.
3. **Oxford University Press, Chapter 34 "Pedagogies for Teaching Clarinet", supplement "Learning about the
   Pinky or Little Finger Keys"** (companion material to Powell, 1st ed.;
   [docx](https://arc-next.oup-arc.com/protected/files/content/file/1689086899009-powell1e_clarinet_fingering_ch34.docx)).
   Its figures show the little-finger keys of each hand and which notes need which hand.

Not usable: Yamaha's fingering PDF and web page returned HTTP 403 to my fetch, the UNT chart returned 404. (The
cross-check agent did read Yamaha's chart; see *Cross-check*.)

## Slots and keys
Slot ids and order are the sax's (`LT`, `L1`–`L4`, `R1`–`R4`), so Detect Fingers results and bones carry over when
switching instrument. The right thumb only holds the instrument (no slot), as on the sax.

| Slot | Keys (`keys[0]` = home) | Why |
|---|---|---|
| `LT` L Thumb (register) | `Hole`, `Register`, `RegOnly` | The thumb plays three states: hole (E3–F4), hole **and** register key (all clarion notes, WFG `RT`), register key alone with the hole open (throat B♭4, WFG `R A`). One finger presses one marker, so "hole + register" is one combined marker, like the sax's `PalmEb`. It's named `Register` because that is what players add at the break. The plan suggested two keys; with two, B♭4 and the clarion notes would collapse into one state. |
| `L1` L Index | `Hole`, `A`, `G#` | The throat A key (index rolls up) and G# key (side of the index), as the plan says. |
| `L2`, `L3`, `R2`, `R3` | `Hole` | |
| `L4` L Pinky | `E/B`, `F/C`, `F#/C#`, `C#/G#` | All three sources put E/B, F/C, F#/C# on both little fingers, and the **C#/G#** key on the left only (C#4, G#5; the take plays G#5 once). The plan didn't list C#/G#; using `F#/C#` instead would press the wrong key. No left Ab/Eb: Powell marks it "not usual for beginning instruments", WFG "some models". |
| `R1` R Index | `Hole`, `Eb/Bb` | The lowest side key (WFG side key 4, the plan's `Side4`), pressed with the side of the index: D#4 and A#5. It's named after the notes it plays, like the little-finger keys. No other side key is in a basic fingering. |
| `R4` R Pinky | `F/C`, `E/B`, `F#/C#`, `Ab/Eb` | As the plan says. Home is `F/C`, where the right pinky rests in the chart. |

**Key names:** the plan suggested `Thumb` and `L1`/`L2`/… for the holes. That gives pose names like
`F.L1.L1.Down`, so every hole is `Hole` instead (`Key.L1.Hole`, `F.L1.Hole.Down`): the slot already says which
finger. Names with `/` and `#` (`F.L4.F#/C#.Down`) work: the e2e test creates, autoassigns and bakes them.

## Chart
Written pitch. Every note B4–C6 equals the note 19 below plus `LT:Register` (tested). "6 holes" = L1 L2 L3 R1 R2 R3 on `Hole`.

| Written | Combination | WFG basic | Izen (first listed) |
|---|---|---|---|
| E3 52 | LT:Hole, 6 holes, L4:E/B | `T 123E\|123` | left E + right F (second: left E alone) |
| F3 53 | LT:Hole, 6 holes, R4:F/C | `T 123\|123F` | same |
| F#3 54 | LT:Hole, 6 holes, L4:F#/C# | `T 123F#\|123` | left F# + right F (second: left F# alone) |
| G3 55 | LT:Hole, 6 holes | `T 123\|123` | same |
| G#3 56 | LT:Hole, 6 holes, R4:Ab/Eb | `T 123\|123G#` | same |
| A3 57 | LT:Hole, L1–L3, R1, R2 | `T 123\|12-` | same |
| A#3 58 | LT:Hole, L1–L3, R1 | `T 123\|1--` | same |
| B3 59 | LT:Hole, L1–L3, R2 | `T 123\|-2-` | same |
| C4 60 | LT:Hole, L1–L3 | `T 123\|---` | same |
| C#4 61 | LT:Hole, L1–L3, L4:C#/G# | `T 123C#\|---` | same |
| D4 62 | LT:Hole, L1, L2 | `T 12-\|---` | same |
| D#4 63 | LT:Hole, L1, L2, R1:Eb/Bb | `T 12-\|4---` | same (side key) |
| E4 64 | LT:Hole, L1 | `T 1--\|---` | same |
| F4 65 | LT:Hole | `T ---\|---` | same |
| F#4 66 | L1 | `1--\|---` | same |
| G4 67 | open | `---\|---` | same |
| G#4 68 | L1:G# | `G#---\|---` | same |
| A4 69 | L1:A | `A---\|---` | same |
| A#4 70 | LT:RegOnly, L1:A | `R A---\|---` | same (register, thumb hole open) |
| B4–C6 71–84 | the entry for 52–65 with `LT:Register` | `RT …` = the low entry with `R` added | same as WFG (the B4 and C#5 columns again list left + right F first) |

**The difference from Izen:** for E3/B4 and F#3/C#5, Izen's first diagram also holds the right pinky on F/C,
which helps a chromatic run to F/C. It lists the single-pinky fingering second. WFG lists that combination as an
option for slurs to F3/C5. The chart has one fingering per pitch, so it uses the plain one, WFG's basic.

**Pinky hands:** E/B and F#/C# left, F/C right (WFG's first-listed; Powell says either hand works for these
notes), so B4 → C5 → C#5 alternates hands.

**Throat tones and the break** (task 4), tested by value: F#4 `{L1: Hole}`, G4 `{}`, G#4 `{L1: G#}`,
A4 `{L1: A}`, A#4 `{LT: RegOnly, L1: A}`, B4 = E3 with `LT:Register`. The clarion rule holds for all 14 notes
B4–C6 in all three sources. It doesn't apply to F#4–A#4 (66–70): there are no notes 19 below them.

## Cross-check
The Antigravity (Gemini) agent's chart
(`…\scratch\step10-clarinet-chart-crosscheck.md`; sources: WFG, Yamaha's Boehm guide and PDF, UNSW Music
Acoustics) was compared with a script that maps its key names to ours (`Thumb`/`L1`/`R1`… → `Hole`,
`Side4` → `Eb/Bb`, `Register [+ LT:Thumb]` → `Register`, `Register` alone → `RegOnly`):
`33 rows compared, 0 differences`. Its four flagged points:

| # | Point | This chart | Result |
|---|---|---|---|
| 1 | C#4 / G#5 on the left-pinky `C#/G#` key, not `F#/C#` | `L4:C#/G#` (key added to L4) | agrees |
| 2 | Pinky defaults E/B left, F/C right, F#/C# left | same | agrees |
| 3 | Throat B♭4 (register only) vs clarion (thumb hole + register) | `LT:RegOnly` vs `LT:Register` (third thumb key) | agrees; nothing lost |
| 4 | D#4 / A#5 on the bottom right-hand side key | `R1:Eb/Bb` | agrees (name only: its `Side4`) |

Both found the take at written E3–A5, 21 pitches, with nothing above C6.

## Changes
| File | What changed |
|---|---|
| `midi_animator/core/profiles.py` | `Profile.default_transpose`. Presets moved to a shared `WIND_PRESETS` (sax unchanged). New `CLARINET_SLOTS`, `_clarinet_chart()` (docstring: sources, key meanings, pinky choice) and the `CLARINET_BB` profile ("B♭ Clarinet", +2). |
| `midi_animator/blender/props.py` | `profile` update callback: applies the new default Transpose if Transpose still equals the previous profile's default (hidden `transpose_profile`; "" = the sax), and refreshes listed finger slots. |
| `midi_animator/blender/rig.py` | `sync_finger_slots` also rebuilds when the labels differ (same ids, bones kept), so the list shows "L Thumb (register)". One line. |
| `tests/core/test_clarinet.py` | New, 10 tests: registry and defaults, full range and slot keys, register key placement, clarion rule, throat tones and break, the WFG source table (parser), the take's pitches, `combination_label`, timeline (G4 → A4 moves only L1; crossing the break). |
| `tests/test_in_blender.py` | `clarinet_checks()` at the end: Transpose follows the instrument (and is kept when the user changed it), labels and bones, markers + Autoassign (bend and tip checks), Fill: Whole Chart (52–84), Fill: This File + Analyze (only E6 unmapped), Bake (A4 and B4 frames carry the right poses). |
| `docs/aerophone-guide.md` | Instrument choice; Transpose defaults (+2, HUD Concert); Fill after switching; a **Clarinet keys** table (where to place each marker, which notes use it), the break, throat tones, pinky hands. |
| `CLAUDE.md` | Status: 49 core tests, clarinet profile. |
| `docs/plan/reports/step-10/clarinet_sidebar.png` | Screenshot: panels 1 and 3 with the clarinet selected (Blender 5.2.3, a window). |

## Verification
```
python -m pytest tests/core -q
49 passed in 0.19s

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup --python tests/test_in_blender.py
Info: 42 poses created; Rest pose: F.Rest
bend: max against the axis 0.000 deg, max on locked axes 0.000 deg, max tip-to-target distance (Down and Up) 2.28 mm
...
clarinet bend: against 0.000 deg, locked axes 0.024 deg, tip 0.40 mm
Info: Filled 33 notes
Warning: Filled 13 notes | not in the chart (map by hand): E6
Warning: Baked: 13 fingered notes; Cheeks ← CC2; Chest ← CC2 | unmapped notes: E6 | Missing: CC11 not in file — choose Use Velocity or Turn Off
clarinet checks passed
ALL TESTS PASSED

"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" --command extension validate midi_animator
Success parsing TOML in "midi_animator"
```
The sax numbers are unchanged from step 5 (42 poses, 0.000°, 2.28 mm). E6 is in the sample file with Transpose +2
and above the clarinet chart, so it is reported, not silently clamped.

Also checked:
- The take, read-only with the core parser: 111 notes, written E3 (52) to A5 (81), 21 pitches (E3 G3 G#3 A3 B3 D4 D#4
  E4 F4 F#4 G4 G#4 A4 B4 C5 C#5 D5 E5 F#5 G#5 A5).
- The "♭" in the dropdown renders: Inter has no ♭, but Blender's bundled fallback fonts (Noto Sans Symbols, Noto
  Sans Math, DejaVu Sans Mono) do (checked with fontTools), and the screenshot shows "B♭ Clarinet".
- UI with a window (`clarinet_sidebar.png`): Instrument "B♭ Clarinet", Transpose 2 after switching, the note map
  with B4 showing `Register`, `E/B` and the six holes pressed.

## Deviations from the plan or spec
- Key names: `Hole` for every hole (the plan said `Thumb`, `L1`, …), `Eb/Bb` for the side key (the plan's
  `Side4`), and two keys the plan didn't list: `LT:RegOnly` and `L4:C#/G#`. Reasons under *Slots and keys*.
- `rig.sync_finger_slots` changed by one line, so labels follow the profile. **Heads-up for step 11**, which works on
  the same function.
- The clarinet reuses the sax's blow presets (Cheeks, Chest) through `WIND_PRESETS`.
- Tests were written by a Traycer child agent (Sonnet, medium) per the user's agent guide; I reviewed them, made
  three small edits (an unused import, two names) and ran the verification.

## Decisions
No ADR. The chart and keys are profile data inside ADRs 0002/0003, and ADR 0012 already decided the clarinet profile
and its +2 default. Within the step: one fingering per pitch (WFG basic), three thumb keys, `C#/G#` on L4, pinky
hands as above, range E3–C6 (no altissimo; the take doesn't need it).

## Problems and risks
- **Labels cut off** in the default sidebar width in the note map's finger rows (`Regis…`, `RegO…`, `F#/…`, `C#/…`;
  see the screenshot). It's the same issue as step 7's confirmed label polish.
- **`Register` and `RegOnly` are close:** Autoassign only places the fingertip, so the two thumb poses differ only
  as much as the user places their markers apart (`RegOnly` a little higher, the thumb rolled off the hole). On CJ
  (no thumb) it doesn't show at all.
- **Switching instrument keeps the old note map.** Sax rows (`L1=B`, …) stay until Fill runs with *Overwrite
  Existing*. The guide says so, but nothing warns.
- **One fingering per pitch:** in the take, B4 → C#5 happens 4 times, and both use the left pinky (E/B → F#/C#),
  so the pinky slides. A player would take one of them with the right pinky.
- Cheeks preset on a clarinet: players don't puff their cheeks, and CJ has no CheekPuff anyway. Nothing changed.

## Follow-ups for the planner
- Add to step 12: place the clarinet markers from the guide's *Clarinet keys* table (put `RegOnly` a little above
  `Register`), and have the user confirm a few fingerings by eye, especially G#5 (`C#/G#`) and the break.
- Add to step 12: decide with the user whether B4 → C#5 should use the right pinky for one of them. If yes, it's the
  step 7 "alternate fingerings per note" candidate.
- Add to step 7: Analyze warns when note-map rows use keys that the current instrument's slots don't have (after
  switching instrument).
- Add to step 7's label polish: the clarinet key buttons in the note map (`Register`, `RegOnly`, `F#/C#`, `C#/G#`).
- Consider later: altissimo C#6–G6 (WFG `cl_bas_3` has them) if a take needs them; ask the user then.
- Consider: a Cheeks default closer to 0 for the clarinet (embouchure).

## Questions for the user
None asked. The take stays below C6, so there was no altissimo choice to make.
