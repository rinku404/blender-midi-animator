"""Operators."""

import os

import bpy
from bpy.props import BoolProperty, EnumProperty, IntProperty, StringProperty

from ..core import hud as core_hud
from ..core import midi as core_midi
from ..core.notes import note_name
from . import actions, autoassign, bake, hold, hud_draw, rig, state


def _err(op, e):
    op.report({"ERROR"}, str(e))
    return {"CANCELLED"}


# ---------------------------------------------------------------------------
# MIDI & audio
# ---------------------------------------------------------------------------

class MIDIANIM_OT_analyze(bpy.types.Operator):
    """Read the MIDI file: tracks, the performer's notes, blow data, and what is still missing"""
    bl_idname = "midianim.analyze"
    bl_label = "Analyze MIDI"

    def execute(self, context):
        s = state.settings(context)
        try:
            data = state.load_midi(s)
        except Exception as e:
            return _err(self, e)
        rig.sync_finger_slots(s)
        s.tracks.clear()
        s.report.clear()

        def line(text, icon="NONE"):
            item = s.report.add()
            item.text, item.icon = text, icon

        line(f"{len(data.notes)} notes, {data.length:.1f} s, {len(data.tracks)} tracks", "FILE_SOUND")
        for ti, tname in enumerate(data.tracks):
            tn = [n for n in data.notes if n.track == ti]
            if not tn:
                continue
            pitches = sorted({n.pitch for n in tn})
            chans = ",".join(str(c) for c in sorted({n.channel + 1 for n in tn}))
            t = s.tracks.add()
            t.index = ti
            t.label = (f"{ti}: {tname} · ch {chans} · {len(tn)} notes · "
                       f"{note_name(pitches[0])}–{note_name(pitches[-1])}")

        notes = state.performer_notes(s, data)
        written = sorted({n.pitch + s.transpose for n in notes})
        if not notes:
            line("The performer track/channel has no notes", "ERROR")
        else:
            line(f"Performer: {len(notes)} notes, written {note_name(written[0])}–{note_name(written[-1])}",
                 "USER")
        summary = data.controllers_summary(s.performer_track, s.performer_channel)
        if summary:
            line("Controllers: " + ", ".join(f"{core_midi.controller_label(k, n)} ({c})"
                                             for k, n, c in summary[:5]), "DRIVER")
        else:
            line("No controller data (blow can only come from velocity)", "INFO")

        for e in s.effects:
            events, notes_, label, problem = bake.effect_source(s, e, data)
            e.missing = bool(problem) and e.if_missing == "ASK"
            e.status = problem or f"uses {label}"

        mapped = {m.pitch for m in s.notes}
        unmapped = [p for p in written if p not in mapped]
        if unmapped:
            line("Unmapped notes: " + ", ".join(note_name(p) for p in unmapped), "ERROR")

        markers = rig.find_markers()
        needed_keys = set()
        for m in s.notes:
            if m.pitch in written and not m.pose:
                needed_keys.update(state.parse_combination(m.combination).items())
        no_marker = sorted(f"{sl} {k}" for sl, k in needed_keys if (sl, k) not in markers)
        if no_marker:
            line("Keys without a marker: " + ", ".join(no_marker), "ERROR")
        no_pose = sorted(f"{sl} {k}" for sl, k in needed_keys
                         if (sl, k) in markers and not bpy.data.actions.get(autoassign.pose_name(sl, k, True)))
        if no_pose:
            line("Keys without poses (run Autoassign): " + ", ".join(no_pose), "ERROR")
        if not unmapped and not no_marker and not no_pose and notes:
            line("Everything this file needs is set up", "CHECKMARK")
        self.report({"INFO"}, s.report[0].text)
        return {"FINISHED"}


class MIDIANIM_OT_set_performer_track(bpy.types.Operator):
    """Use this track as the performer"""
    bl_idname = "midianim.set_performer_track"
    bl_label = "Use Track"
    bl_options = {"REGISTER", "UNDO"}
    track: IntProperty()

    def execute(self, context):
        s = state.settings(context)
        s.performer_track = self.track
        return bpy.ops.midianim.analyze()


class MIDIANIM_OT_set_scene_range(bpy.types.Operator):
    """Set the scene frame range to cover the whole MIDI file"""
    bl_idname = "midianim.set_scene_range"
    bl_label = "Fit Scene Range"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        try:
            data = state.load_midi(s)
        except Exception as e:
            return _err(self, e)
        scene = context.scene
        scene.frame_start = s.start_frame
        scene.frame_end = int(state.frame_of(s, scene, data.length)) + int(state.fps(scene))
        return {"FINISHED"}


class MIDIANIM_OT_add_audio(bpy.types.Operator):
    """Add the audio file to the Video Sequencer at the start frame for playback sync"""
    bl_idname = "midianim.add_audio"
    bl_label = "Add Audio"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        path = bpy.path.abspath(s.audio_path)
        if not os.path.isfile(path):
            self.report({"ERROR"}, "Choose an audio file first")
            return {"CANCELLED"}
        scene = context.scene
        strip = hud_draw._strips(scene).new_sound("MIDI Audio", path, channel=1, frame_start=s.start_frame)
        scene.sync_mode = "AUDIO_SYNC"
        self.report({"INFO"}, f"Added {strip.name}")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Fingers & key markers
# ---------------------------------------------------------------------------

class MIDIANIM_OT_detect_fingers(bpy.types.Operator):
    """Find each finger's bones from the rig's bone names (Rigify, Mixamo, VRoid, ...)"""
    bl_idname = "midianim.detect_fingers"
    bl_label = "Detect Fingers"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return state.settings(context).rig is not None

    def execute(self, context):
        s = state.settings(context)
        missing = rig.detect_fingers(s)
        if missing:
            self.report({"WARNING"}, "Not found, pick bones by hand: " + ", ".join(missing))
        else:
            self.report({"INFO"}, f"Found all {len(s.fingers)} fingers")
        return {"FINISHED"}


class MIDIANIM_OT_guess_hold_bones(bpy.types.Operator):
    """Fill the strap and hand bones from the rig's bone names"""
    bl_idname = "midianim.guess_hold_bones"
    bl_label = "Guess Bones"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return state.settings(context).rig is not None

    def execute(self, context):
        missing = hold.guess_bones(state.settings(context))
        if missing:
            self.report({"WARNING"}, "Not found, pick by hand: " + ", ".join(missing))
        return {"FINISHED"}


class MIDIANIM_OT_lock_hands(bpy.types.Operator):
    """Hang the instrument from the strap bone and lock both hands onto it with IK, keeping the
    current pose. Pose the hold first (instrument at the lips, hands on the keys), then click this"""
    bl_idname = "midianim.lock_hands"
    bl_label = "Lock"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        problem = hold.check(s)
        if problem:
            return _err(self, problem)
        self.report({"INFO"}, hold.lock_hands(context, s))
        return {"FINISHED"}


class MIDIANIM_OT_unlock_hands(bpy.types.Operator):
    """Remove the hand IK, rotation constraints and targets (the instrument stays on the strap)"""
    bl_idname = "midianim.unlock_hands"
    bl_label = "Unlock"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = hold.unlock_hands(context, state.settings(context))
        self.report({"INFO"}, f"Removed {n} hold constraints")
        return {"FINISHED"}


class MIDIANIM_OT_finger_bone_add(bpy.types.Operator):
    """Add a bone slot to the selected finger (bones go root to tip)"""
    bl_idname = "midianim.finger_bone_add"
    bl_label = "Add Bone"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        rig.sync_finger_slots(s)
        if 0 <= s.finger_index < len(s.fingers):
            s.fingers[s.finger_index].bones.add()
        return {"FINISHED"}


class MIDIANIM_OT_finger_bone_remove(bpy.types.Operator):
    bl_idname = "midianim.finger_bone_remove"
    bl_label = "Remove Bone"
    bl_options = {"REGISTER", "UNDO"}
    index: IntProperty()

    def execute(self, context):
        s = state.settings(context)
        if 0 <= s.finger_index < len(s.fingers):
            f = s.fingers[s.finger_index]
            if 0 <= self.index < len(f.bones):
                f.bones.remove(self.index)
        return {"FINISHED"}


class MIDIANIM_OT_add_marker(bpy.types.Operator):
    """Place this key's marker at the selected vertices (Edit Mode: Z follows their normal)
    or at the 3D cursor. Markers become children of the instrument"""
    bl_idname = "midianim.add_marker"
    bl_label = "Place Key Marker"
    bl_options = {"REGISTER", "UNDO"}
    slot: StringProperty()
    key: StringProperty()

    def execute(self, context):
        s = state.settings(context)
        if s.instrument is None:
            self.report({"WARNING"}, "Set the Instrument first so markers move with it")
        m = rig.add_marker(context, s, self.slot, self.key)
        self.report({"INFO"}, f"Placed {m.name}")
        return {"FINISHED"}


class MIDIANIM_OT_select_marker(bpy.types.Operator):
    """Select this key marker"""
    bl_idname = "midianim.select_marker"
    bl_label = "Select Marker"
    slot: StringProperty()
    key: StringProperty()

    def execute(self, context):
        m = rig.find_markers().get((self.slot, self.key))
        if m is None or context.mode != "OBJECT":
            return {"CANCELLED"}
        for o in context.selected_objects:
            o.select_set(False)
        m.select_set(True)
        context.view_layer.objects.active = m
        return {"FINISHED"}


class MIDIANIM_OT_autoassign(bpy.types.Operator):
    """Solve each finger onto its key markers (Down) and above them (Up) and save the
    results as pose assets. Poses you edited or locked are kept unless Overwrite Locked is on"""
    bl_idname = "midianim.autoassign"
    bl_label = "Autoassign Finger Poses"
    bl_options = {"REGISTER", "UNDO"}
    only_selected: BoolProperty(name="Only Selected Finger", default=False)

    @classmethod
    def poll(cls, context):
        return state.settings(context).rig is not None

    def execute(self, context):
        s = state.settings(context)
        rig.sync_finger_slots(s)
        only = s.fingers[s.finger_index].slot if self.only_selected and s.fingers else None
        created, skipped, problems = autoassign.autoassign(context, s, only)
        msg = f"{created} poses created"
        if skipped:
            msg += f", {skipped} locked kept"
        if problems:
            msg += " | " + "; ".join(problems)
        self.report({"WARNING"} if problems else {"INFO"}, msg)
        return {"FINISHED"}


class MIDIANIM_OT_toggle_lock(bpy.types.Operator):
    """Lock or unlock a generated pose (locked poses are kept by Autoassign)"""
    bl_idname = "midianim.toggle_lock"
    bl_label = "Toggle Lock"
    bl_options = {"REGISTER", "UNDO"}
    action: StringProperty()

    def execute(self, context):
        act = bpy.data.actions.get(self.action)
        if act is None:
            return {"CANCELLED"}
        if autoassign.is_locked(act):
            act[autoassign.LOCK_PROP] = False
            act[autoassign.HASH_PROP] = autoassign._fingerprint(actions.pose_values(act))
        else:
            act[autoassign.LOCK_PROP] = True
        return {"FINISHED"}


class MIDIANIM_OT_apply_pose(bpy.types.Operator):
    """Apply a pose to the rig so you can look at it or tweak it"""
    bl_idname = "midianim.apply_pose"
    bl_label = "Apply Pose"
    bl_options = {"REGISTER", "UNDO"}
    action: StringProperty()

    def execute(self, context):
        s = state.settings(context)
        act = bpy.data.actions.get(self.action)
        if s.rig is None or act is None:
            return {"CANCELLED"}
        for (path, idx), v in actions.pose_values(act).items():
            try:
                owner, prop = path.rsplit(".", 1)
                getattr(s.rig.path_resolve(owner), prop)[idx] = v
            except Exception:
                pass
        return {"FINISHED"}


class MIDIANIM_OT_save_pose(bpy.types.Operator):
    """Save the selected pose bones as a pose asset (for Rest, Up overrides or whole-hand poses)"""
    bl_idname = "midianim.save_pose"
    bl_label = "Save Pose Asset"
    bl_options = {"REGISTER", "UNDO"}
    name: StringProperty(name="Name", default="Rest")
    use_as: EnumProperty(name="Use As", items=[
        ("NONE", "Just Save", ""), ("REST", "Rest Pose", ""),
        ("UP", "Selected Finger's Up Pose", ""), ("NOTE", "Active Note's Whole-hand Pose", "")],
        default="REST")

    @classmethod
    def poll(cls, context):
        return context.mode == "POSE" and context.selected_pose_bones

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        s = state.settings(context)
        arm = context.active_object
        chans = []
        for pb in context.selected_pose_bones:
            chans += [(p, i, [(1.0, v)]) for (p, i), v in actions.bone_channels(pb).items()]
        act = actions.build_action(arm, self.name, chans, "CONSTANT", fake_user=True, replace=True)
        act.asset_mark()
        if self.use_as == "REST":
            s.rest_pose = act
        elif self.use_as == "UP" and s.fingers:
            s.fingers[s.finger_index].up_pose = act
        elif self.use_as == "NOTE" and 0 <= s.note_index < len(s.notes):
            s.notes[s.note_index].pose = act
        self.report({"INFO"}, f"Saved pose asset '{act.name}'")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Note map
# ---------------------------------------------------------------------------

class MIDIANIM_OT_fill_from_chart(bpy.types.Operator):
    """Fill the note map from the instrument's built-in fingering chart"""
    bl_idname = "midianim.fill_from_chart"
    bl_label = "Fill From Chart"
    bl_options = {"REGISTER", "UNDO"}
    which: EnumProperty(items=[
        ("FILE", "Notes in This File", "Only the written notes the performer plays"),
        ("ALL", "Whole Chart", "Every note in the chart")], default="FILE")
    overwrite: BoolProperty(name="Overwrite Existing", default=False)

    def execute(self, context):
        s = state.settings(context)
        prof = state.profile(s)
        if self.which == "FILE":
            try:
                data = state.load_midi(s)
            except Exception as e:
                return _err(self, e)
            pitches = sorted({n.pitch + s.transpose for n in state.performer_notes(s, data)})
        else:
            pitches = sorted(prof.chart)
        added, unknown = 0, []
        for p in pitches:
            combo = prof.combination_for(p)
            if combo is None:
                unknown.append(note_name(p))
                continue
            row = state.find_note(s, p)
            if row is not None and not self.overwrite:
                continue
            if row is None:
                row = s.notes.add()
                row.pitch = p
            row.combination = state.format_combination(combo)
            added += 1
        _sort_notes(s)
        msg = f"Filled {added} notes"
        if unknown:
            msg += " | not in the chart (map by hand): " + ", ".join(unknown)
        self.report({"WARNING"} if unknown else {"INFO"}, msg)
        return {"FINISHED"}


def _sort_notes(s):
    order = sorted(range(len(s.notes)), key=lambda i: s.notes[i].pitch)
    for target, _ in enumerate(order):
        cur = min(range(target, len(s.notes)), key=lambda i: s.notes[i].pitch)
        if cur != target:
            s.notes.move(cur, target)


class MIDIANIM_OT_note_add(bpy.types.Operator):
    """Add a note to the map"""
    bl_idname = "midianim.note_add"
    bl_label = "Add Note"
    bl_options = {"REGISTER", "UNDO"}
    pitch: IntProperty(name="Written Note", default=62, min=0, max=127)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "pitch")
        self.layout.label(text=note_name(self.pitch))

    def execute(self, context):
        s = state.settings(context)
        row = state.find_note(s, self.pitch)
        if row is None:
            row = s.notes.add()
            row.pitch = self.pitch
            _sort_notes(s)
        s.note_index = next(i for i, m in enumerate(s.notes) if m.pitch == self.pitch)
        return {"FINISHED"}


class MIDIANIM_OT_note_remove(bpy.types.Operator):
    bl_idname = "midianim.note_remove"
    bl_label = "Remove Note"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        if 0 <= s.note_index < len(s.notes):
            s.notes.remove(s.note_index)
            s.note_index = max(0, s.note_index - 1)
        return {"FINISHED"}


class MIDIANIM_OT_set_finger(bpy.types.Operator):
    """Set what this finger does for the active note"""
    bl_idname = "midianim.set_finger"
    bl_label = "Set Finger"
    bl_options = {"REGISTER", "UNDO"}
    slot: StringProperty()
    key: StringProperty(description="Key to press; empty = up")

    def execute(self, context):
        s = state.settings(context)
        if not (0 <= s.note_index < len(s.notes)):
            return {"CANCELLED"}
        m = s.notes[s.note_index]
        combo = state.parse_combination(m.combination)
        if self.key:
            combo[self.slot] = self.key
        else:
            combo.pop(self.slot, None)
        m.combination = state.format_combination(combo)
        return {"FINISHED"}


class MIDIANIM_OT_copy_fingering(bpy.types.Operator):
    """Copy the active note's fingering"""
    bl_idname = "midianim.copy_fingering"
    bl_label = "Copy Fingering"

    def execute(self, context):
        s = state.settings(context)
        if 0 <= s.note_index < len(s.notes):
            m = s.notes[s.note_index]
            s.clipboard = m.combination + "|" + (m.pose.name if m.pose else "")
        return {"FINISHED"}


class MIDIANIM_OT_paste_fingering(bpy.types.Operator):
    """Paste the copied fingering onto the active note"""
    bl_idname = "midianim.paste_fingering"
    bl_label = "Paste Fingering"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        if not s.clipboard or not (0 <= s.note_index < len(s.notes)):
            return {"CANCELLED"}
        combo, _, pose = s.clipboard.partition("|")
        m = s.notes[s.note_index]
        m.combination = combo
        m.pose = bpy.data.actions.get(pose) if pose else None
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Blow effects
# ---------------------------------------------------------------------------

def _guess_bone(arm, keywords):
    if not arm or arm.type != "ARMATURE":
        return ""
    names = [b.name for b in arm.pose.bones]
    for kw in keywords:
        for n in names:
            if n.lower().replace("mixamorig:", "") == kw:
                return n
    for kw in keywords:
        for n in names:
            if kw in n.lower() and not n.lower().startswith(("org-", "mch-", "def-")):
                return n
    return ""


class MIDIANIM_OT_effect_add(bpy.types.Operator):
    """Add a blow effect"""
    bl_idname = "midianim.effect_add"
    bl_label = "Add Blow Effect"
    bl_options = {"REGISTER", "UNDO"}
    preset: StringProperty(default="")

    def execute(self, context):
        s = state.settings(context)
        e = s.effects.add()
        preset = next((p for p in state.profile(s).presets if p.id == self.preset), None)
        obj = context.active_object
        if preset is None:
            e.name = f"Effect {len(s.effects)}"
            e.target = obj
        else:
            e.name = preset.label
            e.target_type = preset.target_type
            e.mode = preset.mode
            e.out_min, e.out_max = preset.out_min, preset.out_max
            e.attack, e.release, e.curve = preset.attack, preset.release, preset.curve
            if preset.target_type == "SHAPE_KEY":
                e.shape_key = preset.shape_key
                mesh = obj if obj and obj.type == "MESH" else None
                if mesh is None and s.rig:
                    mesh = next((c for c in s.rig.children if c.type == "MESH" and c.data.shape_keys
                                 and preset.shape_key in c.data.shape_keys.key_blocks), None)
                e.target = mesh
            elif preset.target_type == "BONE":
                e.target = s.rig or (obj if obj and obj.type == "ARMATURE" else None)
                e.bone = _guess_bone(e.target, preset.bone_keywords)
                e.channel = preset.channel
            e.blend_type = preset.blend
        s.effect_index = len(s.effects) - 1
        return {"FINISHED"}


class MIDIANIM_OT_effect_remove(bpy.types.Operator):
    bl_idname = "midianim.effect_remove"
    bl_label = "Remove Blow Effect"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        if 0 <= s.effect_index < len(s.effects):
            s.effects.remove(s.effect_index)
            s.effect_index = max(0, s.effect_index - 1)
        return {"FINISHED"}


class MIDIANIM_OT_effect_if_missing(bpy.types.Operator):
    """Choose what this effect does without its controller data"""
    bl_idname = "midianim.effect_if_missing"
    bl_label = "If Missing"
    bl_options = {"REGISTER", "UNDO"}
    index: IntProperty()
    choice: StringProperty()

    def execute(self, context):
        s = state.settings(context)
        e = s.effects[self.index]
        e.if_missing = self.choice
        e.missing = False
        e.status = "uses note velocity" if self.choice == "VELOCITY" else "turned off for this file"
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

class MIDIANIM_OT_hud_fit(bpy.types.Operator):
    """Fit the HUD's pitch range to the performer's notes"""
    bl_idname = "midianim.hud_fit"
    bl_label = "Fit Pitch Range"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        try:
            data = state.load_midi(s)
        except Exception as e:
            return _err(self, e)
        lo, hi = core_hud.fit_pitch_range([n.pitch + s.transpose for n in state.performer_notes(s, data)])
        s.hud.pitch_lo, s.hud.pitch_hi = lo, hi
        return {"FINISHED"}


class MIDIANIM_OT_hud_export(bpy.types.Operator):
    """Render the HUD for the scene's frame range as transparent PNGs (and ProRes 4444 if chosen)"""
    bl_idname = "midianim.hud_export"
    bl_label = "Export HUD"

    def execute(self, context):
        s = state.settings(context)
        wm = context.window_manager
        wm.progress_begin(0, 100)
        try:
            folder, count = hud_draw.export_png_sequence(context, lambda x: wm.progress_update(int(x * 100)))
            msg = f"Wrote {count} PNG frames to {folder}"
            if s.hud.output_format == "PRORES":
                mov = hud_draw.encode_prores(context, folder)
                msg += f" and {os.path.basename(mov)}"
        except Exception as e:
            return _err(self, e)
        finally:
            wm.progress_end()
        self.report({"INFO"}, msg)
        return {"FINISHED"}


class MIDIANIM_OT_hud_composite(bpy.types.Operator):
    """Create a scene that renders this scene with the exported HUD on top"""
    bl_idname = "midianim.hud_composite"
    bl_label = "Make Composite Scene"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        s = state.settings(context)
        try:
            comp = hud_draw.composite_scene(context, bpy.path.abspath(s.hud.output_dir))
        except Exception as e:
            return _err(self, e)
        self.report({"INFO"}, f"Created scene '{comp.name}': render it for the video with the HUD")
        return {"FINISHED"}


# ---------------------------------------------------------------------------
# Bake
# ---------------------------------------------------------------------------

class MIDIANIM_OT_bake(bpy.types.Operator):
    """Bake fingering and blow effects (replaces the previous MIDI bake)"""
    bl_idname = "midianim.bake"
    bl_label = "Bake MIDI to Animation"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        try:
            msgs, warnings = bake.bake_all(context)
        except Exception as e:
            return _err(self, e)
        text = "Baked: " + "; ".join(msgs) if msgs else "Nothing baked: set a rig or a blow effect"
        if warnings:
            text += " | " + " | ".join(warnings)
        self.report({"WARNING"} if warnings else {"INFO"}, text)
        return {"FINISHED"}


class MIDIANIM_OT_clear(bpy.types.Operator):
    """Remove all NLA tracks created by MIDI Animator"""
    bl_idname = "midianim.clear"
    bl_label = "Clear MIDI Bake"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        n = actions.clear_baked(set(actions.animated_ids(context.scene.objects)))
        self.report({"INFO"}, f"Removed {n} MIDI tracks")
        return {"FINISHED"}


classes = (
    MIDIANIM_OT_analyze,
    MIDIANIM_OT_set_performer_track,
    MIDIANIM_OT_set_scene_range,
    MIDIANIM_OT_add_audio,
    MIDIANIM_OT_detect_fingers,
    MIDIANIM_OT_guess_hold_bones,
    MIDIANIM_OT_lock_hands,
    MIDIANIM_OT_unlock_hands,
    MIDIANIM_OT_finger_bone_add,
    MIDIANIM_OT_finger_bone_remove,
    MIDIANIM_OT_add_marker,
    MIDIANIM_OT_select_marker,
    MIDIANIM_OT_autoassign,
    MIDIANIM_OT_toggle_lock,
    MIDIANIM_OT_apply_pose,
    MIDIANIM_OT_save_pose,
    MIDIANIM_OT_fill_from_chart,
    MIDIANIM_OT_note_add,
    MIDIANIM_OT_note_remove,
    MIDIANIM_OT_set_finger,
    MIDIANIM_OT_copy_fingering,
    MIDIANIM_OT_paste_fingering,
    MIDIANIM_OT_effect_add,
    MIDIANIM_OT_effect_remove,
    MIDIANIM_OT_effect_if_missing,
    MIDIANIM_OT_hud_fit,
    MIDIANIM_OT_hud_export,
    MIDIANIM_OT_hud_composite,
    MIDIANIM_OT_bake,
    MIDIANIM_OT_clear,
)
