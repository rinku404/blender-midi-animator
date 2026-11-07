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
