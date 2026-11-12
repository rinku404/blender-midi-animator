import math

import pytest

from midi_animator.core import breathing as B

UP = (0.0, 0.0, 1.0)
FWD = (0.0, -1.0, 0.0)          # Blender's front view: the character faces -Y
SIDE = (-1.0, 0.0, 0.0)         # toward the character's right


def rot_x(deg, v):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (v[0], c * v[1] - s * v[2], s * v[1] + c * v[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def test_body_frame_from_left_and_right_shoulders():
    f, side, up = B.body_frame((0.2, 0.0, 1.4), (-0.2, 0.0, 1.4))
    assert f == pytest.approx(FWD) and side == pytest.approx(SIDE) and up == UP
    # a rig turned on the spot, tilted shoulders: still horizontal
    f, side, _ = B.body_frame((0.0, 0.2, 1.5), (0.0, -0.2, 1.3))
    assert f == pytest.approx((1.0, 0.0, 0.0))
    assert B.body_frame((0, 0, 1), (0, 0, 2)) is None


def test_face_the_instrument_flips_a_backwards_frame_only_when_clear():
    assert B.face_the_instrument(FWD, (0, 0, 1), (0, -0.3, 0.8)) == FWD
    assert B.face_the_instrument(FWD, (0, 0, 1), (0, 0.3, 0.8)) == pytest.approx((0.0, 1.0, 0.0))
    assert B.face_the_instrument(FWD, (0, 0, 1), (0, 0.01, 0.8)) == FWD      # too close to tell


def test_pick_axes_rigify_style():
    # Rigify: X side to side, Y up the bone, Z front to back (pointing back)
    assert B.pick_axes([(-1, 0, 0), (0, 0, 1), (0, 1, 0)], FWD, SIDE, UP) == (2, 0, 1)


def test_pick_axes_cj_tidied_and_original_fbx_rig():
    # tidied, as measured on 'spine lower_011': X up, Y side to side... Z front to back
    tidied = [(0.03, 0.0, 0.0), (0.0, 0.0, 0.03), (0.0, -0.03, 0.0)]
    assert B.pick_axes(tidied, FWD, SIDE, UP) == (2, 0, 1)
    # original FBX rig, 'spine lower_011': the bone points sideways
    old = [(0.0, 0.0, 0.03), (0.03, 0.0, 0.0), (0.0, 0.03, 0.0)]
    assert B.pick_axes(old, FWD, SIDE, UP) == (2, 1, 0)
    # a bone rolled 45 degrees about its length still gets three different axes
    rolled = [rot_x(45, v) for v in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
    assert sorted(B.pick_axes(rolled, FWD, SIDE, UP)) == [0, 1, 2]


def test_lean_back_and_lift_axes_swing_the_right_way():
    axes = [(-1, 0, 0), (0, 0, 1), (0, 1, 0)]          # Rigify chest
    i, sign = B.lean_back_axis(axes, UP, FWD)
    assert i == 0
    swing = cross(tuple(sign * c for c in axes[i]), UP)
    assert swing[1] > 0.9                               # the top of the bone goes backwards (+Y)
    # a left shoulder pointing out to +X: the rotation that raises its far end
    shoulder = [(0, 1, 0), (1, 0, 0), (0, 0, 1)]
    d = (1.0, 0.0, 0.0)
    i, sign = B.lift_axis(shoulder, d, UP)
    swing = cross(tuple(sign * c for c in shoulder[i]), d)
    assert swing[2] > 0.9                               # the far end goes up
