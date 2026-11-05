# MIDI Animator for Blender

A Blender add-on that turns a MIDI recording into character animation. It's built first for
wind controllers like the **Roland Aerophone GO**:

- **Fingering:** a built-in saxophone fingering chart. You pose each finger pressing its key once,
  and every note presses exactly the right fingers while the others rest on their keys. Octave key,
  low notes and palm keys are included.
- **Hold:** hang the instrument from a chest bone and lock both hands to it with IK.
- **Breath:** the breath signal in the recording (auto-detected) puffs the cheeks, grows the
  instrument's bell, lifts the chest and sways the body. Each effect has its own range, smoothing and curve.
- **Note triggers:** a generic "play this action when these notes play" mode, for drums, piano and so on.

Everything is baked as NLA tracks named `MIDI: …`, so you can change settings and bake again at
any time without touching your own animation.

Tested with Blender 5.2. It's written to work from Blender 4.2 on.

## Install

1. Download `midi_animator.py`.
2. In Blender, go to Edit > Preferences > Add-ons, open the dropdown (top right), choose **Install from Disk…** and pick the file.
3. Enable it, then in the 3D Viewport press **N** and open the **MIDI** tab.

## Quick start (Aerophone)

1. Record in Reaper and export the MIDI and the audio ([guide](docs/aerophone-guide.md#1-record-in-reaper)).
2. Import your character and instrument.
3. Sculpt a `CheekPuff` shape key on the face, and split the bell into its own object.
4. Pose the hold and click **Lock Hands to Instrument**. Then save Rest and the 10 finger presses with **3. Fingering > Save**.
5. Load the MIDI, click **Analyze MIDI** and check that no poses are missing.
6. In **4. Breath Effects**, click Cheeks, Bell, Chest and Sway.
7. Click **Bake** and press play.

The full walkthrough is in **[docs/aerophone-guide.md](docs/aerophone-guide.md)**.

## Panels

| Panel | What it does |
|---|---|
| 1. Models & Rigs | Import FBX/GLB/OBJ/USD into its own collection, add a Rigify metarig, bind meshes with automatic weights. Hold the Instrument: strap bone and hand IK lock |
| 2. MIDI & Audio | Load the .mid file, analyze it (tracks, note range, breath controller, missing poses), fit the scene range, add the audio |
| 3. Fingering | Choose the rig and the mode (per-finger sax chart, or whole-hand poses), save or load poses, set transpose, octave key, transition and the "relax after" time |
| 4. Breath Effects | Cheeks, Bell, Chest and Sway presets, plus custom effects. Each has a source, target, min/max, attack/release, threshold, curve and blend mode |
| 5. Note → Action Triggers | One-shot, stretch or loop actions per note or note range, with hit-frame alignment and velocity → influence |
| 6. Bake | Bake everything or clear it. With "Keep Active Actions as Base" on, an idle animation becomes a base layer under the MIDI tracks |

## Development

```
python tests/make_sample_midi.py          # regenerate examples/*.mid
python tests/test_in_blender.py           # with `pip install bpy==5.2.*` (Python 3.13)
python tests/test_chart_and_hold.py
blender -b --factory-startup --python tests/test_in_blender.py
```

## Roadmap

- Animate the instrument's own keys from the same fingering data.
- Live MIDI input for previewing.
- Drum kit and piano presets.
