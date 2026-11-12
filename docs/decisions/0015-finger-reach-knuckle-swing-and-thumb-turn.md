# 0015. Finger reach: knuckle swing and lift, thumb turn, and misses listed per pose

Status: accepted (2026-11-12, plan step 7c). Supersedes the joint-limit part of the 2026-11-07 note
in [0004](0004-key-markers-and-autoassign.md) ("only curl, 0 to 120°; the knuckle may also spread
±25°; Keep Twist locks the twist") and its one-line miss report. Everything else in 0004 stands.

## Context

Step 12 measured Autoassign on the user's file (CJ, B♭ clarinet). With bend-only limits the left
index could not roll up the tube from its hole onto the throat A and G# keys, and the left thumb
could not reach round the back to its hole and the register key: 10 to 16 mm misses. The status bar
showed the misses as one line that Blender cut after two fingers, and the advice was always "check
the Bend Axis" (P11, P12, P13).

## Decision

- **Knuckle Swing** (scene setting, default **25°**, 0 to 45°): every finger's root joint may turn
  sideways by the old 25° spread **plus** the swing, so ±50° by default. The user started at 15° and
  chose 25° after comparing renders of the left hand at both values. 15° left the pinky's C#/G#
  and F#/C# keys 6 to 11 mm off.
  On a hand holding a wind instrument the fingers lie across the tube, so the knuckle's sideways axis
  runs along it: the swing is the index rolling up onto a throat key, or the pinky down to its
  levers. Middle and end joints stay hinges that only curl.
- It applies to **every finger's root, not only the index.** It is the same joint (knuckle
  abduction) on all four fingers. IK only uses it when a key needs it: on the user's file the
  middle and ring poses come out unchanged (0 mm, same angles). The pinky and the right index need
  it as much as the left index (right index Hole Down 11.4 → 1.2 mm). A per-finger setting would be
  one more thing to set for no gain.
- **Thumb Turn** (scene setting, default **45°**, 0 to 60°): the thumb's base joint (its first
  bone) may turn about its own length, ±Thumb Turn, even with Keep Twist on. With the existing curl
  and spread, that makes the base a limited ball joint, which can turn the thumb pad round the tube
  to a key behind it. The thumb gets no extra swing.
  - **Why 45°:** the thumb's base (carpometacarpal) joint rolls the thumb about its length as it
    opposes. I proposed 30° as a moderate share of that roll. The user chose 45° after comparing
    renders of the left hand at 30° and 45°: it still doesn't look twisted.
  - On the user's file every thumb pose is ≤ 0.1 mm at 45°, using up to 35° of turn (Register Up).
    At 30° it was ≤ 1.2 mm. The Up poses also need the Knuckle Lift (below); without it they missed by
    6.0 and 11.6 mm.
- **Keep Twist still holds** for every other bone. With Keep Twist off, twist stays free as before.
- **Misses are stored on the pose:** a pose whose fingertip ends more than 3 mm from its target keeps
  `midianim_miss_mm` and `midianim_miss_advice`. Panel 2 lists them under the finger's poses, the
  Info log gets one line per finger plus one per missing pose, and the status bar says only
  "32 poses; 3 fingers miss: see panel 2 (details in the Info log)", which is what the user's file
  gives at the shipped defaults.
- **Advice names a direction:** the miss (target minus tip) is split along the tube (its axis from
  the key markers' principal direction, signed toward the mouthpiece by the profile's slot order)
  and along the marker's Z. If one part is at least 60 % of the miss, the advice says to move the
  hand that far up or down the tube, or toward or away from the keys. Otherwise it says to move the
  hand toward the key, round the tube.

- **Knuckle Lift** (scene setting, default **25°**, 0 to 25°; the user's choice, 2026-11-12): in
  **Up (hover) poses only**, the root joint of every finger and of the thumb may bend backwards
  (hyperextend) by up to this angle. A real knuckle lifts a finger off its key this way. Without it, a
  finger curled round a key could only rise by uncurling, and the thumb's Up poses missed by 6 and
  12 mm. **Down poses keep the bend-only rule:** Autoassign sets the IK limits per pose, with no lift
  for Down. On the user's file, at 15° swing and 30° turn, the Up poses used up to 23.5° (thumb Hole
  Up). No Down pose bends backwards, at those defaults or at the shipped 25° and 45°.
  - This is the only exception to ADR 0004's "fingers never bend backwards". It is limited to the
    root and to hovering, where a lifted finger looks natural.

## Consequences

- Locked poses keep their old miss values; they are not re-solved.
- A hover target can still be out of reach, for example when the finger is already fully curled
  (the right pinky's Up poses: both hinges at 120°). The advice then tells the user how far to move
  the hand.
- With Keep Twist off, the solver leaves up to about 1.2° of sideways turn on a hinge in Up poses
  (0° with Keep Twist on).
