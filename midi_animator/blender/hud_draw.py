"""Draw the note HUD with gpu/blf: live in the 3D viewport, or offscreen to PNG files."""

import os

import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Matrix

from ..core import hud as core_hud
from . import state

_handle = None


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def hud_inputs(s):
    """(notes [(start_s, end_s, written_pitch)], HudStyle) or (None, None) without a file."""
    data = state.try_load_midi(s)
    if data is None:
        return None, None
    h = s.hud
    notes = [(n.start, n.end, n.pitch + s.transpose) for n in state.performer_notes(s, data)]
    if h.pitch_auto:
        lo, hi = core_hud.fit_pitch_range([p for _, _, p in notes])
    else:
        lo, hi = min(h.pitch_lo, h.pitch_hi), max(h.pitch_lo, h.pitch_hi)
    colors = dict(core_hud.DEFAULT_COLORS)
    colors.update(panel=tuple(h.color_panel), upcoming=tuple(h.color_upcoming),
                  active=tuple(h.color_active), played=tuple(h.color_played),
                  hitline=tuple(h.color_hitline))
    style = core_hud.HudStyle(
        width=h.width, height=h.height, lookahead=h.lookahead, hit_x=h.hit_x,
        pitch_lo=lo, pitch_hi=hi, lane_lines=h.lane_lines, label_size=h.label_size,
        now_size=h.now_size, colors=colors)
    return notes, style


def prims_at_frame(s, scene, frame):
    notes, style = hud_inputs(s)
    if notes is None:
        return None, None
    t = state.time_of(s, scene, frame)
    return core_hud.layout(notes, t, style, lambda p: state.display_name(s, p)), style


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def _rect_tris(x, y, w, h):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)], [(0, 1, 2), (0, 2, 3)]


def draw_prims(prims, style, ox=0.0, oy=0.0, scale=1.0):
    """Draw primitives with the current gpu matrices (pixel space). Rects of the same colour
    are batched; lines are drawn as thin rects (wide GL lines are not portable)."""
    shader = gpu.shader.from_builtin("UNIFORM_COLOR")
    gpu.state.blend_set("ALPHA")

    def color(role, alpha):
        r, g, b, a = style.colors.get(role, (1, 1, 1, 1))
        return (r, g, b, a * alpha)

    def flush(verts, idx, col):
        if verts:
            batch = batch_for_shader(shader, "TRIS", {"pos": verts}, indices=idx)
            shader.bind()
            shader.uniform_float("color", col)
            batch.draw(shader)

    for p in prims:
        if isinstance(p, core_hud.Rect):
            v, i = _rect_tris(ox + p.x * scale, oy + p.y * scale, p.w * scale, p.h * scale)
            flush(v, i, color(p.role, p.alpha))
        elif isinstance(p, core_hud.Line):
            w = max(1.0, p.width * scale)
            if abs(p.x0 - p.x1) < 1e-6:     # vertical
                v, i = _rect_tris(ox + p.x0 * scale - w / 2, oy + min(p.y0, p.y1) * scale,
                                  w, abs(p.y1 - p.y0) * scale)
            else:
                v, i = _rect_tris(ox + min(p.x0, p.x1) * scale, oy + p.y0 * scale - w / 2,
                                  abs(p.x1 - p.x0) * scale, w)
            flush(v, i, color(p.role, p.alpha))
        elif isinstance(p, core_hud.Text):
            size = max(1, int(round(p.size * scale)))
            blf.size(0, size)
            x = ox + p.x * scale
            if p.align == "CENTER":
                x -= blf.dimensions(0, p.text)[0] / 2
            blf.color(0, *color(p.role, p.alpha))
            blf.position(0, x, oy + p.y * scale, 0)
            blf.draw(0, p.text)
    gpu.state.blend_set("NONE")


# ---------------------------------------------------------------------------
# Viewport preview
# ---------------------------------------------------------------------------

def _draw_viewport():
    context = bpy.context
    scene = context.scene
    s = getattr(scene, "midi_animator", None)
    if s is None or not s.hud.preview:
        return
    prims, style = prims_at_frame(s, scene, scene.frame_current + scene.frame_subframe)
    if prims is None:
        return
    region = context.region
    scale = min(s.hud.preview_scale, (region.width - 20) / max(style.width, 1))
    w, h = style.width * scale, style.height * scale
    ox = (region.width - w) / 2
    oy = 10 if s.hud.preview_position == "BOTTOM" else region.height - h - 40
    draw_prims(prims, style, ox, oy, scale)


def enable_preview():
    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(_draw_viewport, (), "WINDOW", "POST_PIXEL")


def disable_preview():
    global _handle
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, "WINDOW")
        _handle = None


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def _ortho(w, h):
    return Matrix(((2.0 / w, 0, 0, -1.0), (0, 2.0 / h, 0, -1.0), (0, 0, 1.0, 0), (0, 0, 0, 1.0)))


def render_frame_pixels(prims, style):
    """Float RGBA pixels (straight alpha, rows bottom-up) for one frame."""
    import numpy as np
    w, h = style.width, style.height
    off = gpu.types.GPUOffScreen(w, h, format="RGBA8")
    try:
        with off.bind():
            fb = gpu.state.active_framebuffer_get()
            fb.clear(color=(0.0, 0.0, 0.0, 0.0))
            with gpu.matrix.push_pop():
                gpu.matrix.load_matrix(Matrix.Identity(4))
                gpu.matrix.load_projection_matrix(_ortho(w, h))
                draw_prims(prims, style)
            buf = fb.read_color(0, 0, w, h, 4, 0, "UBYTE")
        buf.dimensions = w * h * 4
        try:
            px = np.frombuffer(buf, dtype=np.uint8).astype(np.float32)
        except (TypeError, ValueError):
            px = np.array(buf.to_list(), dtype=np.float32)
    finally:
        off.free()
    px = px.reshape(-1, 4) / 255.0
    a = px[:, 3:4]
    np.divide(px[:, :3], a, out=px[:, :3], where=a > 1e-6)   # premultiplied -> straight alpha
    np.clip(px, 0.0, 1.0, out=px)
    return px.ravel()


def export_png_sequence(context, progress=None):
    """Render scene.frame_start..frame_end to <output_dir>/hud_####.png. Returns (folder, count)."""
    scene = context.scene
    s = scene.midi_animator
    folder = bpy.path.abspath(s.hud.output_dir)
    os.makedirs(folder, exist_ok=True)
    notes, style = hud_inputs(s)
    if notes is None:
        raise FileNotFoundError("Choose a valid .mid file first")
    img = bpy.data.images.new("MIDIANIM_HUD_frame", style.width, style.height, alpha=True)
    img.alpha_mode = "STRAIGHT"
    count = 0
    try:
        frames = range(scene.frame_start, scene.frame_end + 1)
        for k, frame in enumerate(frames):
            t = state.time_of(s, scene, frame)
            prims = core_hud.layout(notes, t, style, lambda p: state.display_name(s, p))
            img.pixels.foreach_set(render_frame_pixels(prims, style))
            img.filepath_raw = os.path.join(folder, f"hud_{frame:04d}.png")
            img.file_format = "PNG"
            img.save()
            count += 1
            if progress:
                progress(k / max(len(frames), 1))
    finally:
        bpy.data.images.remove(img)
    return folder, count


def _image_strip_from_sequence(strips, name, folder, frame_start, channel, files):
    strip = strips.new_image(name, os.path.join(folder, files[0]), channel=channel,
                             frame_start=frame_start, fit_method="ORIGINAL")
    for f in files[1:]:
        strip.elements.append(f)
    return strip


def _strips(scene):
    if not scene.sequence_editor:
        scene.sequence_editor_create()
    se = scene.sequence_editor
    return se.strips if hasattr(se, "strips") else se.sequences


def _sequence_files(folder):
    return sorted(f for f in os.listdir(folder) if f.startswith("hud_") and f.endswith(".png"))


def _neutral_view(scene):
    """Show images exactly as stored: no view transform, look, exposure or curves."""
    scene.display_settings.display_device = "sRGB"
    v = scene.view_settings
    v.view_transform, v.look = "Standard", "None"
    v.exposure, v.gamma, v.use_curve_mapping = 0.0, 1.0, False


def _set_enum(owner, attr, value):
    try:
        setattr(owner, attr, value)
    except (TypeError, AttributeError):
        return False
    return getattr(owner, attr) == value


def encode_prores(context, folder):
    """Encode the PNG sequence to ProRes 4444 with alpha through a temporary scene."""
    scene = context.scene
    files = _sequence_files(folder)
    if not files:
        raise FileNotFoundError("Export the PNG sequence first")
    s = scene.midi_animator

    def no_prores(why):
        return (f"This Blender's FFmpeg can't write ProRes 4444 with alpha ({why}). "
                f"The PNG sequence in {folder} is complete: use it instead.")

    tmp = bpy.data.scenes.new("MIDIANIM_HUD_encode")
    try:
        _neutral_view(tmp)          # new scenes default to AgX, which would tone the HUD's colours
        tmp.render.resolution_x, tmp.render.resolution_y = s.hud.width, s.hud.height
        tmp.render.resolution_percentage = 100
        tmp.render.fps, tmp.render.fps_base = scene.render.fps, scene.render.fps_base
        tmp.frame_start, tmp.frame_end = scene.frame_start, scene.frame_start + len(files) - 1
        _image_strip_from_sequence(_strips(tmp), "HUD", folder, scene.frame_start, 1, files)
        r = tmp.render
        if hasattr(r.image_settings, "media_type"):
            r.image_settings.media_type = "VIDEO"
        if not _set_enum(r.image_settings, "file_format", "FFMPEG"):
            raise RuntimeError(no_prores("no FFmpeg output"))
        r.ffmpeg.format = "QUICKTIME"
        if not _set_enum(r.ffmpeg, "codec", "PRORES"):
            raise RuntimeError(no_prores("no ProRes codec"))
        if not _set_enum(r.ffmpeg, "ffmpeg_prores_profile", "4444"):
            raise RuntimeError(no_prores("no 4444 profile"))
        if not _set_enum(r.image_settings, "color_mode", "RGBA"):
            raise RuntimeError(no_prores("no alpha channel"))
        r.use_sequencer = True
        r.filepath = os.path.join(folder, "hud.mov")
        if os.path.isfile(r.filepath):
            os.remove(r.filepath)
        bpy.ops.render.render(animation=True, scene=tmp.name)
        if not os.path.isfile(r.filepath) or os.path.getsize(r.filepath) == 0:
            raise RuntimeError(f"ProRes encoding wrote no {r.filepath}; the PNG sequence is complete")
        return r.filepath
    finally:
        bpy.data.scenes.remove(tmp)


def composite_scene(context, folder):
    """Make '<scene> + HUD': a sequencer scene with this scene's render and the HUD on top,
    at the bottom of the frame. Render that scene to get the video with the HUD burnt in.

    Returns (scene, warning). The composite uses this scene's colour management so the render
    looks the same; the HUD strip is read in the matching display space so the view transform
    cancels on it. warning is set when that can't be exact (the HUD colours get toned)."""
    scene = context.scene
    files = _sequence_files(folder)
    if not files:
        raise FileNotFoundError("Export the PNG sequence first")
    name = f"{scene.name} + HUD"
    old = bpy.data.scenes.get(name)
    if old:
        bpy.data.scenes.remove(old)
    comp = bpy.data.scenes.new(name)
    r, src = comp.render, scene.render
    r.resolution_x, r.resolution_y = src.resolution_x, src.resolution_y
    r.resolution_percentage = src.resolution_percentage
    r.fps, r.fps_base = src.fps, src.fps_base
    comp.frame_start, comp.frame_end = scene.frame_start, scene.frame_end

    sv, cv = scene.view_settings, comp.view_settings
    comp.display_settings.display_device = scene.display_settings.display_device
    cv.view_transform, cv.look = sv.view_transform, sv.look
    cv.exposure, cv.gamma, cv.use_curve_mapping = sv.exposure, sv.gamma, sv.use_curve_mapping
    comp.sequencer_colorspace_settings.name = scene.sequencer_colorspace_settings.name

    strips = _strips(comp)
    strips.new_scene(scene.name, scene, channel=1, frame_start=scene.frame_start)
    hud = _image_strip_from_sequence(strips, "HUD", folder, scene.frame_start, 2, files)
    hud.blend_type = "ALPHA_OVER"
    space, exact, why = core_hud.overlay_colorspace(
        sv.view_transform, sv.look, scene.display_settings.display_device,
        sv.exposure, sv.gamma, sv.use_curve_mapping)
    hud.colorspace_settings.name = space
    # Strip offsets are in full-resolution pixels; the render percentage scales the whole frame
    if hasattr(hud, "transform"):
        hud.transform.offset_y = -(src.resolution_y - scene.midi_animator.hud.height) / 2
    warning = None
    if not exact:
        warning = (f"The HUD colours are toned by this scene's {why}. For exact colours, overlay "
                   f"the exported PNGs or ProRes on your render in a video editor")
    return comp, warning
