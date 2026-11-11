# Aerophone GO → Blender: step by step

From a take on your Aerophone to a character that fingers the notes, puffs its cheeks,
breathes with its chest, and a note HUD you can lay over the video.

## 1. Record in Reaper

1. Enable the Aerophone under Options > Preferences > MIDI Inputs.
2. Record a track with input **MIDI > Aerophone GO > All channels**. Record the audio on a second track if you want it.
3. **Keep the breath data.** The Aerophone sends breath as CC2 by default. Don't quantize or thin the CC lane.
4. Export the MIDI (File > Export project MIDI…) and render the audio to WAV from the same start position.

## 2. Load the MIDI

**1. Instrument & MIDI**
1. Instrument: **Monophonic Wind / Brass** (saxophone fingering) or **B♭ Clarinet** (Boehm
   fingering, see [Clarinet keys](#clarinet-keys)).
2. Choose the .mid file and click **Analyze MIDI**. The report lists the tracks, the notes the
   performer plays, the controllers found (look for CC2), and anything still missing.
3. If the file has several tracks, click the dot next to the one you played.
4. **Transpose:** the fingering chart uses *written* pitch: the file's pitch plus Transpose.
   Choosing an instrument sets its usual Transpose: **0** for the sax (if the Aerophone is set to an
   alto or tenor key, it may already send written pitch) and **+2** for the B♭ clarinet (it sounds
   a tone below what is written, so a recorded concert D3 is the clarinet's written E3). If you
   changed Transpose yourself, switching instrument leaves it alone. If the fingers look shifted,
   set the difference in semitones here. The HUD can still show the recorded notes: set its
   Pitch to **Concert**.
5. **Fit Scene Range**, then choose the WAV and **Add Audio**.

## 3. Fingers and keys

**2. Fingers & Keys**
1. Set **Character Rig** and click **Detect Fingers**. Rigify, Mixamo and VRoid names are recognised.
   Fix any finger by picking its bones (root → tip). Detect Fingers also sets the **Bend Axis**
   (in the Autoassign box) from the way the fingers curl at rest; see step 5.
2. **Hold the instrument.** A real sax hangs from a neck strap at chest height, angled down and to
   the player's right, with the mouthpiece in the mouth and the bell near the right hip. The **left
   hand is on top** (thumb on the thumb rest and octave key; index, middle and ring on B, A and G).
   The **right hand is below** (thumb under the thumb rest; index, middle and ring on F, E and D).
   The pinkies hover over the side keys.
   1. Place the instrument at the lips, angled like that, and pose both arms and hands onto it,
      each finger lightly curled over its key.
   2. In the **Hold the instrument** box set **Instrument** (the sax body; the bell can stay its
      child) and click **Guess Bones**. Check the **Strap Bone** (an upper-chest bone, for example
      `mixamorig:Spine2` or Rigify's `spine.003`) and the two **Hand** bones.
   3. Click **Lock**. The instrument now hangs from the strap bone, and two small targets
      (`MIDI Hold L` and `MIDI Hold R`) keep the hands glued to it with IK wherever the body moves.
      To adjust the grip, move those targets. **Unlock** removes the targets and constraints (the
      instrument stays on the strap).
   The Chest breathing effect scales the chest bone but never the instrument or the arms: while
   locked, each upper arm's *Inherit Scale* is set to *None* (Blender's IK misses its target under
   a scaled parent), so the hands stay on their targets. **Unlock** puts the setting back.
3. **Place key markers.** Select a finger in the list. For each of its keys, put the 3D cursor on
   the key (or select the key's vertices in Edit Mode, and the marker's arrow follows their normal)
   and click **Place**. The arrow should point out of the key, toward where the finger lifts.
4. **Hover Height:** how high a lifted finger floats above its key.
5. Click **Autoassign Finger Poses**. Every finger is solved onto each of its markers (Down) and
   above it (Up) and saved as pose assets such as `F.L1.B.Down`.
   - Fingers only bend the way they curl: each joint turns around the **Bend Axis** and only
     in the curling direction, so no finger twists sideways or bends backwards (the knuckle may
     also spread a little to reach side keys). Rigify fingers curl around **X**; for other rigs
     click **Detect** next to it. If the rig's fingers are straight at rest, Detect can't tell:
     rotate one finger joint in Pose Mode to see which axis curls it, and pick that one
     (with a minus if the curl is a negative rotation).
   - **Keep Twist** (on by default) also stops the bones twisting around their own length.
   - If a fingertip can't reach its target this way, the status bar says which finger and key,
     and by how much. Move the marker within reach, check the Bend Axis, or curl the hand more
     in your hold pose.
   - Autoassign also builds **`F.Rest`**: every finger up over its home key (the first key in
     its list, for example B for the left index) and the hand bones as they are now. It becomes
     the **Rest Pose** if you haven't set one (see the Note Map).
6. Check a pose with the eye button. To fix one, apply it, tweak the bones, and update the pose
   asset. The pose locks itself and Autoassign won't overwrite it. You can also toggle the lock
   by hand, or tick **Overwrite Locked** to regenerate everything.
7. Optional: give a finger an authored **Up Pose** instead of hovering.

## 4. Note map

**3. Note Map**
1. **Fill: This File** maps every note in the take from the instrument's built-in chart (**Fill: Whole Chart**
   maps all of it: Bb3–F#6 for the sax, E3–C6 for the clarinet, written). Switched instrument? Fill again
   with **Overwrite Existing** ticked (in the operator's redo panel), or the old instrument's rows stay.
2. Click a note to see its fingers. Each finger row has `up` plus the keys it can press, so you can
   change any of them. Copy and paste fingerings between notes.
3. **Whole-hand Pose:** use a pose asset for that note instead of the combination (a trill shape, a gesture).
4. **Rest Pose:** the hand between phrases. Autoassign fills it with `F.Rest` (fingers up over
   their home keys). For your own, select the hand and finger bones in Pose Mode and use
   **Save Pose Asset** with "Use As: Rest Pose". Your own Rest Pose always wins: Autoassign still
   updates `F.Rest` but leaves your choice alone.
5. Timing: **Transition** (frames a finger takes to move), **Lift Lead** (frames lifting fingers
   leave early) and **Relax After** (rest length before the hand relaxes).

**High notes (palm and side keys).** One finger presses one marker, so keys that the hand
presses together share one marker. The top of the range uses these (written pitch, all with the
octave key, `LT:Octave`):

| Note | Left index (`L1`) | Right index (`R1`) |
|---|---|---|
| D6 | `PalmD` | up |
| D#6 | `PalmEb` | up |
| E6 | `PalmEb` | `SideE` |
| F6 | `PalmF` | `SideE` |
| F#6 | `PalmF` | `HighF#` |

Where to place each marker (on the instrument, arrow out of the key as usual):
- `PalmD`: on the palm D key, where the side of the left index presses it alone.
- `PalmEb`: where the left hand presses the palm D and Eb keys together, between the two.
- `PalmF`: where the left hand presses palm D, Eb and F together, between the three (closer to F).
- `SideE`: on the high E side key, where the side of the right index presses it.
- `HighF#`: where the right hand presses the side E key and the high F# key together, between the two.

You only need markers for the notes you play: a key without a marker gets no poses, and Bake lists
what is missing.

### Clarinet keys

The **B♭ Clarinet** chart is the standard Boehm fingering (17 keys, 6 rings), written E3–C6, one
fingering per note. The right thumb only holds the instrument (under the thumb rest), so it has no
slot. Place the markers like this (arrow out of the key or hole, as usual):

| Finger | Keys | Where to place the marker | Used for (written) |
|---|---|---|---|
| L Thumb (`LT`) | `Hole` | on the thumb hole (ring) at the back, where the thumb pad closes it | E3–F4 |
| | `Register` | where the thumb tip lands when it closes the hole **and** presses the register key above it | every clarion note, B4–C6 |
| | `RegOnly` | on the register key with the thumb rolled up off the hole | throat A#4 (B♭4) only |
| L Index (`L1`) | `Hole` | on the first left-hand hole | |
| | `A` | on the throat A key above that hole (the index rolls up onto it) | A4, A#4 |
| | `G#` | on the throat G# key beside that hole (the side of the index presses it) | G#4 |
| L Middle, L Ring (`L2`, `L3`) | `Hole` | on their rings | |
| L Pinky (`L4`) | `E/B`, `F/C`, `F#/C#` | on the left little-finger keys of those names | `E/B`: E3, B4; `F#/C#`: F#3, C#5 |
| | `C#/G#` | on the C#/G# key at the top of the left little-finger keys | C#4, G#5 |
| R Index (`R1`) | `Hole` | on its ring | |
| | `Eb/Bb` | on the lowest side key, where the side of the right index presses it | D#4, A#5 |
| R Middle, R Ring (`R2`, `R3`) | `Hole` | on their rings | |
| R Pinky (`R4`) | `F/C`, `E/B`, `F#/C#` | on the right little-finger keys of those names | `F/C`: F3, C5 |
| | `Ab/Eb` | on the Ab/Eb key, the top right little-finger key | G#3, D#5 |

- **The break:** the clarion register is the low (chalumeau) fingering plus the register key, a
  twelfth (19 semitones) higher: B4 is E3's fingering with `LT:Register`, C6 is F4's.
- **Throat tones:** from F#4 to A#4 the thumb leaves its hole. G4 is open (no finger down), G#4 and A4
  use the throat keys, and A#4 adds the register key alone (`RegOnly`).
- **Little fingers:** E/B, F/C and F#/C# exist on both hands. The chart plays E/B and F#/C# with the left
  pinky and F/C with the right, so B4 → C5 → C#5 alternates hands. For the other hand, change that finger in
  the note map and place a marker for that key.

## 5. Blow

**4. Blow**: click **Cheeks** (select the face mesh first) and **Chest**.

| Preset | Drives | Mode |
|---|---|---|
| Cheeks | `CheekPuff` shape key, 0 → 1 | **Direct**: follows the blow |
| Chest | chest bone, scale X+Z, +0 → +4% | **Lung**: full before a phrase, empties while you blow, refills in rests |

- **Source:** CC2 by default. If Analyze finds no CC2, the effect shows **Use Velocity** / **Turn Off**.
  It isn't baked until you choose. Velocity rises to the note's velocity and decays to **Sustain**.
- **Min / Max:** output at no blow and full blow (Lung: empty and full lungs). Rotations are in degrees.
- **Attack / Release:** how fast it follows. **Lung Capacity:** seconds of full blow that empty the lungs.
- Advanced: threshold, curve, normalize, blend, and a separate track/channel if the breath was recorded elsewhere.

## 6. Bake

**6. Bake > Bake MIDI to Animation.** The status bar lists what was baked and anything missing
(unmapped notes, poses not generated yet, blow sources you haven't decided on). Change something? Bake again.
Your rig's active action (for example an idle) moves to a `Base:` track underneath.

## 7. Note HUD

**5. Note HUD**
1. Tick the panel header to preview it in the viewport and scrub the timeline.
2. Size, look-ahead, hit-line position, names (written or concert, letters or Dó Ré Mi, sharps
   or flats) and colours.
3. **Export HUD** renders the scene's frame range to `hud_####.png` with transparency (pick ProRes
   4444 to also get a .mov with alpha). In DaVinci Resolve, drop the image sequence on a track above your video.
   If your Blender's FFmpeg can't write ProRes 4444, the export says so; the PNG sequence is still complete.
4. Or **Make Composite Scene**: a new scene that renders your scene with the HUD at the bottom. It uses
   your scene's colour management, so your render looks the same as when you render it directly. With the
   **Standard** or **ACES** view the HUD keeps its exact colours. With **AgX** (Blender's default) or
   **Filmic**, or with a Look, exposure, gamma or curves, Blender tones the HUD too (AgX makes the gold
   duller), and the operator warns you. For exact colours, overlay the exported PNGs in your editor.

Export needs Blender's UI (it draws with the GPU), not `blender -b`.

## Troubleshooting

- **The sax drifts away from the hands:** use **Lock** in the Hold box. Parenting it to the Armature object or to one hand doesn't keep both hands on it.
- **A finger doesn't move:** check its bones in panel 2 and that its markers exist, then run Autoassign. Bake lists missing poses.
- **The fingertip misses the key:** move the marker and run Autoassign again (unlock the pose if you edited it). If the status bar says "fingertip … mm off", check the **Bend Axis**.
- **Fingers bend backwards or sideways:** the **Bend Axis** is wrong for this rig. Click **Detect**, or pick it by hand, and run Autoassign with **Overwrite Locked**.
- **Wrong notes fingered:** adjust **Transpose**.
- **Cheeks don't move:** the effect's object must have the shape key. Check the status line for the blow source.
- **"CC2 not in file":** the export lost the CC lane, or the Aerophone sends breath on another controller (see Analyze's Controllers line).
