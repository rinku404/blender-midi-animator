# Hold guide text to port (from PR #2, `docs/aerophone-guide.md` on `main`)

For step 2. Panel names refer to the old add-on ("1. Models & Rigs > Hold the Instrument"); in v1 the
Hold box sits at the top of panel 2 (Fingers & Keys) and the strap bone replaces "chest bone".

## Section "2b. Hold the sax like a player"

A real alto or tenor sax hangs from a neck strap at chest height. It angles down and to the
player's right, with the mouthpiece in the mouth and the bell near the right hip. The **left hand
is on top**: the thumb is on the thumb rest and octave key, and the index, middle and ring fingers
rest on the B, A and G keys. The **right hand is below**: the thumb hooks under the thumb rest, and
the index, middle and ring fingers rest on F, E and D. The pinkies hover over the side keys.

1. Place the sax: mouthpiece at the lips, angled as described above.
2. Pose both arms and hands onto it, with each finger lightly curled over its key.
3. Open **1. Models & Rigs > Hold the Instrument**. Set the Rig and the Instrument (the sax
   body; the bell can stay its child), then click **Guess Bones**. Check the Strap Bone (a chest
   bone, for example `Bip01_Spine2`) and the two Hand bones.
4. Click **Lock Hands to Instrument**. The sax now hangs from the chest bone, and two small
   targets (`MIDI Hold L` and `MIDI Hold R`) keep the hands glued to it with IK, wherever the body moves.
   To adjust the grip, move those targets. The unlock button removes the lock.

## Troubleshooting line

- **The sax drifts away from the hands:** lock it (section 2b). Parenting it to the Armature object
  or to one hand doesn't keep both hands on it.

## Replaced text (old step 2 of "Import" in the guide)

"**Hold the instrument:** pose the hands around it. Then select the instrument, shift-select the rig,
go into Pose Mode, make the right hand bone active and press Ctrl+P > Bone. The instrument now follows that hand."
