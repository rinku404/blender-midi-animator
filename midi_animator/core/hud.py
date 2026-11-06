"""Note HUD layout: what to draw at time t, as backend-neutral primitives in pixels
(origin bottom-left). Blender draws them with gpu/blf; tests draw them with Pillow.

Layout: a "now playing" band on top (note name pops when it starts, held time counts up)
and a horizontal highway below. Notes scroll right -> left toward the hit line; pitch is
vertical; bar length is the note's duration. Upcoming bars are dim, the sounding bar lights
up and fills while held, played bars stay at full length and fade out to the left.
"""

import math
from dataclasses import dataclass, field

DEFAULT_COLORS = {
    "panel": (0.04, 0.05, 0.08, 0.55),
    "lane_alt": (1.0, 1.0, 1.0, 0.05),
    "lane_line": (1.0, 1.0, 1.0, 0.10),
    "hitline": (1.0, 0.85, 0.3, 0.95),
    "upcoming": (0.30, 0.65, 1.00, 0.85),
    "active": (1.00, 0.80, 0.25, 1.00),
    "active_fill": (1.00, 0.95, 0.70, 1.00),
    "played": (0.55, 0.55, 0.60, 0.70),
    "label": (1.0, 1.0, 1.0, 1.0),
    "label_dark": (0.05, 0.05, 0.08, 1.0),
    "now": (1.0, 0.92, 0.55, 1.0),
    "timer": (1.0, 1.0, 1.0, 0.85),
}

BLACK_KEYS = {1, 3, 6, 8, 10}


@dataclass
class HudStyle:
    width: int = 1920
    height: int = 360
    lookahead: float = 3.0          # seconds visible to the right of the hit line
    hit_x: float = 0.22             # hit line position, fraction of width
    now_band: float = 0.26          # fraction of height reserved for the "now playing" band
    pitch_lo: int = 58
    pitch_hi: int = 89
    lane_lines: bool = True
    label_size: float = 0.07        # bar label font size, fraction of height
    min_bar: float = 0.095          # minimum bar height, fraction of height
    now_size: float = 0.17          # "now playing" font size, fraction of height
    fade_played: bool = True
    colors: dict = field(default_factory=lambda: dict(DEFAULT_COLORS))


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    role: str
    alpha: float = 1.0


@dataclass
class Line:
    x0: float
    y0: float
    x1: float
    y1: float
    role: str
    width: float = 2.0
    alpha: float = 1.0


@dataclass
class Text:
    x: float
    y: float
    size: float
    text: str
    role: str
    align: str = "LEFT"     # LEFT or CENTER (x is the left edge or the centre)
    alpha: float = 1.0


def fit_pitch_range(pitches, min_span=12):
    """Pitch range that covers the notes with a semitone of margin, at least min_span wide."""
    if not pitches:
        return 60, 60 + min_span - 1
    lo, hi = min(pitches) - 1, max(pitches) + 1
    grow_low = True
    while hi - lo + 1 < min_span:
        if grow_low:
            lo -= 1
        else:
            hi += 1
        grow_low = not grow_low
    return lo, hi


def text_width(text, size):
    """Rough width for layout decisions (backends measure exactly when they draw)."""
    return 0.6 * size * len(text)


def layout(notes, t, style, name_fn):
    """notes: [(start_s, end_s, written_pitch)] sorted by start. name_fn(pitch) -> str."""
    W, H = float(style.width), float(style.height)
    prims = [Rect(0, 0, W, H, "panel")]

    top = H * (1.0 - style.now_band)          # highway occupies 0 .. top
    lo, hi = style.pitch_lo, max(style.pitch_hi, style.pitch_lo)
    lanes = hi - lo + 1
    lane_h = top / lanes
    hit = W * style.hit_x
    pps = (W - hit) / max(style.lookahead, 0.1)
    past = hit / pps

    for i in range(lanes):
        y = i * lane_h
        if (lo + i) % 12 in BLACK_KEYS:
            prims.append(Rect(0, y, W, lane_h, "lane_alt"))
        if style.lane_lines and (lo + i) % 12 == 0:      # a line under every C
            prims.append(Line(0, y, W, y, "lane_line", 1.0))
    prims.append(Line(hit, 0, hit, top, "hitline", 3.0))

    # Bars may be taller than a lane (one note sounds at a time, so they rarely touch)
    bar_h = max(lane_h * 0.76, H * style.min_bar)
    label_px = H * style.label_size
    active = None
    for start, end, pitch in notes:
        if end < t - past or start > t + style.lookahead:
            continue
        if pitch < lo or pitch > hi:
            continue
        x0 = hit + (start - t) * pps
        x1 = max(hit + (end - t) * pps, x0 + 2.0)
        h = bar_h
        y = min(max((pitch - lo + 0.5) * lane_h - h / 2, 0.0), top - h)
        cx0, cx1 = max(x0, 0.0), min(x1, W)
        if cx1 <= cx0:
            continue
        if t < start:
            role, alpha = "upcoming", 1.0
        elif t < end:
            role, alpha = "active", 1.0
            active = (start, end, pitch)
        else:
            role = "played"
            alpha = max(0.2, 1.0 - (t - end) / past) if style.fade_played else 1.0
        prims.append(Rect(cx0, y, cx1 - cx0, h, role, alpha))
        if role == "active":
            prims.append(Rect(cx0, y, max(0.0, min(hit, cx1) - cx0), h, "active_fill"))
        name = name_fn(pitch)
        size = min(label_px, h * 0.9)
        if size >= 6 and text_width(name, size) + 6 <= cx1 - cx0:
            prims.append(Text(cx0 + 4, y + (h - size) / 2, size, name,
                              "label_dark" if role == "active" else "label", "LEFT", alpha))

    if active:
        start, end, pitch = active
        held = t - start
        pop = 1.0 + 0.3 * math.exp(-held / 0.12)
        size = H * style.now_size * pop
        band_mid = top + (H - top) / 2
        prims.append(Text(hit, band_mid - size * 0.45, size, name_fn(pitch), "now", "CENTER"))
        tsize = H * style.now_size * 0.45
        prims.append(Text(hit + text_width(name_fn(pitch), H * style.now_size) / 2 + 24,
                          band_mid - tsize * 0.45, tsize, f"{held:.1f}s", "timer", "LEFT"))
    return prims
