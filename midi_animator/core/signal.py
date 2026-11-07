"""Blow signal processing: turn MIDI controller or velocity data into a 0..1 curve per frame.

Pipeline for one effect:
    raw  = sample_hold(events, times)          # or velocity_envelope(notes, times, ...)
    raw  = smooth(raw, times, attack, release)
    x    = shape(raw, peak, threshold, curve)  # 0..1
    x    = lung(x, times, ...)                 # only in Lung mode
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
    mode: str = "DIRECT"        # "DIRECT" or "LUNG"
    lung_capacity: float = 6.0  # s of full blow that empties the lungs
    refill_time: float = 0.35   # s time constant to refill during rests
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


def lung(intensity, times, capacity=6.0, refill_time=0.35, rest_level=0.02):
    """Lung volume 0..1 (1 = full). Blowing at intensity x drains x/capacity per second;
    below rest_level the player inhales and the lungs refill exponentially. Starts full,
    so the chest is already expanded before the first phrase."""
    out, v, prev = [], 1.0, None
    drain = 1.0 / max(capacity, 1e-3)
    for x, t in zip(intensity, times):
        if prev is not None:
            dt = max(t - prev, 0.0)
            if x > rest_level:
                v -= x * drain * dt
            else:
                v += (1.0 - v) * (1.0 - math.exp(-dt / max(refill_time, 1e-3)))
            v = min(max(v, 0.0), 1.0)
        prev = t
        out.append(v)
    return out


def blow_curve(times, params, events=None, notes=None):
    """0..1 per time from controller events [(t, 0-127)] or, if events is None, from notes
    [(start, end, velocity)] via the velocity envelope."""
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
        x = lung(x, times, params.lung_capacity, params.refill_time)
    return x


def remap(x, out_min, out_max):
    return [out_min + (out_max - out_min) * v for v in x]
