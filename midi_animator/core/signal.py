"""Blow signal processing: turn MIDI controller or velocity data into a 0..1 curve per frame.

Pipeline for one effect:
    raw  = sample_hold(events, times)          # or velocity_envelope(notes, times, ...)
    raw  = smooth(raw, times, attack, release)
    x    = shape(raw, peak, threshold, curve)  # 0..1
    x    = plan_breaths(spans, times, x).curve # only in Lung mode
    out  = out_min + (out_max - out_min) * x
"""

import bisect
import math
from dataclasses import dataclass


@dataclass
class BlowParams:
    attack: float = 0.04        # s, rise time constant
    release: float = 0.15       # s, fall time constant
    threshold: float = 0.05     # fraction of full scale ignored as noise
    curve: float = 1.0          # exponent: <1 reacts to soft breath, >1 only to strong
    normalize: bool = True      # loudest value in the take = full
    mode: str = "DIRECT"        # "DIRECT" or "LUNG" (the breath planner, see plan_breaths)
    sustain: float = 0.6        # velocity fallback: level held while the note sounds
    decay: float = 0.2          # velocity fallback: time constant from peak to sustain


def sample_hold(events, times):
    """Value of a step signal [(t, value), ...] (sorted) at each time; 0 before the first event."""
    if not events:
        return [0.0] * len(times)
    ev_t = [e[0] for e in events]
    out = []
    for t in times:
        i = bisect.bisect_right(ev_t, t) - 1
        out.append(float(events[i][1]) if i >= 0 else 0.0)
    return out


def velocity_envelope(notes, times, sustain=0.6, decay=0.2):
    """Synthesised blow from note velocities (0-127 scale): jumps to the velocity at note on,
    decays toward sustain*velocity while held, 0 when no note sounds. Smoothing afterwards
    gives the attack rise and the release tail. notes: [(start, end, velocity)] sorted."""
    starts = [n[0] for n in notes]
    out = []
    for t in times:
        i = bisect.bisect_right(starts, t) - 1
        if i < 0 or t >= notes[i][1]:
            out.append(0.0)
            continue
        start, _end, vel = notes[i]
        k = math.exp(-(t - start) / decay) if decay > 0 else 0.0
        out.append(vel * (sustain + (1.0 - sustain) * k))
    return out


def smooth(values, times, attack, release):
    """One-pole smoothing with separate rise (attack) and fall (release) time constants."""
    out, y, prev = [], None, None
    for x, t in zip(values, times):
        if y is None:
            y = x
        else:
            dt = max(t - prev, 1e-6)
            tau = attack if x > y else release
            y += (x - y) * (1.0 if tau <= 0 else 1.0 - math.exp(-dt / tau))
        prev = t
        out.append(y)
    return out


def shape(values, peak, threshold, curve):
    """0-127 values -> 0..1 with threshold and response curve."""
    peak = max(float(peak), 1.0)
    out = []
    for v in values:
        x = min(max(v / peak, 0.0), 1.0)
        x = 0.0 if x <= threshold else (x - threshold) / (1.0 - threshold)
        out.append(x ** curve)
    return out


# --- breathing: the breath planner ------------------------------------------------------------
# Lung volume 0..1 (1 = full). The player breathes in at every break and drains in proportion to the
# blow. One rule, one fitted number: the lung size, the smallest one that never runs under RESERVE.

INHALE_RATE = 3.0       # lungs per second a player can breathe in (empty to full in a third of a second)
RESERVE = 0.15          # the plan never goes under this
MIN_GAP = 0.10          # s, shortest note gap that is a breath point
DIP = 0.12              # blow under this, inside a legato run, is a breath point too
DIP_MIN = 0.12          # s the blow has to stay under DIP
EDGE = 0.02             # s kept clear after a note ends and before the next starts
PREP = 0.7              # s of preparation breath before a first note that comes late
TIDAL_LEVEL = 0.5       # after the last note: slow breathing around this level...
TIDAL_DEPTH = 0.08      # ...this deep
TIDAL_PERIOD = 4.0      # s per breath
TIDAL_TAU = 0.5         # s to settle onto the tidal curve
LUNG_MIN, LUNG_MAX = 2.0, 60.0      # s of full blow that empty the lungs: the fit's search range


@dataclass
class Breath:
    t0: float
    t1: float
    start: float        # lung volume before
    end: float          # and after
    kind: str           # "break" (gap or dip in the music) or "prep" (before the first note)


@dataclass
class BreathPlan:
    curve: list         # lung volume per time
    breaths: list       # [Breath]
    lung_size: float    # s of full blow that empty the lungs (fitted)
    minimum: float      # lowest volume while the notes play


def spans_from_blow(x, times, level=0.02):
    """[(start, end)] where a blow curve is above `level`: stands in for note times when only the
    blow is known."""
    spans, t0 = [], None
    for v, t in zip(x, times):
        if v > level and t0 is None:
            t0 = t
        elif v <= level and t0 is not None:
            spans.append((t0, t))
            t0 = None
    if t0 is not None:
        spans.append((t0, times[-1]))
    return spans


def _index(times, dt):
    def idx(t):
        return min(max(int(round((t - times[0]) / dt)), 0), len(times) - 1)
    return idx


def _breath_points(spans, times, blow, dt):
    idx = _index(times, dt)
    cands = []
    for (_s0, e0), (s1, _e1) in zip(spans, spans[1:]):
        if s1 - e0 >= MIN_GAP:
            cands.append([e0 + EDGE, s1 - EDGE])
        else:
            low = [i for i in range(idx(e0 - 0.15), idx(s1 + 0.15)) if blow[i] < DIP]
            if len(low) * dt >= DIP_MIN - 1e-9:
                cands.append([times[low[0]], times[low[-1]] + dt])
    cands.sort()
    merged = []
    for c in cands:
        if merged and c[0] <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], c[1])
        else:
            merged.append(list(c))
    return [(a, b) for a, b in merged if b - a >= MIN_GAP]


def _run(size, points, first, last, times, blow, dt):
    """Plan the breaths for a lung that empties in `size` s of full blow. Returns (breaths, curve)."""
    idx = _index(times, dt)

    def air(t0, t1):
        return sum(blow[idx(t0):idx(t1)]) * dt / size

    v0 = 1.0 if first < 0.6 else 0.55
    v, t_prev, breaths = v0, first, []
    if first >= 0.6:                         # a late first note: breathe in before it
        breaths.append(Breath(first - PREP, first - EDGE, v0, 0.95, "prep"))
        v = 0.95
    for t0, t1 in points:
        v -= air(t_prev, t0)
        amount = min(1.0 - v, INHALE_RATE * (t1 - t0))
        if amount > 0.02:
            breaths.append(Breath(t0, t1, v, v + amount, "break"))
            v += amount
        t_prev = t1

    curve, v, k = [], v0, 0
    tidal = 1.0 - math.exp(-dt / TIDAL_TAU)
    for i, t in enumerate(times):
        while k < len(breaths) and t > breaths[k].t1:
            k += 1
        b = breaths[k] if k < len(breaths) and breaths[k].t0 <= t else None
        if b:
            u = (t - b.t0) / max(b.t1 - b.t0, 1e-6)
            v = b.start + (b.end - b.start) * (u * u * (3 - 2 * u))
        elif t > last + 0.3:                 # slow tidal breathing after the last note
            goal = TIDAL_LEVEL + TIDAL_DEPTH * math.sin(2 * math.pi * (t - last - 0.3) / TIDAL_PERIOD)
            v += (goal - v) * tidal
        elif i:
            v -= blow[i] * dt / size
        curve.append(max(v, 0.0))
    return breaths, curve


def plan_breaths(spans, times, blow, reserve=RESERVE):
    """Lung volume per time for a take. `spans` are the notes [(start, end)], `times` the sample
    times (evenly spaced, seconds) and `blow` the shaped blow 0..1 at those times.

    At every breath point (a gap of at least MIN_GAP between notes, or a dip of the blow inside a
    legato run) the player breathes in toward full lungs, as fast as INHALE_RATE and the gap allow,
    eased. Between breath points the lungs drain in proportion to the blow. The lung size (seconds of
    full blow that empty them) is fitted, by bisection, to the smallest one whose volume stays at or
    above `reserve` while the notes play. After the last note the player breathes slowly and evenly.
    Returns a BreathPlan."""
    if len(times) < 2:
        return BreathPlan([TIDAL_LEVEL] * len(times), [], LUNG_MAX, TIDAL_LEVEL)
    dt = (times[-1] - times[0]) / (len(times) - 1)
    spans = sorted((float(a), float(b)) for a, b in spans if b > a)
    if not spans:                                       # no notes: tidal breathing throughout
        curve = [TIDAL_LEVEL + TIDAL_DEPTH * math.sin(2 * math.pi * (t - times[0]) / TIDAL_PERIOD)
                 for t in times]
        return BreathPlan(curve, [], LUNG_MAX, min(curve))
    first, last = spans[0][0], max(b for _, b in spans)
    points = _breath_points(spans, times, blow, dt)
    playing = max(1, min(len(times), int(round((last - times[0]) / dt))))

    def minimum(size):
        return min(_run(size, points, first, last, times, blow, dt)[1][:playing])

    lo, hi = LUNG_MIN, LUNG_MAX
    for _ in range(40):
        mid = (lo + hi) / 2
        if minimum(mid) >= reserve - 0.005:
            hi = mid
        else:
            lo = mid
    size = round(hi + 0.05, 1)
    breaths, curve = _run(size, points, first, last, times, blow, dt)
    return BreathPlan(curve, breaths, size, min(curve[:playing]))


def blow_curve(times, params, events=None, notes=None, spans=None):
    """0..1 per time from controller events [(t, 0-127)] or, if events is None, from notes
    [(start, end, velocity)] via the velocity envelope. In Lung mode the result is the planned
    lung volume (plan_breaths); `spans` are the note times [(start, end)] it breathes between
    (default: the notes, else where the blow is up)."""
    if events is not None:
        raw = sample_hold(events, times)
        peak = max((v for _, v in events), default=127) if params.normalize else 127.0
    else:
        notes = notes or []
        raw = velocity_envelope(notes, times, params.sustain, params.decay)
        peak = max((n[2] for n in notes), default=127) if params.normalize else 127.0
    raw = smooth(raw, times, params.attack, params.release)
    x = shape(raw, peak, params.threshold, params.curve)
    if params.mode == "LUNG":
        if spans is None:
            spans = [(n[0], n[1]) for n in notes] if notes else spans_from_blow(x, times)
        x = plan_breaths(spans, times, x).curve
    return x


def remap(x, out_min, out_max):
    return [out_min + (out_max - out_min) * v for v in x]
