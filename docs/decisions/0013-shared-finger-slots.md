# 0013. Hands with fewer fingers: slots share a bone chain, the thumb is the hand's tilt

Status: accepted (2026-11-11). Refines [0003](0003-fingering-is-per-finger-combinations.md) and
[0004](0004-key-markers-and-autoassign.md); follows from [0012](0012-target-cj-and-clarinet.md).

## Context

CJ's original rig has two three-joint fingers per hand and no thumb (`arm left finger 1a_045`, `2a` …).
The charts (ADR 0003) are written for nine finger slots, and the note map, markers and pose names are all
per slot. Replacing the chart with a two-finger one would lose the real fingerings; leaving slots empty
would leave most notes without motion.

## Decision

- A finger slot may **share** another slot's bone chain (`FingerBones.shares`, the owner's slot id).
  Slots, keys, markers and pose names stay per slot: `F.L3.G.Down` is solved with L2's bones onto
  `Key.L3.G`. Bake combines the slots of one chain into one timeline (`core/fingering.merge_shared`).
- **Pressing wins.** While any slot of a chain presses, the chain is at the Down pose of the pressing
  slot listed first (profile order: middle before ring before pinky). While none presses, it follows the
  slot that pressed last, so it hovers over the key it left. Rest and whole-hand poses are unanimous.
  (The user's answer to the plan's question 2.)
- **Detect Fingers** reads numbered fingers: side from *left*/*right*, finger from the digit, joints from
  the hierarchy. Five or more numbered fingers: 1 is the thumb. Fewer: 1 is the index, no thumb. A finger
  the hand lacks shares the nearest found finger before it: a two-finger hand gives **finger 1 = index,
  finger 2 = middle + ring + pinky** (the user's answer to question 1).
- **The left thumb on a hand without a thumb bone is the hand bone's own tilt** (the user's choice over
  "not animated"): the slot's bones are the hand bone with a **Press Tilt** (default 3°, per finger,
  editable). Its Down poses turn the hand that much around the Bend Axis in the curling direction, the
  squeeze a thumb makes when it presses the octave or register key on the back of the instrument; its Up
  poses are the hand as posed. Rotation channels only, no markers, no IK. While the hold is locked (ADR
  0011) the hand's rotation is copied from `MIDI Hold L`, so Bake also keys the tilt on that target.
- A slot with no bones is skipped silently by Autoassign and Bake; Analyze lists it once as *Not animated*.

## Why these choices

- 3°, around the Bend Axis, towards the keys: the fingers are children of the hand, so any hand rotation
  moves the fingertips by angle × distance (about 4 mm at 3° for an 8 cm finger). Turning towards the keys
  sinks Down fingers slightly into their keys, where it doesn't show, and lowers hovering ones from 12 mm
  to about 8 mm. Turning the other way, or around another axis, would lift fingers off their keys or
  slide them along the instrument. The user can set any angle, including 0 or negative.
- The tilt on the hold target instead of a constraint trick: Copy Rotation's *Before/After* mix modes
  compose with the bone's world rotation (which includes the IK-driven forearm), so there is no
  constraint setting that layers a local tilt after the copy. Keying the target is exact: the e2e test
  measures 3.000° around the hand's own X with the wrist 0.000 mm off its target.

## Consequences

- `rig.sync_finger_slots` must save every per-finger field (`bones`, `up_pose`, `shares`, `tilt`) when it
  rebuilds the list; the e2e test covers both the relabel and the rebuild path.
- Markers are still per slot, so a two-finger hand needs markers for the ring and pinky keys too.
- The Bend Axis is read from the fingers; the hand bone's X may differ on some rigs, hence the sign note
  in the guide.
