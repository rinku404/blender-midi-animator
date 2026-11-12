# 0004. Key markers + Autoassign pre-solve IK into pose assets

Status: accepted (2026-11-06)

## Context

The user wants an autoassign button that snaps fingers to the instrument's keys.

## Decision

- **Key markers** are Empties parented to the instrument, tagged with custom properties `midianim_slot` / `midianim_key`, with local +Z pointing out of the key. They are placed at the 3D cursor or at selected vertices (Z follows their normal).
- **Autoassign** temporarily adds an IK constraint to the fingertip, solves it onto each marker (Down) and onto marker + Z × hover (Up), copies the evaluated bone matrices back, and saves **pose assets** named `F.<slot>.<key>.Down|Up`.
- Baking only reads pose assets. There is **no live IK** at playback.
- Generated poses store a fingerprint. If the values change (the user edited the pose), the pose becomes **locked** and Autoassign skips it unless *Overwrite Locked* is on. Locks can also be toggled by hand.
- A finger can have an authored **Up Pose** instead of hovering.

## Consequences

Poses are ordinary, hand-tweakable assets. Because the instrument is parented to the hand, pre-solved poses stay correct. If the instrument moves relative to the hand, re-run Autoassign. Later, markers could become instrument bones so the keys animate too.

## Note (2026-11-07, plan step 4)

*The joint limits and the miss report below are superseded by
[0015](0015-finger-reach-knuckle-swing-and-thumb-turn.md) (knuckle swing, thumb turn, misses per pose).*

Refinements inside this decision, no change to it:

- While solving, each finger joint's IK is limited to the rig's **Bend Axis** (a scene setting:
  X, -X, Z or -Z; X by default, which is what Rigify uses; *Detect* reads it from the rest curl
  and Detect Fingers sets it too). Middle and end joints are hinges that only curl (0 to 120°
  from rest); the knuckle may also spread ±25°. **Keep Twist** (default on) locks the twist.
  The bones' own IK settings are restored afterwards. Autoassign reports a fingertip that ends
  more than 3 mm from its target.
- Autoassign also builds **`F.Rest`** (each finger's Up pose over its home key, the slot's first
  key, plus the bones that carry the fingers and the hold's hand bones, as posed now) and uses
  it as the Rest pose when none is set. A Rest pose picked by the user is never replaced.
  `F.Rest` carries the same fingerprint lock as the other generated poses.
