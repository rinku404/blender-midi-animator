"""Finger bone setup and key markers."""

import bmesh
import bpy
from mathutils import Matrix, Vector

from ..core import rigs
from . import state

SLOT_PROP = "midianim_slot"
KEY_PROP = "midianim_key"


# -- fingers -----------------------------------------------------------------

def sync_finger_slots(s):
    """Make s.fingers match the profile's slots (keeps bones already chosen)."""
    prof = state.profile(s)
    existing = {f.slot: f for f in s.fingers}
    if [f.slot for f in s.fingers] == [sl.id for sl in prof.slots]:
        for f, sl in zip(s.fingers, prof.slots):     # same slots (sax <-> clarinet): keep them, relabel
            if f.label != sl.label:
                f.label = sl.label
        return
    # every per-finger field goes here, or a rebuild (slot ids changed) drops it
    saved = {k: ([b.bone for b in f.bones], f.up_pose, f.shares, f.tilt) for k, f in existing.items()}
    s.fingers.clear()
    for sl in prof.slots:
        f = s.fingers.add()
        f.slot, f.label = sl.id, sl.label
        bones, up, shares, tilt = saved.get(sl.id, ([], None, "", 0.0))
        for b in bones:
            f.bones.add().bone = b
        f.up_pose = up
        f.shares, f.tilt = shares, tilt


def _set_bones(f, names):
    f.bones.clear()
    for b in names:
        f.bones.add().bone = b


def detect_fingers(s):
    """Fill every finger slot from the rig's bone names. A finger the hand doesn't have shares a
    found finger's bones; a missing thumb gets the hand bone with a press tilt (core.rigs.assign_slots).
    Slots that get nothing keep what they had. Returns (labels of those, the SlotAssignment)."""
    sync_finger_slots(s)
    arm = s.rig
    bones = [(b.name, b.parent.name if b.parent else None) for b in arm.data.bones]
    asg = rigs.assign_slots(state.profile(s).slots, bones)
    missing = []
    for f in s.fingers:
        if f.slot in asg.chains:
            _set_bones(f, asg.chains[f.slot])
            f.shares, f.tilt = "", 0.0
        elif f.slot in asg.shares:
            _set_bones(f, [])
            f.shares, f.tilt = asg.shares[f.slot], 0.0
        elif f.slot in asg.tilt_hands:
            _set_bones(f, [asg.tilt_hands[f.slot]])
            f.shares = ""
            if not f.tilt:
                f.tilt = rigs.THUMB_TILT_DEG
        else:
            missing.append(f.label)
    return missing, asg


def share_owner(s, slot_id):
    """The slot whose bones `slot_id` moves: itself when it has its own, else the slot it shares
    (following shares of shares), or None when the link is broken or circular."""
    by_slot = {f.slot: f for f in s.fingers}
    seen, cur = set(), slot_id
    while cur in by_slot and by_slot[cur].shares and cur not in seen:
        seen.add(cur)
        cur = by_slot[cur].shares
    return cur if cur in by_slot and not by_slot[cur].shares else None


def finger_bones(s):
    """{slot: [bone names root -> tip]} for slots whose bones exist on the rig. A slot that shares
    another slot's bones lists that chain (the same list object), so every slot in a group
    resolves to one chain."""
    arm = s.rig
    own = {}
    for f in s.fingers:
        if f.shares:
            continue
        names = [b.bone for b in f.bones if b.bone and arm and b.bone in arm.pose.bones]
        if names:
            own[f.slot] = names
    out = {}
    for f in s.fingers:
        owner = share_owner(s, f.slot) if f.shares else f.slot
        if owner in own:
            out[f.slot] = own[owner]
    return out


def share_groups(s):
    """{owner slot: [slot, ...]} for every chain, slots in list order (the first listed has
    priority when they disagree). Single-slot chains are included."""
    bones = finger_bones(s)
    groups = {}
    for f in s.fingers:
        if f.slot in bones:
            groups.setdefault(share_owner(s, f.slot), []).append(f.slot)
    return groups


def tilt_slots(s):
    """Slots whose press is the first bone's tilt (no markers, no IK)."""
    bones = finger_bones(s)
    return {f.slot for f in s.fingers if f.tilt and not f.shares and f.slot in bones}


def _rest_curls(arm, chain):
    """Rest curl (x, z) of each joint inside a finger chain (see core.rigs.joint_curl)."""
    out = []
    for parent, child in zip(chain, chain[1:]):
        pm = arm.data.bones[parent].matrix_local.to_3x3()
        cx, cy, cz = (tuple(arm.data.bones[child].matrix_local.to_3x3().col[i].normalized()) for i in range(3))
        out.append(rigs.joint_curl(tuple(pm.col[1].normalized()), cx, cy, cz))
    return out


def detect_bend_axis(s):
    """Set s.bend_axis from the fingers' rest curl. Returns (axis or None, [finger labels that
    curl around another axis]). None = the fingers are straight at rest; s.bend_axis is kept."""
    bones = finger_bones(s)
    labels = {f.slot: f.label for f in s.fingers}
    joints, per_finger, seen = [], {}, set()
    for slot, chain in bones.items():
        if tuple(chain) in seen:            # a shared chain counts once
            continue
        seen.add(tuple(chain))
        curls = _rest_curls(s.rig, chain)
        joints += curls
        per_finger[slot] = rigs.detect_bend_axis(curls)
    axis = rigs.detect_bend_axis(joints)
    if axis is None:
        return None, []
    s.bend_axis = axis
    odd = [labels.get(sl, sl) for sl, a in per_finger.items() if a is not None and a != axis]
    return axis, odd


# -- key markers -------------------------------------------------------------

def marker_name(slot, key):
    return f"Key.{slot}.{key}"


def find_markers(scene=None):
    """{(slot, key): marker object} for every key marker in the file."""
    out = {}
    for obj in bpy.data.objects:
        slot, key = obj.get(SLOT_PROP), obj.get(KEY_PROP)
        if slot and key:
            out[(slot, key)] = obj
    return out


def _placement(context):
    """World matrix for a new marker: selected vertices (Edit Mode, Z = their normal)
    or the 3D cursor (its location and rotation)."""
    obj = context.edit_object
    if obj and obj.type == "MESH":
        bm = bmesh.from_edit_mesh(obj.data)
        verts = [v for v in bm.verts if v.select]
        if verts:
            mw = obj.matrix_world
            loc = mw @ (sum((v.co for v in verts), Vector()) / len(verts))
            normal = sum((v.normal for v in verts), Vector())
            normal = (mw.to_3x3().inverted().transposed() @ normal)
            if normal.length < 1e-6:
                normal = Vector((0, 0, 1))
            rot = normal.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
            return Matrix.Translation(loc) @ rot
    cur = context.scene.cursor
    return Matrix.Translation(cur.location) @ cur.rotation_euler.to_matrix().to_4x4()


def add_marker(context, s, slot, key):
    name = marker_name(slot, key)
    old = find_markers().get((slot, key))
    world = _placement(context)
    if old is not None:
        marker = old
    else:
        marker = bpy.data.objects.new(name, None)
        marker.empty_display_type = "SINGLE_ARROW"
        marker[SLOT_PROP] = slot
        marker[KEY_PROP] = key
        coll = s.instrument.users_collection[0] if s.instrument and s.instrument.users_collection \
            else context.scene.collection
        coll.objects.link(marker)
    marker.empty_display_size = s.marker_size * 3
    if s.instrument and marker.parent != s.instrument:
        marker.parent = s.instrument
    marker.matrix_world = world
    return marker
