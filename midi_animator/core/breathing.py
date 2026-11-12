"""Breathing: the geometry behind the Blender layer (no bpy).

One breath signal (lung volume 0..1, see signal.plan_breaths) moves the body. Which bone axis is
"depth", "width" or "up" is read from the bone's real orientation in the world, never from a rig
convention: Rigify's Y runs along the bone, Carl Johnson's FBX rig has X up and the spine bones
point sideways. Everything here works on plain tuples.
"""

import itertools
import math

# How far each part moves at full lungs and master slider 1 (the user's prototype, 2026-11-11)
CHEST_DEPTH = 0.10          # ribcage scale along the depth axis
CHEST_WIDTH = 0.04          # ...and along the width axis
BELLY_DEPTH = 0.06          # belly scale along the depth axis
SHOULDER_LIFT = 3.0         # degrees, shoulders rise on the in-breath
TORSO_FULL = 2.0            # degrees, torso leans back at full lungs...
TORSO_EMPTY = -1.0          # ...and forward at empty lungs (on the middle spine; the lower half of that)
LOWER_FRACTION = 0.5


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = math.sqrt(_dot(v, v))
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-12 else None


def body_frame(left, right, up=(0.0, 0.0, 1.0)):
    """(forward, side, up) unit vectors of a standing character, from the world positions of its
    left and right shoulders (or any left/right pair). `side` points to the character's right.
    Returns None when the pair has no horizontal spread."""
    up = _unit(up)
    r = (right[0] - left[0], right[1] - left[1], right[2] - left[2])
    r = (r[0] - up[0] * _dot(r, up), r[1] - up[1] * _dot(r, up), r[2] - up[2] * _dot(r, up))
    side = _unit(r)
    if side is None:
        return None
    return _cross(up, side), side, up


def face_the_instrument(forward, ribcage, instrument, min_offset=0.03):
    """`forward`, turned around if the instrument hangs clearly behind the ribcage (a left and a
    right bone the wrong way round gives a backwards frame). Positions in metres."""
    off = (instrument[0] - ribcage[0], instrument[1] - ribcage[1], instrument[2] - ribcage[2])
    return tuple(-c for c in forward) if _dot(off, forward) < -min_offset else forward


def pick_axes(axes, forward, side, up):
    """Which of a bone's local axes is depth, width and length. `axes` are its local X, Y, Z in the
    world; the three body directions are the world's. Returns (depth, width, length) as local axis
    indices 0..2: the assignment whose axes line up best with the body, whatever the bone's roll."""
    best, best_score = None, -1.0
    for perm in itertools.permutations(range(3)):
        score = sum(abs(_dot(_unit(axes[perm[k]]), d)) for k, d in enumerate((forward, side, up)))
        if score > best_score:
            best, best_score = perm, score
    return best


def rotation_axis(axes, pivot_dir, goal):
    """The local axis (index, sign) around which a positive rotation swings `pivot_dir` (the bone's
    direction, or whatever point hangs on it) most toward `goal`. Small angles: the swing of a
    vector d about axis a is a x d."""
    best, best_gain = (0, 1.0), -1.0
    for i, a in enumerate(axes):
        gain = _dot(_cross(_unit(a), pivot_dir), goal)
        if abs(gain) > best_gain:
            best, best_gain = (i, 1.0 if gain > 0 else -1.0), abs(gain)
    return best


def lean_back_axis(axes, up, forward):
    """The local axis (index, sign): a positive rotation about it tips a vertical bone backwards."""
    return rotation_axis(axes, up, tuple(-c for c in forward))


def lift_axis(axes, toward_arm, up):
    """The local axis (index, sign): a positive rotation about it raises the shoulder's far end
    (`toward_arm`: the direction from the shoulder bone's head to its child, or its tail)."""
    return rotation_axis(axes, toward_arm, up)

