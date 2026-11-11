"""Note -> finger states -> per-finger key timeline.

A finger state is one of:
    ("down", key)   pressing that key
    ("up", key)     hovering over that key (the last key it pressed, or its home key)
    ("rest",)       the hand's Rest pose
    ("pose", name)  a whole-hand override pose for this note

The timeline is a list of (frame, state) per finger slot. Consecutive keys with different
states form a transition; the Blender layer turns each state into bone values and keys them.
"""

from dataclasses import dataclass, field

HAND = "_hand"     # pseudo slot: hand bones that are not part of any finger
REST = ("rest",)
MIN_STEP = 0.25    # frames: shortest transition when notes come faster than the transition


@dataclass
class NoteMap:
    combination: dict = field(default_factory=dict)   # slot_id -> key (missing = up)
    pose: str = ""                                    # whole-hand override pose name


@dataclass
class TimingParams:
    transition: float = 2.0     # frames a finger takes to move
    lift_lead: float = 1.0      # frames lifting fingers leave before pressing ones arrive
    rest_gap: float = 12.0      # frames of silence after which the hand relaxes to Rest
    use_rest: bool = True


@dataclass
class Timeline:
    keys: dict                  # slot_id -> [(frame, state)]
    missing: list               # written pitches with no mapping
    notes_used: int


def _target(slot, m, last_key):
    if m.pose:
        return ("pose", m.pose)
    if slot == HAND:
        return ("up", None)
    key = m.combination.get(slot)
    return ("down", key) if key else ("up", last_key[slot])


def build_timeline(notes, mapping, slots, homes, params):
    """notes: [(start_frame, end_frame, written_pitch)] monophonic and sorted.
    mapping: {pitch: NoteMap}. slots: slot ids (may include HAND). homes: {slot: home key}."""
    keys = {s: [] for s in slots}
    last_key = {s: homes.get(s) for s in slots}
    initial = REST if params.use_rest else None
    current = {s: initial or ("up", last_key[s]) for s in slots}
    missing = sorted({p for _, _, p in notes if p not in mapping})
    playable = [(s, e, p) for s, e, p in notes if p in mapping]

    def move(slot, state, arrive, duration):
        cur = current[slot]
        if state == cur:
            return
        lst = keys[slot]
        hold = arrive - max(duration, MIN_STEP)
        if lst:
            last = lst[-1][0]
            if arrive <= last + MIN_STEP:
                arrive, hold = last + MIN_STEP, None
            elif hold <= last + MIN_STEP:
                hold = None
        if hold is not None:
            lst.append((hold, cur))
        lst.append((arrive, state))
        current[slot] = state

    tr = params.transition
    prev_end = None
    for start, end, pitch in playable:
        m = mapping[pitch]
        if (prev_end is not None and params.use_rest and start - prev_end > params.rest_gap
                and start - prev_end > 2 * tr + params.lift_lead + 2 * MIN_STEP):
            for slot in slots:
                move(slot, REST, prev_end + tr, tr)
        for slot in slots:
            target = _target(slot, m, last_key)
            cur = current[slot]
            lifting = cur[0] == "down" and target[0] != "down"
            move(slot, target, start - params.lift_lead if lifting else start, tr)
            if target[0] == "down":
                last_key[slot] = target[1]
        prev_end = end
    if prev_end is not None and params.use_rest:
        for slot in slots:
            move(slot, REST, prev_end + tr, tr)
    # A finger that never changes still needs one key, or it would sit in the rig's rest pose
    if playable:
        first = playable[0][0] - tr
        for slot in slots:
            if not keys[slot]:
                keys[slot].append((first, current[slot]))
    return Timeline(keys, missing, len(playable))


def merge_shared(keys, groups):
    """Combine the timelines of finger slots that share one bone chain.

    keys: {slot: [(frame, state)]} from build_timeline. groups: {owner: [slot, ...]}: the slots
    that use the owner's bones, in priority order (the slot listed first wins). Slots in no
    group pass through unchanged.

    Returns {owner: [(frame, slot, state)]}: the chain follows `slot`'s pose for `state`.
    Pressing wins: while any slot of the group presses, the chain is at the Down pose of the
    first listed pressing slot. While none presses, it follows the slot that pressed last (at
    the start, the first listed), so it hovers over the key it left, or rests with the hand."""
    sharers = {sl for group in groups.values() for sl in group}
    out = {}
    for slot, lst in keys.items():
        if slot not in sharers:
            out[slot] = [(f, slot, st) for f, st in lst]
    for owner, group in groups.items():
        group = [sl for sl in group if sl in keys]
        if not group:
            continue
        frames = sorted({f for sl in group for f, _ in keys[sl]})
        own_frames = {sl: {f for f, _ in keys[sl]} for sl in group}

        def state_at(sl, frame):
            lst = keys[sl]
            st = lst[0][1] if lst else REST
            for kf, ks in lst:
                if kf > frame:
                    break
                st = ks
            return st

        chosen, last = [], group[0]
        for f in frames:
            pressing = [sl for sl in group if state_at(sl, f)[0] == "down"]
            if pressing:
                last = pressing[0]
            chosen.append((f, last, state_at(last, f)))
        # keep the chosen slot's own keys (they carry its hold/arrive timing) and a key on both
        # sides of a switch between slots, so a switch moves over the same frames as the slot would
        merged = []
        for i, (f, sl, st) in enumerate(chosen):
            switch = ((i > 0 and chosen[i - 1][1] != sl)
                      or (i + 1 < len(chosen) and chosen[i + 1][1] != sl))
            if i == 0 or f in own_frames[sl] or switch:
                merged.append((f, sl, st))
        out[owner] = merged
    return out


def combination_label(combination, slots):
    """Compact text for UI lists, e.g. 'LT L1 L2 L3 | R1 R4:LowC'. slots: FingerSlot list.
    A finger on its home key shows just the slot id; on another key 'slot:key'."""
    parts = {"L": [], "R": []}
    for s in slots:
        key = combination.get(s.id)
        if key:
            parts[s.side].append(s.id if key == s.keys[0] else f"{s.id}:{key}")
    text = " ".join(parts["L"]) + " | " + " ".join(parts["R"])
    return text.strip() if text.strip() != "|" else "open"
