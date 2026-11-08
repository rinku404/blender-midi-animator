"""HUD checks that need Blender's UI (a GPU context), so run it WITH a window:

    blender --factory-startup --python tests/test_hud_in_ui.py

The work runs from a timer once the window is up. Results go to tests/out/hud_ui_result.json
(one entry per check), images to tests/out/. Blender quits when done; exit code 0 = all passed.

Checks: PNG export (30 RGBA frames, straight alpha, gold "active" pixels at the hit line), the
GPU render against tests/hud_preview.py's Pillow render (bars within 3 px; needs a system Python
with Pillow on PATH), ProRes 4444 encode (alpha kept, decoded frame equals the PNG) and its clear
error without ProRes, the composite scene (strips, offset, colours under Standard / ACES 2.0 / AgX,
a 50% render), the viewport preview (draw handler runs without errors and draws), and a
screenshot of panel 2's Hold box (tests/out/hold_box.png, for a person to look at).
"""
import glob
import json
import os
import shutil
import struct
import subprocess
import sys
import traceback

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import midi_animator  # noqa: E402
from midi_animator.blender import hud_draw, state, ui  # noqa: E402
from midi_animator.core import hud as core_hud  # noqa: E402

MID = os.path.join(ROOT, "examples", "aerophone_sample.mid")
OUT = os.path.join(ROOT, "tests", "out")
HUD_DIR = os.path.join(OUT, "hud")
W, H = 1280, 300
FRAMES = 30
COMPARE_FRAME = 20          # t = 0.79 s: one played, one active and several upcoming bars

RESULT = {"blender": bpy.app.version_string, "checks": [], "errors": []}


def check(name, ok, **info):
    RESULT["checks"].append({"name": name, "ok": bool(ok), **info})
    print(("PASS " if ok else "FAIL ") + name, info if info else "")


def step(fn):
    """Run one group of checks; an exception fails that group but not the others."""
    try:
        fn()
    except Exception:
        tb = traceback.format_exc()
        RESULT["errors"].append({"step": fn.__name__, "traceback": tb})
        check(fn.__name__ + " (ran without exception)", False, error=tb.strip().splitlines()[-1])
        print(tb)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ui_context():
    win = bpy.context.window_manager.windows[0]
    area = next(a for a in win.screen.areas if a.type == "VIEW_3D")
    region = next(r for r in area.regions if r.type == "WINDOW")
    return win, area, region


def override(area_type="VIEW_3D"):
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == area_type), win.screen.areas[0])
    region = next(r for r in area.regions if r.type == "WINDOW")
    return bpy.context.temp_override(window=win, screen=win.screen, area=area, region=region)


def png_header(path):
    """(width, height, bit_depth, colour_type) from the IHDR chunk; colour type 6 = RGBA."""
    with open(path, "rb") as f:
        head = f.read(33)
    assert head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR", path
    w, h, depth, ctype = struct.unpack(">IIBB", head[16:26])
    return w, h, depth, ctype


def load_pixels(path):
    """numpy (h, w, 4) floats, row 0 = bottom (Blender's order), values as stored in the file."""
    import numpy as np
    img = bpy.data.images.load(path, check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"    # read the stored values, no conversion
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
    finally:
        bpy.data.images.remove(img)
    return px.reshape(h, w, 4)


def bar_mask(px, hit_x, top):
    """Pixels of the bars: in the highway and more opaque than the panel and its lanes.
    The hit line's columns are cut out (it is drawn over the bars)."""
    mask = px[:, :, 3] > 0.70                      # panel 0.55, lanes <= 0.62, bars >= 0.75 here
    mask[int(top) - 2:, :] = False                 # highway only (the "now playing" band is above)
    mask[:, max(0, int(hit_x) - 4):int(hit_x) + 5] = False
    return mask


def dilate(mask, r):
    import numpy as np
    h, w = mask.shape
    p = np.pad(mask, r)
    out = np.zeros_like(mask)
    for dy in range(2 * r + 1):
        for dx in range(2 * r + 1):
            out |= p[dy:dy + h, dx:dx + w]
    return out


def mask_distance(a, b, limit=8):
    """Smallest r such that each mask lies within r px of the other (None if more than limit)."""
    for r in range(limit + 1):
        if not (a & ~dilate(b, r)).any() and not (b & ~dilate(a, r)).any():
            return r
    return None


def column_runs(row):
    """[(x0, x1)] runs of True in a 1-D mask."""
    runs, start = [], None
    for x, v in enumerate(row.tolist() + [False]):
        if v and start is None:
            start = x
        elif not v and start is not None:
            runs.append((start, x - 1))
            start = None
    return runs


def find_python():
    for name in ("python", "python3", "py"):
        exe = shutil.which(name)
        if exe and "blender" not in exe.lower():
            return exe
    return None


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------

def setup():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(HUD_DIR)
    bpy.context.preferences.view.show_splash = False      # it would cover the screenshots
    # Open panel 2 so the Hold box shows in the screenshot (it is closed by default)
    ui.MIDIANIM_PT_fingers.bl_options = set()
    midi_animator.register()

    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = 24, 1.0
    scene.frame_start, scene.frame_end = 1, FRAMES
    s = scene.midi_animator
    s.midi_path = MID
    h = s.hud
    h.width, h.height = W, H
    h.output_dir = HUD_DIR + os.sep

    # A small Rigify-named rig and an instrument, so the Hold box shows its bone pickers filled
    arm_data = bpy.data.armatures.new("Rig")
    arm = bpy.data.objects.new("Rig", arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    with override():
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm_data.edit_bones
        spine = eb.new("spine")
        spine.head, spine.tail = (0, 0, 0), (0, 0, 1)
        chest = eb.new("chest")
        chest.head, chest.tail, chest.parent = (0, 0, 1), (0, 0, 1.4), spine
        for side, x in (("L", 0.3), ("R", -0.3)):
            fore = eb.new(f"forearm.{side}")
            fore.head, fore.tail, fore.parent = (x, -0.25, 1.3), (x, 0, 1.3), chest
            hand = eb.new(f"hand.{side}")
            hand.head, hand.tail, hand.parent = (x, 0, 1.3), (x, 0.1, 1.3), fore
        bpy.ops.object.mode_set(mode="OBJECT")
    sax = bpy.data.objects.new("Sax", None)
    scene.collection.objects.link(sax)
    s.rig, s.instrument = arm, sax
    with override():
        bpy.ops.midianim.guess_hold_bones()
    RESULT["hold_bones"] = [s.hold_strap_bone, s.hold_hand_l, s.hold_hand_r]


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def png_export():
    import numpy as np
    s = bpy.context.scene.midi_animator
    s.hud.output_format = "PNG"
    with override():
        res = bpy.ops.midianim.hud_export()
    check("export operator finished", res == {"FINISHED"}, result=sorted(res))
    files = sorted(glob.glob(os.path.join(HUD_DIR, "hud_*.png")))
    check("export wrote 30 PNGs", len(files) == FRAMES, count=len(files),
          first=os.path.basename(files[0]) if files else None,
          last=os.path.basename(files[-1]) if files else None)

    headers = {png_header(f) for f in files}
    check("every PNG is 8-bit RGBA at the configured size", headers == {(W, H, 8, 6)},
          headers=sorted(headers))

    _, style = hud_draw.hud_inputs(s)
    panel = style.colors["panel"]
    hit = W * style.hit_x
    top = H * (1.0 - style.now_band)
    active = np.array(style.colors["active"][:3])
    bad_bg, gold = [], {}
    for f in files:
        px = load_pixels(f)
        # The panel spans the frame; where nothing else is drawn (the "now" band's right end)
        # each pixel must carry the panel's own alpha and colour (straight, not premultiplied).
        bg = px[H - 6:H - 2, W - 200:W - 4].reshape(-1, 4)
        if (np.abs(bg[:, 3] - panel[3]).max() > 2.5 / 255
                or np.abs(bg[:, :3] - np.array(panel[:3])).max() > 3.5 / 255):
            bad_bg.append(os.path.basename(f))
        near = px[: int(top), int(hit) - 40:int(hit) + 40]
        is_gold = (np.abs(near[:, :, :3] - active).max(axis=2) < 0.06) & (near[:, :, 3] > 0.97)
        gold[os.path.basename(f)] = int(is_gold.sum())
    check("background pixels carry the panel's straight alpha/colour in every frame", not bad_bg,
          panel_rgba=[round(c, 3) for c in panel], bad_frames=bad_bg)
    frames_with_gold = [k for k, v in gold.items() if v > 50]
    check("at least one frame has active gold pixels near the hit line", bool(frames_with_gold),
          frames_with_gold=len(frames_with_gold), max_gold_px=max(gold.values()) if gold else 0)

    # Transparency where nothing is drawn: same frame with a fully transparent panel
    s.hud.color_panel[3] = 0.0
    try:
        prims, style0 = hud_draw.prims_at_frame(s, bpy.context.scene, COMPARE_FRAME)
        px = np.array(hud_draw.render_frame_pixels(prims, style0)).reshape(H, W, 4)
    finally:
        s.hud.color_panel[3] = panel[3]
    corner = px[H - 6:H - 2, W - 200:W - 4, 3]
    check("with panel alpha 0, empty areas are fully transparent (alpha 0)", float(corner.max()) == 0.0,
          max_alpha=float(corner.max()), transparent_fraction=round(float((px[:, :, 3] == 0).mean()), 3))


def pillow_compare():
    s = bpy.context.scene.midi_animator
    scene = bpy.context.scene
    t = state.time_of(s, scene, COMPARE_FRAME)
    gpu_png = os.path.join(HUD_DIR, f"hud_{COMPARE_FRAME:04d}.png")
    pil_png = os.path.join(OUT, f"pillow_{COMPARE_FRAME:04d}.png")
    py = find_python()
    check("system Python found for the Pillow render", py is not None, python=py)
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import hud_preview; "
            "hud_preview.frame(sys.argv[2], float(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])).save(sys.argv[6])")
    proc = subprocess.run([py, "-c", code, os.path.join(ROOT, "tests"), MID, repr(t), str(W), str(H), pil_png],
                          capture_output=True, text=True)
    check("Pillow render ran", proc.returncode == 0 and os.path.isfile(pil_png),
          stderr=proc.stderr.strip()[-300:])

    _, style = hud_draw.hud_inputs(s)
    hit, top = W * style.hit_x, H * (1.0 - style.now_band)
    a = bar_mask(load_pixels(gpu_png), hit, top)
    b = bar_mask(load_pixels(pil_png), hit, top)
    dist = mask_distance(a, b)
    # Each bar's runs along a row near its top edge (clear of the label), for the report
    prims, _ = hud_draw.prims_at_frame(s, scene, COMPARE_FRAME)
    bars = [p for p in prims if isinstance(p, core_hud.Rect) and p.role in ("upcoming", "active", "played")]
    rows = sorted({int(p.y + p.h - 3) for p in bars})
    check("GPU and Pillow renders have the same bars within 3 px",
          len(bars) >= 3 and a.sum() > 1000 and dist is not None and dist <= 3,
          time_s=round(t, 4), bars_in_layout=len(bars), bar_px_gpu=int(a.sum()), bar_px_pillow=int(b.sum()),
          differing_px=int((a ^ b).sum()), max_edge_distance_px=dist,
          runs_gpu={r: column_runs(a[r]) for r in rows}, runs_pillow={r: column_runs(b[r]) for r in rows})


def prores():
    import numpy as np
    s = bpy.context.scene.midi_animator
    s.hud.output_format = "PRORES"
    try:
        with override():
            res = bpy.ops.midianim.hud_export()
    finally:
        s.hud.output_format = "PNG"
    mov = os.path.join(HUD_DIR, "hud.mov")
    size = os.path.getsize(mov) if os.path.isfile(mov) else 0
    check("ProRes export finished and hud.mov is over 0 bytes", res == {"FINISHED"} and size > 0,
          result=sorted(res), bytes=size)
    if not size:
        return
    with open(mov, "rb") as f:
        data = f.read()
    i = data.find(b"ap4h")             # ProRes 4444 sample entry; depth 32 = with alpha
    depth = struct.unpack(">H", data[i + 4 + 74:i + 4 + 76])[0] if i >= 0 else None
    check("hud.mov is ProRes 4444 with an alpha channel (ap4h, depth 32)", i >= 0 and depth == 32,
          fourcc_found=i >= 0, depth=depth)

    # Decode one frame back through Blender's ffmpeg and compare with the PNG
    img = bpy.data.images.load(mov, check_existing=False)
    try:
        img.colorspace_settings.name = "Non-Color"
        w, h = img.size
        px = np.empty(w * h * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        px = px.reshape(h, w, 4)
    finally:
        bpy.data.images.remove(img)
    ref = load_pixels(os.path.join(HUD_DIR, "hud_0001.png"))
    ok_size = (w, h) == (W, H)
    diff_a = float(np.abs(px[:, :, 3] - ref[:, :, 3]).mean()) if ok_size else None
    diff_rgb = float(np.abs(px[:, :, :3] - ref[:, :, :3]).mean()) if ok_size else None
    check("decoded ProRes frame 1 matches hud_0001.png (mean abs diff < 0.02, alpha kept)",
          ok_size and diff_a < 0.02 and diff_rgb < 0.02,
          size=[w, h], mean_alpha_diff=diff_a, mean_rgb_diff=diff_rgb,
          corner_alpha=float(px[h - 3, w - 3, 3]) if ok_size else None)


def prores_unavailable():
    """Without ProRes 4444 + alpha, export must stop with a clear message, not a traceback."""
    s = bpy.context.scene.midi_animator
    real = hud_draw._set_enum
    hud_draw._set_enum = lambda owner, attr, value: False if attr == "codec" else real(owner, attr, value)
    msg, res = None, set()
    try:
        try:
            hud_draw.encode_prores(bpy.context, HUD_DIR)
        except RuntimeError as e:
            msg = str(e)
        s.hud.output_format = "PRORES"
        with override():
            res = bpy.ops.midianim.hud_export()
    except RuntimeError as e:          # bpy.ops raises RuntimeError when an operator reports an ERROR
        res = {"CANCELLED (error reported)"}
        RESULT["prores_operator_error"] = str(e).strip()
    finally:
        hud_draw._set_enum = real
        s.hud.output_format = "PNG"
    check("without a ProRes codec, export stops with a clear message",
          msg is not None and "can't write ProRes 4444" in msg and "PNG sequence" in msg
          and res != {"FINISHED"}, message=msg, operator_result=sorted(res),
          operator_error=RESULT.get("prores_operator_error"))


def composite():
    import numpy as np
    scene = bpy.context.scene
    s = scene.midi_animator
    with override():
        res = bpy.ops.midianim.hud_composite()
    comp = bpy.data.scenes.get(f"{scene.name} + HUD")
    check("composite operator finished and created the scene", res == {"FINISHED"} and comp is not None,
          result=sorted(res))
    if comp is None:
        return
    strips = list(comp.sequence_editor.strips)
    sc = [x for x in strips if x.type == "SCENE"]
    im = [x for x in strips if x.type == "IMAGE"]
    check("composite has a scene strip and a HUD image strip above it",
          len(strips) == 2 and len(sc) == 1 and len(im) == 1 and sc[0].scene == scene
          and im[0].channel > sc[0].channel,
          strips=[(x.name, x.type, x.channel) for x in strips])
    if not (sc and im):
        return
    hud = im[0]
    out_h = scene.render.resolution_y * scene.render.resolution_percentage / 100
    expect = -(out_h - H) / 2
    check("HUD strip is ALPHA_OVER, 30 frames, offset to the bottom",
          hud.blend_type == "ALPHA_OVER" and hud.frame_final_duration == FRAMES
          and abs(hud.transform.offset_y - expect) < 1e-3 and hud.frame_final_start == scene.frame_start,
          blend=hud.blend_type, frames=hud.frame_final_duration, offset_y=hud.transform.offset_y,
          expected_offset_y=expect, start=hud.frame_final_start)

    check("HUD strip colour space follows the scene's view (factory AgX -> AgX Base sRGB)",
          hud.colorspace_settings.name == "AgX Base sRGB"
          and comp.view_settings.view_transform == scene.view_settings.view_transform,
          view=comp.view_settings.view_transform, strip_colorspace=hud.colorspace_settings.name)

    # Colours, per view: above the HUD the composite must equal a direct render of the scene, and
    # the HUD's gold must come out within 2% where the view can be cancelled (otherwise: a warning).
    ref = load_pixels(os.path.join(HUD_DIR, f"hud_{COMPARE_FRAME:04d}.png"))
    _, style = hud_draw.hud_inputs(s)
    gold = np.array(style.colors["active"][:3])
    gy, gx = [int(np.median(v)) for v in np.nonzero(
        (np.abs(ref[:, :, :3] - gold).max(axis=2) < 0.01) & (ref[:, :, 3] > 0.99))]
    old_view = scene.view_settings.view_transform
    try:
        for view, exact in (("Standard", True), ("ACES 2.0", True), ("AgX", False)):
            scene.view_settings.view_transform = view
            tag = view.replace(" ", "_")
            direct = render(scene, COMPARE_FRAME, f"scene_{tag}.png")
            comp, warning = hud_draw.composite_scene(bpy.context, HUD_DIR)
            name = "comp.png" if view == "Standard" else f"comp_{tag}.png"
            c = render(comp, COMPARE_FRAME, name)
            x0 = (c.shape[1] - W) // 2
            above = float(np.abs(c[H:] - direct[H:]).mean())
            got = c[gy, x0 + gx, :3]
            err = float(np.abs(got - gold).max())
            alpha = ref[:, :, 3:4]
            expect = ref[:, :, :3] * alpha + direct[:H, x0:x0 + W, :3] * (1 - alpha)
            hud_diff = float(np.abs(c[:H, x0:x0 + W, :3] - expect).mean())
            info = dict(view=view, strip_colorspace=comp.sequence_editor.strips["HUD"].colorspace_settings.name,
                        scene_vs_direct_mean_diff=round(above, 5), gold=[round(float(v), 3) for v in got],
                        gold_max_err=round(err, 3), hud_region_mean_diff=round(hud_diff, 4), warning=warning,
                        image=f"tests/out/{name}")
            if exact:
                check(f"composite ({view}): scene as rendered directly, HUD gold within 2%, no warning",
                      above < 0.002 and err <= 0.02 and warning is None, **info)
            else:
                check(f"composite ({view}): scene as rendered directly, and a warning that the HUD is toned",
                      above < 0.002 and warning is not None and view in warning, **info)
    finally:
        scene.view_settings.view_transform = old_view

    # Render percentage: the HUD must still sit at the bottom (strip offsets are in full-size pixels)
    pct = scene.render.resolution_percentage
    scene.render.resolution_percentage = 50
    scene.view_settings.view_transform = "Standard"      # untoned hit-line colour to look for
    try:
        comp, _ = hud_draw.composite_scene(bpy.context, HUD_DIR)
        c = render(comp, COMPARE_FRAME, "comp_50pct.png")
    finally:
        scene.render.resolution_percentage = pct
        scene.view_settings.view_transform = old_view
    col = int(round(((scene.render.resolution_x - W) / 2 + W * style.hit_x) / 2))
    hitline = np.array(style.colors["hitline"][:3])
    near = (np.abs(c[:, col - 2:col + 3, :3] - hitline).max(axis=2) < 0.12).any(axis=1)
    gold_rows = np.nonzero(near)[0]
    top = H * (1.0 - style.now_band) / 2
    check("composite at 50%: the HUD's hit line runs from the bottom edge up to the band",
          len(gold_rows) > 0 and gold_rows.min() <= 2 and abs(gold_rows.max() - top) <= 4,
          frame=[c.shape[1], c.shape[0]], column=col,
          gold_rows=[int(gold_rows.min()), int(gold_rows.max())] if len(gold_rows) else None,
          expected_rows=[0, round(top, 1)])


def render(scn, frame, name):
    scn.frame_current = frame
    path = os.path.join(OUT, name)
    scn.render.filepath = path
    scn.render.image_settings.file_format = "PNG"
    scn.render.image_settings.color_mode = "RGBA"
    with override():
        bpy.ops.render.render(write_still=True, scene=scn.name)
    return load_pixels(path)


def viewport_preview():
    import numpy as np
    s = bpy.context.scene.midi_animator
    calls, errors = [], []
    # Swap the registered handler for a wrapper that calls the real one and records exceptions
    hud_draw.disable_preview()

    def wrapped():
        calls.append(1)
        try:
            hud_draw._draw_viewport()
        except Exception:
            errors.append(traceback.format_exc())

    handle = bpy.types.SpaceView3D.draw_handler_add(wrapped, (), "WINDOW", "POST_PIXEL")
    try:
        s.hud.preview = True
        bpy.context.scene.frame_set(1)
        win, area, region = ui_context()
        area.tag_redraw()
        with override():
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=3)
        shot = os.path.join(OUT, "viewport.png")
        with override():
            bpy.ops.screen.screenshot(filepath=shot)
    finally:
        bpy.types.SpaceView3D.draw_handler_remove(handle, "WINDOW")
        hud_draw.enable_preview()
    check("viewport draw handler ran without Python errors", calls and not errors,
          draw_calls=len(calls), errors=[e.strip().splitlines()[-1] for e in errors])
    # The preview shows in the 3D view: look for the hit line's gold in the bottom of its region
    px = load_pixels(shot)
    _, style = hud_draw.hud_inputs(s)
    reg = px[region.y:region.y + 200, region.x:region.x + region.width, :3]
    near = np.abs(reg - np.array(style.colors["hitline"][:3])).max(axis=2) < 0.12
    check("viewport screenshot shows the HUD (hit-line gold at the bottom of the 3D view)", near.sum() > 30,
          gold_px=int(near.sum()), screenshot="tests/out/viewport.png")


def hold_box_screenshot():
    win, area, region = ui_context()
    space = area.spaces.active
    space.show_region_ui = True
    side = next(r for r in area.regions if r.type == "UI")
    with override():
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    side.active_panel_category = "MIDI"
    area.tag_redraw()
    with override():
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=3)
    shot = os.path.join(OUT, "hold_box.png")
    with override():
        bpy.ops.screen.screenshot_area(filepath=shot)
    check("Hold box screenshot written (look at it)", os.path.isfile(shot),
          screenshot="tests/out/hold_box.png", sidebar_width=side.width, category=side.active_panel_category,
          hold_bones=RESULT.get("hold_bones"))


# ---------------------------------------------------------------------------

def run():
    try:
        step(png_export)
        step(pillow_compare)
        step(prores)
        step(prores_unavailable)
        step(composite)
        step(viewport_preview)
        step(hold_box_screenshot)
    finally:
        RESULT["all_passed"] = all(c["ok"] for c in RESULT["checks"]) and not RESULT["errors"]
        with open(os.path.join(OUT, "hud_ui_result.json"), "w", encoding="utf-8") as f:
            json.dump(RESULT, f, indent=2)
        print("ALL HUD UI CHECKS PASSED" if RESULT["all_passed"] else "HUD UI CHECKS FAILED")
        sys.stdout.flush()
        code = 0 if RESULT["all_passed"] else 1
        try:
            midi_animator.unregister()
        except Exception:
            traceback.print_exc()
        os._exit(code)      # quit_blender would keep the default exit code
    return None


if bpy.app.background:
    print("test_hud_in_ui.py needs a window: run it without -b")
    sys.exit(2)

try:
    setup()
except Exception:
    traceback.print_exc()
    os.makedirs(OUT, exist_ok=True)
    RESULT["errors"].append({"step": "setup", "traceback": traceback.format_exc()})
    RESULT["all_passed"] = False
    with open(os.path.join(OUT, "hud_ui_result.json"), "w", encoding="utf-8") as f:
        json.dump(RESULT, f, indent=2)
    os._exit(1)
bpy.app.timers.register(run, first_interval=2.0)
