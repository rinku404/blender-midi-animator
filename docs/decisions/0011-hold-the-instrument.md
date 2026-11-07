# 0011. Hold the instrument: strap Child Of without scale, hands locked by IK

Status: accepted (2026-11-07). Refines [0004](0004-key-markers-and-autoassign.md).

## Context

0004 said pre-solved finger poses stay correct "because the instrument is parented to the hand".
A sax is held by two hands and a neck strap, so no single hand can carry it. PR #2 hung the
instrument from a chest bone with bone parenting and locked both hands onto it with IK. In v1 that
collides with the Chest breathing effect: it scales a chest bone, and a bone-parented child
inherits the bone's scale, so the instrument would swell with every breath.

## Decision

- The instrument hangs from a **strap bone** (guessed from the rig, editable) through a **Child Of
  constraint with scale off** (`MIDI Hold Strap`), with its inverse matrix set so nothing moves on lock.
- Each hand gets a target empty (`MIDI Hold L/R`, child of the instrument) at the hand's current
  place, a 2-bone IK on the forearm and a Copy Rotation on the hand. Targets are what the user moves
  to adjust the grip. Lock is idempotent: it keeps existing targets and rebuilds constraints.
- Unlock removes the hand constraints and targets; the instrument stays on the strap.
- Key markers stay children of the instrument, so they stay put relative to the hands.

## Why not the alternative

The plan preferred (a): make the Chest effect avoid the strap bone. That cannot work in general.
Scale is inherited down the bone hierarchy, so the effect bone must be neither the strap bone nor
any ancestor of it, and the upper chest (the natural strap bone) is exactly what the Chest effect
wants to scale. The in-Blender test confirms it: a probe empty bone-parented to `chest` reaches a
world scale of 1.04 during the bake, while the instrument's stays 1.0 exactly.

## Consequences

- Blender's IK is not exact under a scaled parent: with the Chest effect at its default 0.04, the
  hand sits up to ~8 mm off its target at peak breath (test rig). Acceptable for v1; step 4/6 may revisit.
- Rig-scale is ignored by the constraint (scale off also strips a scaled Armature object's scale).
