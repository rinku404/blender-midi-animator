"""Sidebar panels (3D Viewport > N > MIDI)."""

import bpy

from ..core import fingering as core_fing
from . import autoassign, rig, state


class MIDIANIM_UL_notes(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        s = state.settings(context)
        row = layout.row(align=True)
        row.label(text=state.ui_name(item.pitch))
        if item.pose:
            row.label(text=item.pose.name, icon="ARMATURE_DATA")
        else:
            combo = state.parse_combination(item.combination)
            row.label(text=core_fing.combination_label(combo, state.profile(s).slots))


class MIDIANIM_UL_fingers(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        s = state.settings(context)
        row = layout.row(align=True)
        row.label(text=item.label)
        ok = [b.bone for b in item.bones if b.bone and s.rig and b.bone in s.rig.pose.bones]
        row.label(text=f"{len(ok)} bones" if ok else "no bones", icon="CHECKMARK" if ok else "ERROR")


class MIDIANIM_UL_effects(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, "enabled", text="")
        row.prop(item, "name", text="", emboss=False)
        row.label(text="", icon="ERROR" if item.missing or not item.target else "CHECKMARK")


class MIDIANIM_PT_base:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MIDI"


class MIDIANIM_PT_midi(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "1. Instrument & MIDI"

    def draw(self, context):
        s = state.settings(context)
        col = self.layout.column()
        col.prop(s, "profile")
        col.separator()
        col.prop(s, "midi_path")
        row = col.row(align=True)
        row.operator("midianim.analyze", icon="VIEWZOOM")
        row.operator("midianim.set_scene_range", icon="TIME")
        col.prop(s, "start_frame")
        col.prop(s, "time_offset")
        col.prop(s, "audio_path")
        col.operator("midianim.add_audio", icon="SOUND")

        box = col.box()
        box.label(text="Performer", icon="USER")
        r = box.row(align=True)
        r.prop(s, "performer_track")
        r.prop(s, "performer_channel")
        box.prop(s, "transpose")
        for t in s.tracks:
            r = box.row(align=True)
            r.label(text=t.label)
            op = r.operator("midianim.set_performer_track", text="",
                            icon="RADIOBUT_ON" if s.performer_track == t.index else "RADIOBUT_OFF",
                            emboss=False)
            op.track = t.index
        if s.report:
            rep = col.box()
            for line in s.report:
                rep.label(text=line.text, icon=line.icon)


class MIDIANIM_PT_fingers(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "2. Fingers & Keys"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = state.settings(context)
        layout = self.layout
        layout.prop(s, "rig")
        box = layout.box()
        box.label(text="Hold the instrument", icon="CON_CHILDOF")
        box.prop(s, "instrument")
        if s.rig:
            for attr in ("hold_strap_bone", "hold_hand_l", "hold_hand_r"):
                box.prop_search(s, attr, s.rig.data, "bones")
        r = box.row(align=True)
        r.operator("midianim.guess_hold_bones", icon="VIEWZOOM")
        r.operator("midianim.lock_hands", icon="LOCKED")
        r.operator("midianim.unlock_hands", icon="UNLOCKED")
        box.label(text="Pose the hold first: instrument at the lips, hands on the keys")
        layout.operator("midianim.detect_fingers", icon="HAND")
        if not s.fingers:
            layout.label(text="Detect Fingers (or Analyze) to list the finger slots")
            return
        layout.template_list("MIDIANIM_UL_fingers", "", s, "fingers", s, "finger_index", rows=4)
        if not (0 <= s.finger_index < len(s.fingers)):
            return
        f = s.fingers[s.finger_index]
        slot = state.profile(s).slot(f.slot)

        box = layout.box()
        box.label(text=f"{f.label}: bones root → tip", icon="BONE_DATA")
        for i, b in enumerate(f.bones):
            r = box.row(align=True)
            if s.rig:
                r.prop_search(b, "bone", s.rig.data, "bones", text="")
            else:
                r.prop(b, "bone", text="")
            r.operator("midianim.finger_bone_remove", text="", icon="X").index = i
        box.operator("midianim.finger_bone_add", icon="ADD")
        box.prop(f, "up_pose")

        box = layout.box()
        box.label(text="Key markers", icon="EMPTY_SINGLE_ARROW")
        box.prop(s, "instrument")
        r = box.row(align=True)
        r.prop(s, "hover")
        r.prop(s, "marker_size", text="Size")
        markers = rig.find_markers()
        if slot:
            for key in slot.keys:
                r = box.row(align=True)
                m = markers.get((slot.id, key))
                r.label(text=key, icon="CHECKMARK" if m else "DOT")
                if m:
                    op = r.operator("midianim.select_marker", text="", icon="RESTRICT_SELECT_OFF")
                    op.slot, op.key = slot.id, key
                op = r.operator("midianim.add_marker", text="Move" if m else "Place", icon="PIVOT_CURSOR")
                op.slot, op.key = slot.id, key
        box.label(text="Place at the 3D cursor, or select key vertices in Edit Mode")

        box = layout.box()
        r = box.row(align=True)
        r.scale_y = 1.2
        r.operator("midianim.autoassign", icon="CON_KINEMATIC").only_selected = False
        r.operator("midianim.autoassign", text="", icon="RESTRICT_SELECT_OFF").only_selected = True
        r = box.row(align=True)
        r.prop(s, "bend_axis")
        r.operator("midianim.detect_bend_axis", icon="VIEWZOOM")
        r = box.row(align=True)
        r.prop(s, "keep_twist")
        r.prop(s, "force_autoassign")
        box.label(text="Also builds F.Rest: fingers up over their home keys")
        for act in autoassign.generated_poses(f.slot):
            r = box.row(align=True)
            r.label(text=act.name)
            r.operator("midianim.apply_pose", text="", icon="HIDE_OFF").action = act.name
            locked = bool(act.get(autoassign.LOCK_PROP))
            r.operator("midianim.toggle_lock", text="", icon="LOCKED" if locked else "UNLOCKED",
                       emboss=False).action = act.name


class MIDIANIM_PT_notes(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "3. Note Map"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = state.settings(context)
        prof = state.profile(s)
        layout = self.layout
        r = layout.row(align=True)
        r.operator("midianim.fill_from_chart", text="Fill: This File", icon="IMPORT").which = "FILE"
        r.operator("midianim.fill_from_chart", text="Fill: Whole Chart").which = "ALL"
        row = layout.row()
        row.template_list("MIDIANIM_UL_notes", "", s, "notes", s, "note_index", rows=6)
        col = row.column(align=True)
        col.operator("midianim.note_add", icon="ADD", text="")
        col.operator("midianim.note_remove", icon="REMOVE", text="")
        col.separator()
        col.operator("midianim.copy_fingering", icon="COPYDOWN", text="")
        col.operator("midianim.paste_fingering", icon="PASTEDOWN", text="")

        if 0 <= s.note_index < len(s.notes):
            m = s.notes[s.note_index]
            box = layout.box()
            box.label(text=f"{state.ui_name(m.pitch)}  (written)", icon="SEQUENCE")
            box.prop(m, "pose")
            if not m.pose:
                combo = state.parse_combination(m.combination)
                grid = box.column(align=True)
                for slot in prof.slots:
                    r = grid.row(align=True)
                    r.label(text=slot.label)
                    current = combo.get(slot.id)
                    op = r.operator("midianim.set_finger", text="up", depress=current is None)
                    op.slot, op.key = slot.id, ""
                    for key in slot.keys:
                        op = r.operator("midianim.set_finger", text=key, depress=current == key)
                        op.slot, op.key = slot.id, key

        box = layout.box()
        box.prop(s, "rest_pose")
        box.operator("midianim.save_pose", icon="FILE_TICK")
        col = box.column(align=True)
        col.prop(s, "transition")
        col.prop(s, "lift_lead")
        col.prop(s, "relax_after")


class MIDIANIM_PT_blow(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "4. Blow"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        s = state.settings(context)
        layout = self.layout
        row = layout.row(align=True)
        for p in state.profile(s).presets:
            row.operator("midianim.effect_add", text=p.label).preset = p.id
        row = layout.row()
        row.template_list("MIDIANIM_UL_effects", "", s, "effects", s, "effect_index", rows=3)
        col = row.column(align=True)
        col.operator("midianim.effect_add", icon="ADD", text="").preset = ""
        col.operator("midianim.effect_remove", icon="REMOVE", text="")
        if not (0 <= s.effect_index < len(s.effects)):
            return
        e = s.effects[s.effect_index]
        box = layout.box()

        src = box.column(align=True)
        src.prop(e, "source")
        if e.source == "CC":
            src.prop(e, "cc_number")
        if e.status:
            src.label(text=e.status, icon="ERROR" if e.missing else "INFO")
        if e.missing:
            r = src.row(align=True)
            op = r.operator("midianim.effect_if_missing", text="Use Velocity")
            op.index, op.choice = s.effect_index, "VELOCITY"
            op = r.operator("midianim.effect_if_missing", text="Turn Off")
            op.index, op.choice = s.effect_index, "OFF"
        elif e.source != "VELOCITY":
            src.prop(e, "if_missing")

        tgt = box.column(align=True)
        tgt.prop(e, "target_type")
        tgt.prop(e, "target")
        if e.target_type == "SHAPE_KEY":
            sk = e.target.data.shape_keys if e.target and e.target.type == "MESH" else None
            if sk:
                tgt.prop_search(e, "shape_key", sk, "key_blocks")
            else:
                tgt.prop(e, "shape_key")
                tgt.label(text="This object has no shape keys", icon="ERROR")
        elif e.target_type == "BONE":
            if e.target and e.target.type == "ARMATURE":
                tgt.prop_search(e, "bone", e.target.data, "bones")
            else:
                tgt.label(text="Choose an armature", icon="ERROR")
            tgt.prop(e, "channel")
        else:
            tgt.prop(e, "data_path")
            tgt.prop(e, "array_index")

        col = box.column(align=True)
        col.prop(e, "mode", expand=True)
        unit = " (°)" if e.target_type == "BONE" and e.channel.startswith("ROT") else ""
        r = col.row(align=True)
        r.prop(e, "out_min", text="Min" + unit)
        r.prop(e, "out_max", text="Max" + unit)
        r = col.row(align=True)
        r.prop(e, "attack")
        r.prop(e, "release")
        if e.mode == "LUNG":
            r = col.row(align=True)
            r.prop(e, "lung_capacity")
            r.prop(e, "refill_time")
        if e.source == "VELOCITY" or e.if_missing == "VELOCITY":
            r = col.row(align=True)
            r.prop(e, "sustain")
            r.prop(e, "decay")

        box.prop(e, "show_advanced", icon="TRIA_DOWN" if e.show_advanced else "TRIA_RIGHT", emboss=False,
                 text="Advanced")
        if e.show_advanced:
            col = box.column(align=True)
            r = col.row(align=True)
            r.prop(e, "threshold")
            r.prop(e, "curve")
            col.prop(e, "normalize")
            col.prop(e, "blend_type")
            col.prop(e, "own_source")
            if e.own_source:
                r = col.row(align=True)
                r.prop(e, "track")
                r.prop(e, "channel_filter")


class MIDIANIM_PT_hud(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "5. Note HUD"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(state.settings(context).hud, "preview", text="")

    def draw(self, context):
        h = state.settings(context).hud
        layout = self.layout
        r = layout.row(align=True)
        r.prop(h, "preview_scale")
        r.prop(h, "preview_position", text="")
        col = layout.column(align=True)
        r = col.row(align=True)
        r.prop(h, "width")
        r.prop(h, "height")
        col.prop(h, "lookahead")
        col.prop(h, "hit_x")
        col = layout.column(align=True)
        col.prop(h, "pitch_auto")
        if not h.pitch_auto:
            r = col.row(align=True)
            r.prop(h, "pitch_lo")
            r.prop(h, "pitch_hi")
            col.operator("midianim.hud_fit", icon="FULLSCREEN_EXIT")
        col.prop(h, "lane_lines")
        box = layout.box()
        box.label(text="Note names")
        r = box.row(align=True)
        r.prop(h, "pitch_display", expand=True)
        r = box.row(align=True)
        r.prop(h, "naming", expand=True)
        r = box.row(align=True)
        r.prop(h, "accidentals", expand=True)
        box.prop(h, "show_octave")
        r = box.row(align=True)
        r.prop(h, "label_size")
        r.prop(h, "now_size")
        box = layout.box()
        box.label(text="Colours")
        for p in ("color_upcoming", "color_active", "color_played", "color_hitline", "color_panel"):
            box.prop(h, p)
        box = layout.box()
        box.prop(h, "output_dir")
        box.prop(h, "output_format")
        box.operator("midianim.hud_export", icon="RENDER_ANIMATION")
        box.operator("midianim.hud_composite", icon="SEQ_SEQUENCER")


class MIDIANIM_PT_bake(MIDIANIM_PT_base, bpy.types.Panel):
    bl_label = "6. Bake"

    def draw(self, context):
        s = state.settings(context)
        col = self.layout.column()
        col.prop(s, "fingering_enabled")
        col.prop(s, "keep_active_actions")
        col.scale_y = 1.3
        col.operator("midianim.bake", icon="REC")
        col.operator("midianim.clear", icon="TRASH")


classes = (
    MIDIANIM_UL_notes,
    MIDIANIM_UL_fingers,
    MIDIANIM_UL_effects,
    MIDIANIM_PT_midi,
    MIDIANIM_PT_fingers,
    MIDIANIM_PT_notes,
    MIDIANIM_PT_blow,
    MIDIANIM_PT_hud,
    MIDIANIM_PT_bake,
)
