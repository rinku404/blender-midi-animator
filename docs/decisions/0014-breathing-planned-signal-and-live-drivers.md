# 0014. Breathing: a planned breath signal, one property, live drivers

Status: accepted (2026-11-12, plan step 7b). Supersedes the Lung-mode and Chest-preset parts of
[0007](0007-blow-optional-cc2-direct-and-lung.md); the rest of 0007 (CC2 default, never a silent
fallback, Direct mode) stands. Refines [0011](0011-hold-the-instrument.md).

## Context

The pipeline trial (step 6, P8 and P3) found two things wrong with the old Lung mode and Chest preset.
Lung mode drained with the blow and refilled only in rests the *blow* showed, so on the user's 54 s take it
breathed once and sat empty for the last 31 s. The Chest preset scaled the lowest spine bone, so the head and
arms grew with it, and its "Scale X+Z" assumed Rigify's axes: on CJ it stretched his height. The user shaped a
prototype (`breath_planner.py`, `breath_body.py`) that fixed both. This records what shipped.

## Decision

- **Breath signal (core, `signal.plan_breaths`).** One rule, "refill at every break": at every breath point
  (a gap between notes of at least 0.10 s, or a dip of the blow below 0.12 for 0.12 s inside a legato run;
  overlapping points merged, 0.02 s kept clear at each end) the player breathes in toward full lungs at up to
  3 lungs/s, eased (smoothstep), as much as the gap allows. Between breath points the lungs drain in proportion
  to the shaped blow. The lung size (seconds of full blow that empty the lungs) is **fitted per take** by
  bisection to the smallest one that never falls under a 15 % reserve while the notes play. After the last note:
  slow tidal breathing (0.5 ± 0.08, 4 s period). No "sized" rule (the user's choice).
  Lung mode in `blow_curve` is this planner; `lung_capacity` and `refill_time` are gone.
- **One breath property.** Bake writes the signal into the rig's custom property `breath_lung` (0..1) through
  an ordinary Property effect named *Breathing* (Lung mode, CC2, attack 0.15, release 0.4). Lung-mode effects
  are baked to at least the scene's end frame, so the slow breathing doesn't freeze after the last note.
- **Live drivers, not baked channels.** *Add Breathing* adds drivers on the body bones that read `breath_lung`,
  a master **Intensity** and one slider per part (Chest, Belly, Shoulders, Torso), the sliders living in
  `Scene.midi_animator`. A slider moves the body at once, also while the animation plays, with no re-bake.
  Bake-time channels with NLA influence would have needed one influence curve per part (or a re-bake per
  change), and an NLA strip's influence can't scale a scale or a rotation about the user's own pose. The
  drivers are plain arithmetic ("simple expressions"), which Blender evaluates natively: no Python script
  needs to be allowed to run.
- **Rig-aware axes (core `breathing.py`).** The body's forward, side and up come from the left and right
  shoulder bones (found from the hold hands: the ancestor that hangs from the ribcage) in the world, with a
  turn-round check against the instrument. Each bone's local axes are read from its rest orientation in the
  world, and the axis lined up best with forward is "depth", with side "width"; the lean and lift axes (and
  their signs) come from small-angle geometry, not from a convention. Verified on a Rigify-style rig, CJ's
  tidied rig, CJ's original FBX rig (spine bones pointing sideways, rolled), and test rigs.
- **No head or arm growth.** Every child of the ribcage (neck, shoulders) and the spine bone below it get
  *Inherit Scale = None* (their original is kept in a bone property and put back by Remove; while the hold is
  locked, Unlock keeps it off). With one spine bone only, the ribcage itself stops inheriting it.
- **Defaults (the prototype's):** ribcage 10 % deep, 4 % wide; belly 6 % deep; shoulders 3° (only where a
  bone sits between ribcage and the arm's IK root; a shoulder that *is* the IK root would just be re-solved);
  torso +2° full / −1° empty on the middle spine, half that on the lower one. Intensity 0..2, parts 0..3,
  all default 1.
- **The Chest preset is removed** (not kept as an advanced effect): everything it did is in Breathing, and it
  was the source of P3. The generic Bone effect with Lung mode and "Scale X+Z" is still there for a user who
  wants one channel, with the Rigify-axes caveat in its tooltip.

## Consequences

- Drivers override the animation of the same channels, so a user's own animation of the ribcage, the two spine
  bones below it or the shoulders stops showing while Breathing is on. Add Breathing switches those bones to
  XYZ Euler rotation (keeping the pose). Remove puts the bones back to the rest values taken at setup.
- The sliders live on the scene, so a rig appended into another scene needs Add Breathing again.
- Quick breaths in very short gaps last only a few frames; the parked idea (start the breath up to 0.15 s
  before the gap) is not built.
