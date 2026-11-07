"""Finger bone-chain detection from bone names (Rigify, Mixamo, VRoid, Unreal, generic)."""

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
