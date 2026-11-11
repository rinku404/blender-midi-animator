# MIDI Animator for Blender

A Blender 5.x extension that turns a recorded MIDI performance into character animation and a
note HUD. Built first for wind controllers such as the **Roland Aerophone GO**:

- **Fingering from finger combinations.** Each note is a set of finger states (up, or down on a
  key). Only the fingers that change move. Lifting fingers leave a little before pressing ones arrive.
- **Autoassign.** Place a marker on each key of the instrument and the extension solves each
  finger onto it with IK, saving **pose assets** (`F.L1.B.Down`, `F.L1.B.Up`, …). Poses you
  tweak are locked so Autoassign won't overwrite them.
- **Built-in saxophone and B♭ clarinet (Boehm) charts**, editable note by note, with optional
  whole-hand pose overrides. Each instrument sets its usual Transpose (B♭ clarinet: +2).
- **Blow (optional).** CC2 (or any CC, aftertouch or velocity) drives the cheeks directly and
  the chest through a **lung model**: it empties while you blow and refills in rests. If the
  file has no blow data, you choose: velocity or off.
- **Note HUD.** A Guitar-Hero-style highway: upcoming notes scroll to the hit line, the
  sounding note lights up and fills, the name pops. Preview it live in the viewport and export
  it as transparent PNGs (or ProRes 4444) to layer over your video.

Everything is baked into NLA tracks named `MIDI: …`, so you can re-bake at any time without
touching your own animation.

The design is in **[docs/SPEC.md](docs/SPEC.md)** (reasons in [docs/decisions/](docs/decisions/)) and the walkthrough in
**[docs/aerophone-guide.md](docs/aerophone-guide.md)**.

## Install

1. Zip the `midi_animator` folder (or download the release zip).
2. Blender > Edit > Preferences > Get Extensions > ▾ (top right) > **Install from Disk…** and pick the zip.
3. In the 3D Viewport press **N** and open the **MIDI** tab.

## Panels

| Panel | What it does |
|---|---|
| 1. Instrument & MIDI | Instrument profile, MIDI file, Analyze, performer track/channel, transpose, audio |
| 2. Fingers & Keys | Rig, Detect Fingers, bones per finger (or shared with another finger), key markers, **Autoassign**, locks |
| 3. Note Map | Fill from the chart, edit each note's fingers, whole-hand override, Rest pose, timing |
| 4. Blow | Cheeks and Chest presets or custom; source, target, Direct/Lung mode, range, smoothing |
| 5. Note HUD | Live preview, layout, names (written/concert, letters/solfège), colours, export |
| 6. Bake | Bake or clear everything |

## Layout

```
midi_animator/
  blender_manifest.toml
  core/        pure Python, no bpy: MIDI parser, blow signal, profiles + sax and clarinet charts,
               fingering timeline, rig name detection, HUD layout
  blender/     properties, operators, Autoassign, baking, HUD drawing, panels
tests/
  core/                 pytest, runs anywhere
  test_in_blender.py    end-to-end inside Blender
  hud_preview.py        renders HUD frames with Pillow to check the layout
```

## Development

```
python -m pytest tests/core
blender -b --factory-startup --python tests/test_in_blender.py
python tests/hud_preview.py examples/aerophone_sample.mid out/ 0.3 4.9
python tests/make_sample_midi.py          # regenerate examples/*.mid
```

## Roadmap

- Fingering diagram in the HUD.
- Key markers as instrument bones, so the instrument's keys animate too.
- Polyphonic (keyboard, guitar) and Percussion profiles; more fingering charts (flute, trumpet).
