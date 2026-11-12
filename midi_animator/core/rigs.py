"""Finger bone-chain detection from bone names (Rigify, Mixamo, VRoid, Unreal, generic, numbered)."""

import math
import re
from dataclasses import dataclass

FINGER_WORDS = {
    "thumb": ("thumb",),
    "index": ("index",),
    "middle": ("middle",),
    "ring": ("ring",),
    "pinky": ("pinky", "little", "pinkie"),
}
FINGER_ORDER = ("index", "middle", "ring", "pinky")      # the fingers a slot can share
# Numbered fingers ("arm left finger 1a_045", "Finger_02_L"): the digit after "finger"
_NUMBERED = re.compile(r"finger[\s_.\-]*0*(\d)(?!\d)")
# Helper / mechanism bones that are not the ones to pose
EXCLUDE = ("org-", "def-", "mch-", "vis_", "master", "tweak", "_ik", ".ik", "ik_", "target",
           "pole", "parent", "socket", "meta", "_end", "nub", "tip")
THUMB_TILT_DEG = 3.0       # default hand tilt that stands in for a missing thumb (see tilt_rotation)


def _side(name):
    low = name.lower()
    if "left" in low:
        return "L"
    if "right" in low:
        return "R"
    tokens = [t for t in re.split(r"[._:\-\s]+", low) if t]
    if "l" in tokens:
        return "L"
    if "r" in tokens:
        return "R"
    if re.search(r"[._\-]l\d*$", low):
        return "L"
    if re.search(r"[._\-]r\d*$", low):
        return "R"
    return None


def _finger(name):
    """A finger word ("index"), or "#<n>" for a numbered finger ("finger 2b"), or None."""
    low = name.lower()
    for finger, words in FINGER_WORDS.items():
        if any(w in low for w in words):
            return finger
    m = _NUMBERED.search(low)
    return f"#{m.group(1)}" if m else None


def _numbered_to_named(found):
    """Give numbered fingers names, per side. Five or more: 1 is the thumb, 2 the index, and so on.
    Fewer: 1 is the index and the hand has no thumb (CJ: 1 = index, 2 = middle). A side with
    named fingers keeps those and drops its numbered ones."""
    out = {}
    for side in ("L", "R"):
        named = {k: v for k, v in found.items() if k[0] == side and not k[1].startswith("#")}
        numbered = sorted((int(k[1][1:]), v) for k, v in found.items() if k[0] == side and k[1].startswith("#"))
        if named or not numbered:
            out.update(named)
            continue
        names = ("thumb",) + FINGER_ORDER if len(numbered) >= 5 else FINGER_ORDER
        for (_, chain), finger in zip(numbered, names):
            out[(side, finger)] = chain
    return out


def detect_finger_chains(bones):
    """bones: [(name, parent_name_or_None)] in any order.
    Returns {(side, finger): [bone names root -> tip]} for every finger found."""
    parent = dict(bones)
    groups = {}
    for name, _ in bones:
        low = name.lower()
        if any(x in low for x in EXCLUDE):
            continue
        side, finger = _side(name), _finger(name)
        if side and finger:
            groups.setdefault((side, finger), set()).add(name)

    chains = {}
    for key, names in groups.items():
        # keep the longest connected chain (children sorted by name: 1a -> 1b -> 1c)
        best = []
        for root in [n for n in names if parent.get(n) not in names]:
            chain, cur = [root], root
            while True:
                kids = sorted(n for n in names if parent.get(n) == cur)
                if not kids:
                    break
                cur = kids[0]
                chain.append(cur)
            if len(chain) > len(best):
                best = chain
        if best:
            chains[key] = best
    return _numbered_to_named(chains)


def chains_for_slots(slots, bones):
    """{slot_id: [bone names]} for the profile's finger slots."""
    return assign_slots(slots, bones).chains


@dataclass
class SlotAssignment:
    chains: dict        # slot id -> [bone names root -> tip]
    shares: dict        # slot id -> slot id whose bones it uses (fingers the hand doesn't have)
    tilt_hands: dict    # thumb slot id -> hand bone: no thumb bone, the hand's tilt stands in


def assign_slots(slots, bones):
    """Fill the profile's finger slots from the rig's bone names.

    A finger the hand doesn't have shares the bones of the nearest found finger before it
    (index, middle, ring, pinky order), or of the first found finger if none comes before it:
    a two-finger hand gives index | middle + ring + pinky. A thumb slot with no thumb bone is
    offered the hand bone (the parent of the fingers) for a press tilt, when the side has any
    finger at all."""
    found = detect_finger_chains(bones)
    parent = dict(bones)
    chains = {s.id: found[(s.side, s.finger)] for s in slots if (s.side, s.finger) in found}
    shares, tilt_hands = {}, {}
    for side in ("L", "R"):
        fingers = sorted((s for s in slots if s.side == side and s.finger in FINGER_ORDER),
                         key=lambda s: FINGER_ORDER.index(s.finger))
        have = [s for s in fingers if s.id in chains]
        if not have:
            continue
        for i, s in enumerate(fingers):
            if s.id in chains:
                continue
            before = [t for t in fingers[:i] if t.id in chains]
            shares[s.id] = (before[-1] if before else have[0]).id
        hand = parent.get(chains[have[0].id][0])
        for s in slots:
            if s.side == side and s.finger == "thumb" and s.id not in chains and hand:
                tilt_hands[s.id] = hand
    return SlotAssignment(chains, shares, tilt_hands)


def tilt_rotation(bend_axis, tilt_deg):
    """(axis index, radians) that turn a hand bone around its own bend axis by tilt_deg, in the
    curling direction (towards the fingers' keys) for a positive tilt. A thumb pressing the
    octave or register key on the back of the instrument squeezes the hand towards the keys,
    which is what the tilt stands for on a hand without a thumb bone."""
    if bend_axis not in BEND_AXES:
        raise ValueError(f"bend axis must be one of {BEND_AXES}, not {bend_axis!r}")
    sign = -1.0 if bend_axis.startswith("-") else 1.0
    return "xyz".index(bend_axis[-1].lower()), sign * math.radians(tilt_deg)


# -- "Hold the Instrument": strap and hand bones -------------------------------

# Strap bone candidates, best first: the upper torso, where a neck strap hangs.
STRAP_KEYWORDS = ("spine2", "spine4", "spine3", "upperchest", "upper_chest", "spine.003", "chest",
                  "spine1", "spine")
_HOLD_EXCLUDE = ("org-", "def-", "mch-", "twist", "tweak", "target", "pole", "master", "socket")


def _hold_ok(name):
    low = name.lower()
    return not any(x in low for x in _HOLD_EXCLUDE) and _finger(name) is None


def _strap_rank(name):
    low = name.lower().replace("mixamorig:", "")
    for i, kw in enumerate(STRAP_KEYWORDS):
        if low == kw:
            return i * 2
    for i, kw in enumerate(STRAP_KEYWORDS):
        if kw in low:
            return i * 2 + 1
    return None


def _hand_rank(name):
    low = name.lower()
    if ("hand" not in low and "wrist" not in low) or "ik" in re.split(r"[._:\-\s]+", low):
        return None
    if re.fullmatch(r"(mixamorig:)?(left|right)?hand([._\-]?[lr])?", low) or re.fullmatch(
            r"(j_bip_[lr]_hand|bip\d* [lr] hand|[lr]_?hand)", low):
        return 0
    return 1 if "_fk" not in low else 2


def _branches(children):
    """True for a bone the arms or the neck hang from: the upper chest in a plain spine chain."""
    return any(_side(c) is not None or "neck" in c.lower() or "head" in c.lower() for c in children)


def guess_hold_bones(bones):
    """bones: [(name, parent_name_or_None)]. Returns (strap, hand_l, hand_r); '' where nothing fits.

    Hands: a bone named hand or wrist, per side. Strap: the upper chest, by keyword
    (STRAP_KEYWORDS); between equally named spine bones ("spine lower/middle/upper") the one the
    arms or the neck branch from wins, then the one highest up the chain."""
    parent = dict(bones)
    children = {}
    for n, p in bones:
        children.setdefault(p, []).append(n)

    def depth(n):
        d = 0
        while parent.get(n):
            n, d = parent[n], d + 1
        return d

    names = [n for n, _ in bones if _hold_ok(n)]
    strap = ""
    ranked = sorted(((_strap_rank(n), not _branches(children.get(n, ())), -depth(n), n)
                     for n in names if _strap_rank(n) is not None and _side(n) is None))
    if ranked:
        strap = ranked[0][-1]
    hands = {}
    for side in ("L", "R"):
        c = sorted((_hand_rank(n), len(n), n) for n in names if _side(n) == side and _hand_rank(n) is not None)
        hands[side] = c[0][2] if c else ""
    return strap, hands["L"], hands["R"]


# -- Finger bend axis (Autoassign IK limits) -----------------------------------

BEND_AXES = ("X", "-X", "Z", "-Z")
MAX_BEND_DEG = 120.0       # how far one joint may curl during Autoassign
ROOT_SPREAD_DEG = 25.0     # side-to-side freedom of a finger's root (knuckle) joint
KNUCKLE_SWING_DEG = 15.0   # default extra knuckle swing along the instrument (ADR 0015)
THUMB_TURN_DEG = 30.0      # default turn of the thumb's base joint about its own length (ADR 0015)
_MIN_CURL = 0.02           # sin of the summed rest curl below which a chain counts as straight


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def joint_curl(parent_y, child_x, child_y, child_z):
    """Rest curl of one joint, as (x, z): the axis that turns the parent's direction into the
    child's, in the child's bone frame (x along its local X, z along its local Z). Its length is
    the sine of the bend angle; a positive rotation around that axis bends the joint further.

    parent_y: the parent bone's direction; child_x / child_y / child_z: the child's local axes
    (unit vectors in armature space, at rest)."""
    axis = _cross(parent_y, child_y)
    return _dot(axis, child_x), _dot(axis, child_z)


def detect_bend_axis(joints):
    """joints: [(x, z)] rest curls from joint_curl(), for the joints *inside* finger chains
    (not the knuckle, whose parent is the palm). Returns the bend axis in BEND_AXES, or None
    if the fingers are straight at rest (then nothing can be told from the rest pose)."""
    sx = sum(j[0] for j in joints)
    sz = sum(j[1] for j in joints)
    if max(abs(sx), abs(sz)) < _MIN_CURL:
        return None
    if abs(sx) >= abs(sz):
        return "X" if sx > 0 else "-X"
    return "Z" if sz > 0 else "-Z"


def ik_joint_settings(bend_axis, keep_twist=True, root=False, swing_deg=0.0, turn_deg=0.0):
    """Pose-bone IK settings for one finger joint during Autoassign, as {attribute: value}.

    Middle and end joints are hinges: they turn only around the bend axis, and only in the
    curling direction (0..MAX_BEND_DEG from rest). The root joint (knuckle) may also spread
    sideways by ROOT_SPREAD_DEG plus `swing_deg`, the knuckle swing along the instrument
    (fingers lie across the tube, so the knuckle's sideways axis runs along it). Keep Twist
    locks the twist around the bone (Y), except a root given `turn_deg` (the thumb's base
    joint), which may turn that far either way about its own length (ADR 0015)."""
    if bend_axis not in BEND_AXES:
        raise ValueError(f"bend axis must be one of {BEND_AXES}, not {bend_axis!r}")
    bend = bend_axis[-1].lower()
    side = "z" if bend == "x" else "x"
    lo, hi = 0.0, math.radians(MAX_BEND_DEG)
    if bend_axis.startswith("-"):
        lo, hi = -hi, 0.0
    out = {}
    for a in "xyz":
        out[f"lock_ik_{a}"] = False
        out[f"use_ik_limit_{a}"] = False
    out[f"use_ik_limit_{bend}"] = True
    out[f"ik_min_{bend}"], out[f"ik_max_{bend}"] = lo, hi
    if root:
        spread = math.radians(ROOT_SPREAD_DEG + max(0.0, swing_deg))
        out[f"use_ik_limit_{side}"] = True
        out[f"ik_min_{side}"], out[f"ik_max_{side}"] = -spread, spread
    else:
        out[f"lock_ik_{side}"] = True
    if keep_twist:
        if root and turn_deg > 0:
            turn = math.radians(turn_deg)
            out["use_ik_limit_y"] = True
            out["ik_min_y"], out["ik_max_y"] = -turn, turn
        else:
            out["lock_ik_y"] = True
    return out


def locked_axes(bend_axis, keep_twist=True, root=False, turn_deg=0.0):
    """Axes ('x', 'y', 'z') a joint must not turn around after Autoassign."""
    s = ik_joint_settings(bend_axis, keep_twist, root, turn_deg=turn_deg)
    return [a for a in "xyz" if s[f"lock_ik_{a}"]]


# -- Autoassign misses: where to move the hand ---------------------------------

def _unit(v):
    n = math.sqrt(_dot(v, v))
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-12 else None


def tube_axis(points):
    """The instrument's long axis from the key markers, as a unit vector pointing up the tube,
    toward the mouthpiece. points: [(rank, (x, y, z))], rank growing down the tube (the
    profile's slot order: left hand before right, index before pinky). The direction is the
    markers' principal axis; its sign is the one along which the rank falls. None with fewer
    than two distinct points."""
    if len(points) < 2:
        return None
    n = len(points)
    c = tuple(sum(p[i] for _, p in points) / n for i in range(3))
    rel = [(r, (p[0] - c[0], p[1] - c[1], p[2] - c[2])) for r, p in points]
    cov = [[sum(v[i] * v[j] for _, v in rel) for j in range(3)] for i in range(3)]
    if max(abs(cov[i][j]) for i in range(3) for j in range(3)) < 1e-12:
        return None
    axis = (1.0, 1.0, 1.0)                       # power iteration: the largest eigenvector
    for _ in range(60):
        nxt = tuple(sum(cov[i][j] * axis[j] for j in range(3)) for i in range(3))
        u = _unit(nxt)
        if u is None:
            break
        axis = u
    axis = _unit(axis)
    if axis is None:
        return None
    mean_rank = sum(r for r, _ in rel) / n
    corr = sum((r - mean_rank) * _dot(v, axis) for r, v in rel)
    return axis if corr <= 0 else (-axis[0], -axis[1], -axis[2])


def miss_advice(miss, up=None, out=None):
    """One short sentence saying which way to move the hand (or the marker the other way) for a
    fingertip that ends `miss` = target - tip (metres, world) from its target. `up`: unit vector
    up the tube (tube_axis), `out`: unit vector out of the key (the marker's Z). The dominant
    part names the direction; a miss that is mostly round the tube, or with no frame, says
    "toward the key"."""
    total = math.sqrt(_dot(miss, miss))
    if total < 1e-9:
        return ""
    mm = f"{total * 1000:.0f} mm"
    along = _dot(miss, up) if up else 0.0
    outward = _dot(miss, out) if out else 0.0
    if abs(along) >= 0.6 * total:
        way = "up the tube, toward the mouthpiece" if along > 0 else "down the tube, toward the bell"
        return f"move the hand {abs(along) * 1000:.0f} mm {way} (or the marker the other way)"
    if abs(outward) >= 0.6 * total:
        if outward > 0:
            return f"the finger ends {abs(outward) * 1000:.0f} mm inside the key: move the hand that far away from the keys"
        return f"the finger ends {abs(outward) * 1000:.0f} mm short of the key: move the hand that far toward the keys"
    return f"move the hand {mm} toward the key, round the tube (or the marker toward the hand)"
