"""Hold the Instrument: the pure geometry behind the Blender layer (no bpy).

- Arm bones whose tail doesn't sit on the next joint (an FBX import can leave the forearm's tail
  beside the limb). Lock's IK aims the forearm's *tail* at the hand target, so such a rig throws the
  hand off by the tail's offset. `off_joint` finds them; the Blender layer moves the tails.
- The instrument's front (the side with the keys / tone holes), stored as one of the instrument's
  local axes, and whether it faces away from the player.
"""

import math

AXES = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
FACING_OK_DEG = 60.0        # front within this of the player's forward: fine (a sax hangs to the right)
FACING_BAD_DEG = 90.0       # beyond this the front faces the player: Lock refuses
MIN_TAIL_TOLERANCE = 0.002  # metres
TAIL_TOLERANCE_FRACTION = 0.02


def axis_vector(name):
    """Unit vector of a local axis name ("+X", "-Y", ...)."""
    if name not in AXES:
        raise ValueError(f"axis must be one of {AXES}, not {name!r}")
    sign = -1.0 if name[0] == "-" else 1.0
    i = "XYZ".index(name[1])
    return tuple(sign if j == i else 0.0 for j in range(3))


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _length(v):
    return math.sqrt(_dot(v, v))


def _unit(v):
    n = _length(v)
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-12 else None


def nearest_axis(v):
    """The local axis name closest to direction v, and the angle between them in degrees.
    None if v is (near) zero."""
    u = _unit(v)
    if u is None:
        return None, None
    best = max(AXES, key=lambda a: _dot(u, axis_vector(a)))
    return best, angle_deg(u, axis_vector(best))


def angle_deg(a, b):
    """Angle between two directions in degrees (0..180)."""
    ua, ub = _unit(a), _unit(b)
    if ua is None or ub is None:
        return None
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(ua, ub)))))


def facing(front, forward):
    """How the instrument's front sits against the player's forward direction:
    (angle in degrees, verdict) with verdict "forward" (fine), "sideways" or "player" (the
    front faces the player: wrong way round). (None, "unknown") if a direction is missing."""
    a = angle_deg(front, forward) if front is not None and forward is not None else None
    if a is None:
        return None, "unknown"
    if a <= FACING_OK_DEG:
        return a, "forward"
    if a <= FACING_BAD_DEG:
        return a, "sideways"
    return a, "player"


def roll_angle(axis, front, forward):
    """Signed angle (radians) to turn around `axis` so that `front` points along `forward`, both
    taken perpendicular to the axis (rolling a tube about its length moves nothing on the axis).
    None if the front or the forward direction lies along the axis."""
    u = _unit(axis)
    if u is None:
        return None
    proj = []
    for v in (front, forward):
        d = _dot(v, u)
        p = _unit((v[0] - d * u[0], v[1] - d * u[1], v[2] - d * u[2]))
        if p is None:
            return None
        proj.append(p)
    f, w = proj
    return math.atan2(_dot(_cross(f, w), u), _dot(f, w))


def player_forward(object_minus_y_world):
    """The direction the player faces, from the rig object's local -Y axis in world space: its
    horizontal part when it has one (a rig turned on the spot), else the world's front (-Y), which
    is what an import with a 90-degree X rotation or a sideways axis convention should get."""
    x, y, _ = object_minus_y_world
    h = _unit((x, y, 0.0))
    if h is not None and math.hypot(x, y) > 0.5:
        return h
    return (0.0, -1.0, 0.0)


def tail_tolerance(bone_length):
    """How far a tail may sit from the next joint before Lock corrects it (metres)."""
    return max(MIN_TAIL_TOLERANCE, TAIL_TOLERANCE_FRACTION * bone_length)


def off_joint(bones):
    """bones: [(name, distance from the tail to the child's head, bone length)], in metres.
    Returns the ones whose tail is off the joint: [(name, distance)]."""
    return [(n, d) for n, d, length in bones if d > tail_tolerance(length)]


def mean_direction(directions):
    """Unit mean of a list of directions, or None when they cancel out or the list is empty."""
    if not directions:
        return None
    s = [0.0, 0.0, 0.0]
    for d in directions:
        u = _unit(d)
        if u is not None:
            s = [s[i] + u[i] for i in range(3)]
    return _unit(tuple(s))
