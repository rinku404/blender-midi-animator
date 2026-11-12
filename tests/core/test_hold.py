import math

import pytest

from midi_animator.core import hold as H


def test_axis_vector_and_nearest_axis():
    assert H.axis_vector("+X") == (1.0, 0.0, 0.0)
    assert H.axis_vector("-Z") == (0.0, 0.0, -1.0)
    with pytest.raises(ValueError):
        H.axis_vector("Y")
    # the step-12 clarinet: the key markers' mean arrow in the instrument's own axes
    axis, off = H.nearest_axis((0.408, -0.861, 0.303))
    assert axis == "-Y" and 29 < off < 31
    assert H.nearest_axis((0, 0, 0)) == (None, None)
    assert H.nearest_axis((0, 0, 2))[0] == "+Z"


def test_facing_verdicts():
    fwd = (0, -1, 0)
    assert H.facing((0, -1, 0), fwd) == (0.0, "forward")
    a, v = H.facing((0.7, -0.7, 0), fwd)
    assert v == "forward" and abs(a - 45) < 1e-6
    assert H.facing((1, 0, 0), fwd)[1] == "sideways"          # 90 degrees: still not "player"
    assert H.facing((0, 1, 0), fwd) == (180.0, "player")
    assert H.facing((0.1, 0.5, 0), fwd)[1] == "player"
    assert H.facing(None, fwd) == (None, "unknown")
    assert H.facing((0, 0, 0), fwd) == (None, "unknown")


def _rot(axis, angle, v):
    """Rodrigues rotation of v about a unit axis."""
    c, s = math.cos(angle), math.sin(angle)
    k = axis
    kv = (k[1] * v[2] - k[2] * v[1], k[2] * v[0] - k[0] * v[2], k[0] * v[1] - k[1] * v[0])
    kd = k[0] * v[0] + k[1] * v[1] + k[2] * v[2]
    return tuple(v[i] * c + kv[i] * s + k[i] * kd * (1 - c) for i in range(3))


def test_roll_angle_turns_front_onto_forward():
    axis = (0.0, 0.0, 1.0)            # a vertical tube
    fwd = (0.0, -1.0, 0.0)
    for front in ((0, 1, 0), (1, 0, 0), (-1, 0, 0), (0.6, 0.8, 0), (0.3, -0.5, 0.8)):
        a = H.roll_angle(axis, front, fwd)
        turned = _rot(axis, a, front)
        # the part along the tube can't change by rolling; the rest must point forward
        ang, verdict = H.facing((turned[0], turned[1], 0.0), fwd)
        assert verdict == "forward" and ang < 1e-6, (front, a, turned)
    # a tilted tube (22 degrees from vertical) with the front facing the player: half a turn
    tube = (0.0, -math.sin(math.radians(22)), -math.cos(math.radians(22)))
    front = (0.0, math.cos(math.radians(22)), -math.sin(math.radians(22)))     # back, perpendicular
    assert abs(abs(H.roll_angle(tube, front, fwd)) - math.pi) < 1e-6
    # degenerate: the front lies along the axis
    assert H.roll_angle(axis, (0, 0, 1), fwd) is None
    assert H.roll_angle((0, 0, 0), (0, 1, 0), fwd) is None


def test_player_forward():
    assert H.player_forward((0, -1, 0)) == (0.0, -1.0, 0.0)
    f = H.player_forward((1, 0, 0))                 # rig turned 90 degrees on the spot
    assert abs(f[0] - 1) < 1e-9 and abs(f[1]) < 1e-9
    assert H.player_forward((0, 0, -1)) == (0.0, -1.0, 0.0)      # FBX-style 90-degree X rotation
    assert H.player_forward((0.2, -0.3, 0.9)) == (0.0, -1.0, 0.0)  # mostly up: fall back


def test_off_joint_tails():
    assert H.tail_tolerance(0.0) == pytest.approx(0.002)
    assert H.tail_tolerance(0.276) == pytest.approx(0.00552)
    bones = [("forearm.L", 0.0, 0.25), ("upper_arm.L", 0.001, 0.30),       # on the joint
             ("arm left elbow_040", 0.3897, 0.2756),                       # CJ: 39 cm off
             ("arm left shoulder 2_039", 0.3988, 0.2820), ("short", 0.003, 0.05)]
    assert H.off_joint(bones) == [("arm left elbow_040", 0.3897), ("arm left shoulder 2_039", 0.3988),
                                  ("short", 0.003)]


def test_mean_direction():
    assert H.mean_direction([]) is None
    assert H.mean_direction([(0, 1, 0), (0, -1, 0)]) is None
    m = H.mean_direction([(0, -1, 0), (0, -1, 0), (1, 0, 0), (0, 0, 0)])
    assert H.nearest_axis(m)[0] == "-Y"
