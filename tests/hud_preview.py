"""Render HUD frames with Pillow (outside Blender) to check the layout.

    python tests/hud_preview.py examples/aerophone_sample.mid out_dir [time ...]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from midi_animator.core import hud as H  # noqa: E402
from midi_animator.core import midi as M  # noqa: E402
from midi_animator.core.notes import note_name  # noqa: E402


def _font(size):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, max(1, int(size)))
    return ImageFont.load_default()


def render(prims, style):
    img = Image.new("RGBA", (style.width, style.height), (0, 0, 0, 0))
    H_ = style.height

    def rgba(role, alpha):
        r, g, b, a = style.colors[role]
        return int(r * 255), int(g * 255), int(b * 255), int(a * alpha * 255)

    for p in prims:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        if isinstance(p, H.Rect):
            d.rectangle([p.x, H_ - (p.y + p.h), p.x + p.w, H_ - p.y], fill=rgba(p.role, p.alpha))
        elif isinstance(p, H.Line):
            d.line([p.x0, H_ - p.y0, p.x1, H_ - p.y1], fill=rgba(p.role, p.alpha), width=int(p.width))
        elif isinstance(p, H.Text):
            f = _font(p.size)
            w = d.textlength(p.text, font=f)
            x = p.x - w / 2 if p.align == "CENTER" else p.x
            d.text((x, H_ - p.y - p.size), p.text, font=f, fill=rgba(p.role, p.alpha))
        img = Image.alpha_composite(img, layer)
    return img


def main():
    path, out = sys.argv[1], sys.argv[2]
    times = [float(t) for t in sys.argv[3:]] or [0.3, 4.9, 7.5]
    m = M.parse_midi(path)
    notes = [(n.start, n.end, n.pitch) for n in M.monophonic(m.notes)]
    lo, hi = H.fit_pitch_range([n[2] for n in notes])
    style = H.HudStyle(width=1280, height=300, pitch_lo=lo, pitch_hi=hi)
    os.makedirs(out, exist_ok=True)
    for t in times:
        img = render(H.layout(notes, t, style, note_name), style)
        bg = Image.new("RGBA", img.size, (90, 120, 90, 255))      # stand-in for the video
        Image.alpha_composite(bg, img).save(os.path.join(out, f"hud_{t:05.2f}.png"))
    print("wrote", sorted(os.listdir(out)))


if __name__ == "__main__":
    main()
