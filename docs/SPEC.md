# MIDI Animator v1 — Design Spec

Agreed 2026-11-06. Turns a pre-recorded MIDI performance (e.g. a Roland Aerophone take) into
baked character animation (fingering + breath) and a Guitar-Hero-style note HUD.

## Platform & structure
- Blender **5.2** Extension (`blender_manifest.toml`, no `bl_info`).
- `core/` is pure Python (no `bpy`), tested with pytest:
  - `midi.py` — Standard MIDI File parser (format 0/1, tempo map, running status, SMPTE).
  - `signal.py` — blow signal: sampling, attack/release smoothing, threshold, curve,
    normalize, velocity fallback shape, Direct and Lung modes.
  - `profiles.py` — instrument profile registry; v1 ships *Monophonic Wind/Brass* (sax chart).
  - `fingering.py` — note → finger-combination resolution and per-finger key timeline.
  - `hud.py` — HUD layout maths (what to draw at time *t*).
- `blender/` is the thin layer: properties, operators, baking, drawing, UI.
- **Cut from v0.2:** model import / Rigify / bind panel, drum & piano note triggers (return
  later as Percussion / Polyphonic profiles). The bell is just an ordinary blow target.

## Instrument profiles
Dropdown backed by Python profile classes. A profile defines: finger slots, built-in
fingering chart, blow-effect presets, and overlap handling. Monophonic Wind/Brass: a note
ends where the next begins.

## Performer
One track/channel selection + **Transpose** at the top; per-effect override under Advanced.

## Fingers & keys
- Finger slots (sax): LH thumb (octave), LH index/middle/ring/pinky, RH index/middle/ring/pinky.
  RH thumb only supports the instrument.
- Bone chains auto-detected from common rig names (Rigify, Mixamo, VRoid); manual bone picker override.
- **Key markers:** Empties parented to the instrument, assigned to a finger, local +Z out of the key.
  Added at the 3D cursor or at the selected vertex.
- Finger state = **Up** or **Down on marker X**.
- **Up** = hover a set distance along the marker's Z; optional authored Up pose per finger.
- **Autoassign** temporarily solves IK onto each marker (Down) and its hover point (Up) and
  saves the visual result as a **pose asset** per finger × key × state.
- Generated poses carry a **lock**, set automatically when the user edits them; Autoassign
  skips locked poses unless forced.

## Note mapping
- Explicit per-note table. Each row = a finger combination (one combination may serve many notes).
- Bulk-fill from the built-in **saxophone chart**; fully editable.
- Optional per-note **whole-hand pose** override. Required **Rest** pose.
- Analyze lists notes in the file that have no mapping.

## Motion
- Only fingers whose state changes move.
- Pressing fingers arrive exactly at note onset over **Transition** frames; lifting fingers
  leave **Lift Lead** frames earlier (parameter, default 1; 0 = all together).
- Short rests hold the fingering; rests longer than **Relax After** go to Rest.

## Blow (optional)
- Source per effect: **CC2** default; any CC, channel aftertouch, or velocity.
- If the chosen CC is absent, Analyze offers **use velocity** or **off** — never silent.
- Velocity shape: rise over attack → decay to **Sustain** (default 0.6) while held → release.
- Target picker: Object → Shape Key | Bone → Channel | Property (raw data path under Advanced).
- Per effect: min/max, attack/release, threshold, curve, normalize, blend.
- **Mode:** Direct (Cheeks default) or **Lung** (lung volume drains with integrated blow,
  refills during rests; Chest default).

## Baking
Into `MIDI: …` NLA tracks, re-bakeable; the user's active action is pushed to a `Base:` track.

## HUD
- Horizontal highway: notes scroll right→left to a hit line; pitch on the vertical axis;
  bar length = duration.
- On hit: bar lights up, note name pops at the hit line, bar fills while held; played bars
  show how long the note lasted.
- Names: **written pitch** default (after Transpose); options: concert pitch, sharps/flats,
  letter names / solfège.
- Settings: look-ahead (3 s), resolution, position/scale, pitch range (auto-fit), colours
  (upcoming / active / played), font size, semitone lines.
- Same drawing code drives the **live viewport preview**, **PNG-with-alpha export**
  (ProRes 4444 optional), and an in-Blender composite option.

## Later
Fingering diagram in the HUD, external pose libraries, instrument key animation
(key markers as bones), polyphonic and percussion profiles, more fingering charts.
