# Aerophone GO → Blender: step by step

This guide takes you from playing your Aerophone to a rendered character that fingers the notes,
puffs its cheeks and makes the bell swell with your breath.

## 1. Record in Reaper

1. Connect the Aerophone GO over USB, or Bluetooth MIDI on a Mac. In Reaper go to
   Options > Preferences > MIDI Inputs and enable the Aerophone. If you also want its sound, set up
   the audio input under Options > Preferences > Audio > Device.
2. Make a track, set its input to **MIDI > Aerophone GO > All channels**, arm it and record.
   If you want to hear the Aerophone's own sound, record a second track with its audio.
3. **Keep the breath data.** The Aerophone sends breath as a continuous MIDI controller (usually
   CC2, or CC11/aftertouch depending on its settings). Reaper records it along with the notes, and you
   can see it in the MIDI editor's CC lane. Don't quantize or thin it.
4. Export the MIDI: select the item, then File > Export project MIDI… (or right-click the item >
   Source properties > Export to new MIDI file).
5. Export the audio: File > Render… to a WAV file, starting at the same project position as the MIDI.

If the two exports start at the same time, Blender's **Start Frame** puts them in sync. Use
**Offset (s)** to fix any small lag.

## 2. Bring in the character and the instrument

- **1. Models & Rigs > Import Model** brings in a rigged FBX or GLB (Mixamo, VRoid, Auto-Rig Pro…).
  Each file goes into its own collection.
- Rig it if it isn't rigged: **Add Rigify Human Metarig**, fit the bones, then Armature tab > Generate
  Rig. Select the mesh, shift-select the rig, then click **Bind Selected Meshes to Rig**.
- **Hold the instrument:** see the next section.

## 2b. Hold the sax like a player

A real alto or tenor sax hangs from a neck strap at chest height. It angles down and to the
player's right, with the mouthpiece in the mouth and the bell near the right hip. The **left hand
is on top**: the thumb is on the thumb rest and octave key, and the index, middle and ring fingers
rest on the B, A and G keys. The **right hand is below**: the thumb hooks under the thumb rest, and
the index, middle and ring fingers rest on F, E and D. The pinkies hover over the side keys.

1. Place the sax: mouthpiece at the lips, angled as described above.
2. Pose both arms and hands onto it, with each finger lightly curled over its key.
3. Open **1. Models & Rigs > Hold the Instrument**. Set the Rig and the Instrument (the sax
   body; the bell can stay its child), then click **Guess Bones**. Check the Strap Bone (a chest
   bone, for example `Bip01_Spine2`) and the two Hand bones. On a Rigify rig the hands should be
   the IK controls `hand_ik.L` and `hand_ik.R`, with the arms in IK mode (the default), and the lock pins those controls.
4. Click **Lock Hands to Instrument**. The sax now hangs from the chest bone, and two small
   targets (`MIDI Hold L` and `MIDI Hold R`) keep the hands glued to it with IK, wherever the body moves.
   To adjust the grip, move those targets. The unlock button removes the lock.

## 3. The cheek puff shape key

1. Select the face or body mesh. In Object Data Properties > Shape Keys, click **+** twice to get
   `Basis` and a second key. Rename the second one exactly **`CheekPuff`**.
2. With `CheekPuff` selected, go into Sculpt Mode. Use the **Inflate** or **Grab** brush on both
   cheeks, with X symmetry on, until they look fully blown.
3. Back in Object Mode, slide the value from 0 to 1 to check it. The add-on animates this value.

## 4. Make the bell its own object

1. Select the instrument and go into Edit Mode. Select the bell faces (L over them, or box select), then
   press **P > Selection**. The bell is now a separate object.
2. Put its origin where the bell joins the body, so it grows outward from there. Snap the 3D cursor
   to the joint (select a vertex there, then Shift+S > Cursor to Selected). Back in Object Mode, use
   Object > Set Origin > Origin to 3D Cursor.
3. Parent the bell to the instrument body: select the bell, shift-select the body, then Ctrl+P > Object.

## 5. Pose the fingerings

Real players barely move their fingers: a note change is about 1 cm of press or lift on single
fingers, seen mostly in the middle and tip joints. The default **Per Finger (sax chart)** mode works
that way. You pose each finger pressing its key once, and the built-in saxophone chart presses the
right fingers for every note. Fingers that a note doesn't use stay resting on their keys.

1. In **3. Fingering**, set **Character Rig** and keep the mode on **Per Finger (sax chart)**.
2. Go into Pose Mode with the hold from section 2b.
3. **Rest:** all fingers resting lightly curled on their keys, nothing pressed. Select **every
   joint of every finger and both thumbs**, pick `Rest` and click **Save**.
4. For each element below, press **only that finger**: bend its middle and tip joints a few degrees
   so the pad closes the key. Select **all 3 joints of that finger**, pick the element and click
   **Save**. Then put the finger back to rest before doing the next one.

| Element | Finger | Key |
|---|---|---|
| `L1` `L2` `L3` | left index, middle, ring | B, A, G |
| `LP` | left pinky | G# and the low B / Bb / C# keys |
| `R1` `R2` `R3` | right index, middle, ring | F, E, D |
| `RP` | right pinky | low C and Eb |
| `OctaveKey` | left thumb | octave key, used from D5 up |
| `Palm` | left hand | palm keys for the top notes (D6 to F#6) |

That's 11 small poses. **Analyze MIDI** lists any that the recording still needs. The 👁 button
loads a saved element so you can check it.

Bake with **Transition** at 2 to 3 frames. Fingers then press and lift quickly, like on a real horn.

**Transpose:** the add-on uses the note numbers the Aerophone sends. If the fingers look shifted
(you finger a G but the rig shows an A), set **Transpose** to the difference in semitones. Alto
sax players reading concert pitch usually need +9, and tenor +14.

*The older Whole-Hand Pose per Note mode (`Fingering_C`, `Fingering_D`, …) is still in the mode
dropdown, but it makes the whole hand morph between notes.*

## 6. Breath effects

In **4. Breath Effects**, click the presets. Select the matching object first, and the preset picks it up.

| Preset | Drives | Starts with |
|---|---|---|
| **Cheeks** | `CheekPuff` shape key, 0 → 1 | quick attack 0.04 s, release 0.15 s, curve 0.8 (soft breath already shows) |
| **Bell** | Bell scale, 1.0× → 1.3× its rest scale | attack 0.05 s, release 0.2 s |
| **Chest** | Chest bone rotation, small and added on top | slow, 0.15 / 0.4 s |
| **Sway** | Spine or hips rotation, a gentle lean with phrases | very slow, 0.6 / 1.2 s |

What each setting does:
- **Source:** *Breath (auto-detect)* finds CC2, CC11 or aftertouch, and falls back to note velocity when the
  recording has no breath. You can also force a specific CC, aftertouch or velocity.
- **Min / Max:** the output at no breath and at full breath. For the bell, try a Max of 1.15 for subtle or 1.5 for cartoony.
- **Attack / Release:** how fast it reacts when you blow harder or let go. Longer values are smoother.
- **Threshold:** breath below this fraction is ignored, which removes noise between notes.
- **Curve:** below 1 it reacts to soft breath, above 1 only strong breath moves it.
- **Normalize to Peak:** your strongest breath in the take counts as "full".
- **Chest and Sway data path:** the preset guesses a bone. If your rig names bones differently,
  right-click the bone's rotation field > Copy Data Path and paste it here.

## 7. Bake and render

1. **2. MIDI & Audio**: choose the .mid file, click **Fit Scene Range**, then choose the WAV and click **Add Audio**.
2. **6. Bake > Bake MIDI to Animation.** The status bar says how many notes were fingered and which
   breath source each effect used.
3. Press play. Changed something? Bake again. It replaces only the `MIDI: …` tracks.

If you keep an idle or body animation as the rig's active action, **Keep Active Actions as Base** moves it
into a `Base: …` track underneath, so it keeps playing under the fingers and breath.

## Troubleshooting

- **The fingers swing stiffly:** the poses only key the base joint of each finger. Re-save them with
  all 3 joints selected (section 5).
- **The sax drifts away from the hands:** lock it (section 2b). Parenting it to the Armature object
  or to one hand doesn't keep both hands on it.
- **The fingers don't move:** check that **Bake Fingering** is ticked and that Analyze doesn't list missing poses.
- **The fingers move but look one note off:** adjust **Transpose**.
- **The cheeks don't move:** the shape key must be named exactly as in the effect (default `CheekPuff`),
  and the effect's target must be the mesh that has it.
- **The bell scales from the wrong point:** move its origin to the joint (step 4).
- **It says "note velocity (no breath data found)":** the export lost the CC lane, or the Aerophone sends
  breath on another controller. Check Reaper's MIDI editor, or set Source to that CC.
