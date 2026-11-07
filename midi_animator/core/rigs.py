"""Finger bone-chain detection from bone names (Rigify, Mixamo, VRoid, Unreal, generic)."""

import math
import re

FINGER_WORDS = {
    "thumb": ("thumb",),
    "index": ("index",),
    "middle": ("middle",),
    "ring": ("ring",),
    "pinky": ("pinky", "little", "pinkie"),
}
# Helper / mechanism bones that are not the ones to pose
EXCLUDE = ("org-", "def-", "mch-", "vis_", "master", "tweak", "_ik", ".ik", "ik_", "target",
           "pole", "parent", "socket", "meta", "_end", "nub", "tip")


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
    low = name.lower()
    for finger, words in FINGER_WORDS.items():
        if any(w in low for w in words):
            return finger
    return None


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
        def depth(n, names=names):
            d, p = 0, parent.get(n)
            while p in names:
                d, p = d + 1, parent.get(p)
            return d
        # keep the longest connected chain
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
    return chains


def chains_for_slots(slots, bones):
    """{slot_id: [bone names]} for the profile's finger slots."""
    found = detect_finger_chains(bones)
    return {s.id: found[(s.side, s.finger)] for s in slots if (s.side, s.finger) in found}


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
    if "hand" not in low or "ik" in re.split(r"[._:\-\s]+", low):
        return None
    if re.fullmatch(r"(mixamorig:)?(left|right)?hand([._\-]?[lr])?", low) or re.fullmatch(
            r"(j_bip_[lr]_hand|bip\d* [lr] hand|[lr]_?hand)", low):
        return 0
    return 1 if "_fk" not in low else 2


def guess_hold_bones(bones):
    """bones: [(name, parent_name_or_None)]. Returns (strap, hand_l, hand_r); '' where nothing fits."""
    names = [n for n, _ in bones if _hold_ok(n)]
    strap = ""
    ranked = sorted(((_strap_rank(n), n) for n in names if _strap_rank(n) is not None
                     and _side(n) is None))
    if ranked:
        strap = ranked[0][1]
    hands = {}
    for side in ("L", "R"):
        c = sorted((_hand_rank(n), len(n), n) for n in names if _side(n) == side and _hand_rank(n) is not None)
        hands[side] = c[0][2] if c else ""
    return strap, hands["L"], hands["R"]


# -- Finger bend axis (Autoassign IK limits) -----------------------------------

BEND_AXES = ("X", "-X", "Z", "-Z")
MAX_BEND_DEG = 120.0       # how far one joint may curl during Autoassign
ROOT_SPREAD_DEG = 25.0     # side-to-side freedom of a finger's root (knuckle) joint
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


def ik_joint_settings(bend_axis, keep_twist=True, root=False):
    """Pose-bone IK settings for one finger joint during Autoassign, as {attribute: value}.

    Middle and end joints are hinges: they turn only around the bend axis, and only in the
    curling direction (0..MAX_BEND_DEG from rest). The root joint (knuckle) may also spread
    sideways by ROOT_SPREAD_DEG. Keep Twist locks the twist around the bone (Y)."""
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
        spread = math.radians(ROOT_SPREAD_DEG)
        out[f"use_ik_limit_{side}"] = True
        out[f"ik_min_{side}"], out[f"ik_max_{side}"] = -spread, spread
    else:
        out[f"lock_ik_{side}"] = True
    if keep_twist:
        out["lock_ik_y"] = True
    return out


def locked_axes(bend_axis, keep_twist=True, root=False):
    """Axes ('x', 'y', 'z') a joint must not turn around after Autoassign."""
    s = ik_joint_settings(bend_axis, keep_twist, root)
    return [a for a in "xyz" if s[f"lock_ik_{a}"]]
