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
   changed Transpose yourself, switching instrument leaves it alone, unless your value equals the
   previous instrument's default (then it changes to the new one's). If the fingers look shifted,
   set the difference in semitones here. The HUD can still show the recorded notes: set its
   Pitch to **Concert**.
5. **Fit Scene Range**, then choose the WAV and **Add Audio**.

## 3. Fingers and keys

**2. Fingers & Keys**
1. Set **Character Rig** and click **Detect Fingers**. Rigify, Mixamo and VRoid names are recognised,
   and numbered fingers such as `arm left finger 1a` (see *Hands with fewer fingers* below).
   Fix any finger by picking its bones (root → tip). Detect Fingers also sets the **Bend Axis**
   (in the Autoassign box) from the way the fingers curl at rest; see step 5.
2. **Hold the instrument.** Place the instrument at the lips, set which side of it is the front,
   pose the arms onto it, then **Lock** the hands to it. Click by click in
   [Set up the hold](#set-up-the-hold) below.
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
   - Three reach settings sit in the Autoassign box of panel **2. Fingers & Keys** (sidebar **N** ▸
     **MIDI** tab), just under **Keep Twist** and **Overwrite Locked**. **Swing °** and **Lift °**
     share a row, and **Thumb Turn °** is on the row below:
     - **Swing °** (Knuckle Swing, 25° by default, up to 45°): how much further each finger's knuckle
       may swing sideways, which on a held instrument is along the tube. This lets the left index roll
       up from its hole onto the throat A and G# keys. The middle and end joints still only curl.
     - **Lift °** (Knuckle Lift, 25° by default, up to 25°): how far a finger's or the thumb's knuckle
       may bend backwards, **in Up (hover) poses only**, so a curled finger can still rise off its key.
       Down poses never bend backwards. Set 0 for no lift.
     - **Thumb Turn °** (45° by default, up to 60°): how far the thumb's base joint may turn about its
       own length, so the thumb reaches round the back to its hole and the register key. It is the
       one twist Keep Twist allows. Raise it if a thumb pose still misses and the thumb doesn't look
       twisted; set 0 to lock it.
   - If a fingertip can't reach its target, the status bar says how many fingers miss. Panel 2
     marks each missing pose under the finger's poses with "… mm off" and says which way and how far
     to move the hand (up or down the tube, toward or away from the keys, or round the tube). The
     Info log (**Window ▸ Info**, or the Scripting workspace) lists every miss. Move the hand in
     your hold pose, or the marker the other way, and run Autoassign again.
   - Autoassign also builds **`F.Rest`**: every finger up over its home key (the first key in
     its list, for example B for the left index) and the hand bones as they are now. It becomes
     the **Rest Pose** if you haven't set one (see the Note Map).
6. Check a pose with the eye button. To fix one, apply it, tweak the bones, and update the pose
   asset. The pose locks itself and Autoassign won't overwrite it. You can also toggle the lock
   by hand, or tick **Overwrite Locked** to regenerate everything.
7. Optional: give a finger an authored **Up Pose** instead of hovering.

### Set up the hold

Do this once, before placing key markers. Everything here is in the 3D Viewport; the plugin's
panel is in the sidebar (press **N** with the mouse over the viewport, then the **MIDI** tab, panel
**2. Fingers & Keys**, box **Hold the instrument**).

**How a real player stands.** A **clarinet** hangs from the lips, pointing down and forward: the
tube leans about **20–25° away from the body**, bell toward the knees, never flat. The **keys and
tone holes face forward**, away from the player. The **left hand is on top** (the upper joint, just
below the barrel), the **right hand below** it (the lower joint), palms toward the tube from the
sides, fingers reaching round to the front, and **both thumbs behind** the tube (the left thumb
on its hole and the register key, the right under the thumb rest, carrying the weight). A **sax**
hangs from a neck strap at chest height, angled down and to the player's right, mouthpiece in the
mouth and bell near the right hip; same hands (left on top, right below), thumbs behind.

1. **Pick the Instrument.** In the Outliner (top right), an imported instrument is a tree: a
   top name (for the trial's clarinet, `Clarinet`) with an in-between object and the meshes nested
   under it. The **Instrument** field wants that **top object**, so that the whole instrument moves
   as one. Click the field in the Hold box and pick it from the list (or click the eyedropper, then
   the instrument in the viewport, then check the name). If your import is a single mesh, pick that.
2. **Put it at the lips.** Click the instrument in the Outliner (so it is selected), move the mouse
   over the viewport and press **G** to move it (**X**, **Y** or **Z** after G locks the move to one
   axis; left-click to confirm, right-click to cancel), **R** to turn it. Work from the side view
   (**Numpad 3**) to set the lean and the height, and from the front (**Numpad 1**) to centre it.
   For exact numbers, open the sidebar's **Item** tab and type **Location** and **Rotation**. Aim for:
   mouthpiece tip at the mouth, the tube leaning 20–25° forward from vertical, bell forward and down.
   Don't scale the rig to fit the instrument; scale the instrument (**S**) if it is the wrong size.
3. **Set the Front.** Orbit the view (drag with the **middle mouse button**) until you look
   **straight at the keys** (the side with the rings, rods and tone holes) and click **From View**.
   The **Front (keys)** field fills in with one of the instrument's own axes (for the trial's clarinet,
   `-Y`), and the line under it says how the front sits:
   - *Front faces forward (N° off)*: good.
   - *Front faces the player* or *Front faces sideways*: click **Turn Front Forward**. The instrument
     rolls about its own length (the mouthpiece stays put) until the keys face away from the player.
     If the line still says *sideways* after turning, the tube itself points forward: lean it more
     upright (step 2) and click again.
   - Already have key markers? **From Markers** reads the front from their arrows instead.
   The player is taken to face the **front view** (Numpad 1), the way imported characters do. **Lock**
   refuses while the front faces the player, so a hold with the fingers over the back can't happen
   by accident. *Not Set* skips the check.
4. **Pose the arms.** Click the rig (in the Outliner or on a bone), then switch to **Pose Mode**
   (the mode menu at the top left of the viewport, or **Ctrl+Tab**). Bones turn about their own base,
   so pose from the shoulder down and **rotate only**, never move (G) a bone:
   1. Click the **upper arm** bone, press **R** and move the mouse; the arm swings (R twice turns it
      freely, **R X** / **R Y** / **R Z** about one axis). Left-click to confirm. Bring the elbow a
      little forward and out.
   2. Click the **forearm**, **R**, and bring the hand to the tube: left hand at the upper joint,
      right hand at the lower joint, each palm beside the tube, a finger's width away from it.
   3. Click the **hand** (the wrist bone), **R**, and turn it so the fingers reach round the front of
      the tube and the thumb sits behind. Check from the front (**Numpad 1**), the side (**Numpad 3**)
      and above (**Numpad 7**). The fingertips don't have to touch the keys yet: Autoassign curls the
      fingers onto the markers later; what matters is a palm close to the tube and thumbs behind.
   If a hand ends up inside the tube, turn the forearm outward a little. **Ctrl+Z** undoes a turn.
5. **Guess Bones**, then check the three fields: **Strap Bone** should be the upper chest (the bone
   the arms and neck hang from: `spine upper`, `mixamorig:Spine2`, Rigify's `spine.003`), **Left**
   and **Right Hand** the wrist bones (`hand.L`, `arm left wrist_041`, …), not fingers. Fix one by
   typing in it or picking from its list.
6. If a line says ***N arm bones end off the joint (up to 39 cm); Lock fixes them***: some FBX
   imports draw the arm bones beside the limb instead of along it (CJ's does), which would throw the
   hands away from the instrument on Lock. Lock moves those bone ends onto the elbow and wrist
   first. The character's skin and pose don't change (the bones just turn to lie along the arm), and
   the status bar lists the bones moved. **Ctrl+Z** undoes the whole Lock. One caveat: if the rig came
   with arm animation of its own (a walk cycle keyed on those bones), that animation would play
   differently afterwards; the plugin doesn't convert it.
7. Click **Lock**. The instrument now hangs from the strap bone, and two small spheres
   (`MIDI Hold L` and `MIDI Hold R`, children of the instrument) keep the hands glued to it with IK
   wherever the body moves. Nothing should move when you click; the status bar at the bottom says
   what was done. To adjust a grip afterwards, click its sphere and press **G** (the hand follows).
   **Unlock** removes the spheres and constraints (the instrument stays on the strap).

Breathing (section 5) swells the ribcage but never the instrument or the arms: while locked, each
upper arm's *Inherit Scale* is set to *None* (Blender's IK misses its target under a scaled parent), so
the hands stay on their targets. **Unlock** puts the setting back (unless Breathing is on, which needs it off).

### Hands with fewer fingers

A cartoon hand with two or three fingers and no thumb (CJ's original rig: `arm left finger 1a…1c`,
`2a…2c`) still plays. Each finger slot of the chart stays, but several slots can move one bone chain:

- **Detect Fingers** reads numbered names (the side from *left*/*right*, the finger from the digit, the
  joints from the hierarchy). With five numbered fingers, 1 is the thumb; with fewer, 1 is the index and
  the hand has no thumb. A finger the hand doesn't have **shares** the bones of the nearest found finger
  before it: on a two-finger hand, finger 1 = **L Index**, finger 2 = **L Middle + L Ring + L Pinky**
  (same on the right). The status bar says what was proposed.
- **Shares Bones With** (per finger, panel 2) is where you change it. A sharing finger keeps its own
  keys, markers and poses (`F.L3.G.Down` is solved with the middle finger's bones onto `Key.L3.G`), so
  place its markers like any other finger's.
- When two slots on one chain disagree, **pressing wins**: the chain goes to the key of the pressing
  slot, and when both press, to the key of the slot **listed first** (middle before ring before pinky).
  When neither presses, it hovers over the key it left last.
- **The thumb** (`LT`: octave key, or the clarinet's thumb hole and register key) has no bone on such a
  hand, so Detect Fingers gives it the **hand bone** with a **Press Tilt** of 3°: whenever a thumb key is
  down, the whole hand turns 3° around the Bend Axis towards the keys, the squeeze a thumb press makes.
  It needs no markers. Change the angle in the finger's box (negative if the hand tilts away from the
  instrument on your rig; 0 turns the slot back into a normal IK finger), or set the slot's bones to
  nothing to leave it still. With **Lock** on, the hand's rotation comes from its hold target, so Bake
  keys the tilt on `MIDI Hold L` as well, and the hand still tilts (the wrist stays on the instrument).
- A slot with no bones at all is skipped by Autoassign and Bake; **Analyze** lists it once as
  *Not animated*.

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
| | `Register` | on the near (lower) edge of the register key, just above the thumb hole, so the thumb pad stays on the hole while the tip presses the key | every clarion note, B4–C6 |
| | `RegOnly` | a few mm further up than `Register`, past the near edge of the register key, so the thumb visibly rolls up off the hole | throat A#4 (B♭4) only |
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

Open panel **4. Blow** (the **MIDI** tab of the 3D Viewport sidebar; press **N** over the viewport if the
sidebar is hidden, then click the panel's title to unfold it). It has two parts: **Breathing**, a box at the
top that moves the whole upper body, and the effect list below it (for example the **Cheeks**).

### Breathing: chest, belly, shoulders and torso

The character breathes in at every break in your playing, as a player does, and breathes out as the notes
use the air. After the last note it keeps breathing slowly. You don't set anything: the plugin reads your
notes and your breath curve (CC2).

1. **Check the Hold bones first.** In panel **2. Fingers & Keys**, box **Hold the instrument**, the
   **Strap Bone** (the upper chest) and both **Hand** fields must be filled: click **Guess Bones** if they
   are empty (see "Set up the hold"). Breathing needs them to find the ribcage and the shoulders.
2. In panel **4. Blow**, in the **Breathing** box, click **Add Breathing**. The status bar at the bottom of
   the window says what it found, for example *ribcage spine upper_013: depth = local Z, width = local X*.
   It reads the real direction of each bone, so it works on any rig, however the bones are turned.
3. Click **Bake MIDI to Animation** (panel **6. Bake**). This records *when* the character breathes in
   (a track called `MIDI: Breathing`). If the status bar says *CC2 not in file*, click **Use Velocity** on
   the effect named **Breathing** in the list below, then bake again.
4. Press **Space** (or play the timeline). The ribcage swells forward and sideways, the belly swells,
   the shoulders rise a little, and the torso leans back on the in-breath and forward as the air runs out.
   The neck, head, shoulders and arms keep their size, and with the hold **Lock**ed the hands stay on the
   instrument.

The **sliders** in the Breathing box work live, also while the animation plays. You never have to bake
again after moving one:

| Slider | What it does | Default |
|---|---|---|
| **Intensity** | Everything at once: 0 = still, 1 = as set, 2 = double | 1 |
| **Chest** | Ribcage swell: up to 10 % deeper, 4 % wider | 1 |
| **Belly** | Belly swell: up to 6 % deeper | 1 |
| **Shoulders** | Shoulders rise up to 3° | 1 |
| **Torso** | Leans back up to 2° with full lungs, 1° forward with empty lungs | 1 |

Each part slider goes from 0 (that part stays still) to 3 (three times as much). Click **Redo** to set up
again (after you change the Strap Bone, say), or the **X** beside it to take Breathing off the rig.

Things worth knowing:
- Breathing drives the pose bones of the ribcage, the two spine bones below it and the shoulders, so it
  overrides animation of your own on those bones. Other bones are left alone.
- The 3° and the percentages are for a normal-sized adult. A more theatrical breath: raise **Intensity**.
- Moving the hands away from the instrument (Unlock) doesn't switch Breathing off. Remove it with the **X**.
- A file made before this version may still have the old **Chest** effect in the list. **Add Breathing**
  switches it off (the tick box in the list; its settings stay) and the status bar says so. **Bake** warns if you
  tick it on again next to Breathing, because the body would move twice. The **X** beside **Redo** ticks it back on.
- The old **Chest** button is gone: it scaled the lowest spine bone, so the head and arms grew with it, and
  it assumed Rigify's bone directions. Breathing replaces it. The generic effect list (below) can still
  drive any bone, but you choose the axis yourself.

### Other blow effects (Cheeks and your own)

Click **Cheeks** (select the face mesh first) to puff the cheeks with the blow. The **+** next to the list adds
an empty effect (pick any shape key, bone channel or property), **−** removes the selected one.

| Preset | Drives | Mode |
|---|---|---|
| Cheeks | `CheekPuff` shape key, 0 → 1 | **Direct**: follows the blow |

- **Source:** CC2 by default. If Analyze finds no CC2, the effect shows **Use Velocity** / **Turn Off**.
  It isn't baked until you choose. Velocity rises to the note's velocity and decays to **Sustain**.
- **Min / Max:** output at no blow and full blow (Lung: empty and full lungs). Rotations are in degrees.
- **Mode: Lung** gives the planned breathing curve (full after each break, emptier as you blow) instead of
  the blow itself; the Breathing box uses it. **Attack / Release:** how fast the blow is followed.
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
- **Lock threw the hands off the instrument:** check that **Left Hand** and **Right Hand** are the wrist bones (not fingers or twist helpers). Arm bones whose ends sit off the joints are fixed by Lock itself (the panel announces it). **Unlock**, fix the bones, **Lock** again.
- **The fingers are over the back of the instrument:** the front wasn't set. **Unlock**, set **Front** (From View) and click **Turn Front Forward**, re-pose the hands, **Lock**.
- **A finger doesn't move:** check its bones (or **Shares Bones With**) in panel 2 and that its markers exist, then run Autoassign. Bake lists missing poses; Analyze lists slots with no bones as *Not animated*.
- **The hand tilts the wrong way on thumb keys:** negate the thumb slot's **Press Tilt** (its sign follows the Bend Axis, which is read from the fingers, not the hand).
- **The fingertip misses the key:** panel 2 shows "… mm off" next to the pose and which way to move the hand. Move the hand (or the marker) and run Autoassign again; unlock the pose if you edited it. A thumb that can't get round the back may need more **Thumb Turn °**, an index that can't roll up the tube more **Swing °**, and an Up pose that stays too close to its key more **Lift °** (up to 25°). If the finger bends the wrong way, check the **Bend Axis**.
- **Fingers bend backwards or sideways:** the **Bend Axis** is wrong for this rig. Click **Detect**, or pick it by hand, and run Autoassign with **Overwrite Locked**.
- **Wrong notes fingered:** adjust **Transpose**.
- **Cheeks don't move:** the effect's object must have the shape key. Check the status line for the blow source.
- **Add Breathing says a bone was not found:** fill the Strap Bone and both Hands in panel 2 (**Guess Bones**), then click it again.
- **The chest doesn't move, or moves backwards:** click **Bake** once (the sliders only scale what is baked), and check that the status bar's line after **Add Breathing** names sensible axes. If the Left Hand and Right Hand fields are on the wrong sides, the front is turned round: swap them.
- **A bone I animated myself stopped following my animation:** Breathing owns the ribcage, the two spine bones below it and the shoulders. Remove it (the **X**) to get them back.
- **"CC2 not in file":** the export lost the CC lane, or the Aerophone sends breath on another controller (see Analyze's Controllers line).
