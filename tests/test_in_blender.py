"""End-to-end test. Run with either:
    blender -b --factory-startup --python tests/test_in_blender.py
    python tests/test_in_blender.py        (with the `bpy` module from PyPI installed)
"""
import os
import sys

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)
import midi_animator as ma  # noqa: E402

MID = os.path.join(ROOT, "examples", "aerophone_sample.mid")


def approx(a, b, tol=1e-3):
    return abs(a - b) <= tol


def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    # Rig: spine -> chest -> hand with an index finger and a thumb
    arm_data = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", arm_data)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, head, tail, parent in [("spine", (0, 0, 0), (0, 0, 1), None),
                                     ("chest", (0, 0, 1), (0, 0, 1.5), "spine"),
                                     ("hand.L", (0.5, 0, 1.4), (0.7, 0, 1.4), "chest"),
                                     ("f_index.L", (0.7, 0, 1.4), (0.8, 0, 1.4), "hand.L"),
                                     ("thumb.L", (0.6, -0.1, 1.4), (0.7, -0.1, 1.4), "hand.L")]:
        b = arm_data.edit_bones.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")

    # Idle action on the rig that must survive as a base layer
    rig.animation_data_create()
    idle = bpy.data.actions.new("Idle")
    rig.animation_data.action = idle
    rig.pose.bones["hand.L"].location.y = 0.25
    rig.pose.bones["hand.L"].keyframe_insert("location", index=1, frame=1)

    # Face with CheekPuff, instrument bell scaled 2x
    bpy.ops.mesh.primitive_uv_sphere_add()
    face = bpy.context.active_object
    face.name = "Face"
    face.shape_key_add(name="Basis")
    face.shape_key_add(name="CheekPuff")
    face.parent = rig
    bpy.ops.mesh.primitive_cone_add()
    bell = bpy.context.active_object
    bell.name = "Bell"
    bell.scale = (2, 2, 2)
    return scene, rig, face, bell


def save_pose(rig, note, index_x, thumb_x=0.0):
    s = bpy.context.scene.midi_animator
    bpy.context.view_layer.objects.active = rig
    if bpy.context.mode != "POSE":
        bpy.ops.object.mode_set(mode="POSE")
    pbs = rig.pose.bones
    pbs["f_index.L"].location.x = index_x
    pbs["thumb.L"].location.x = thumb_x
    bones = [pbs["thumb.L"]] if note == "OctaveKey" else [pbs["f_index.L"], pbs["thumb.L"]]
    s.save_note = note
    with bpy.context.temp_override(selected_pose_bones=bones):
        assert bpy.ops.midianim.save_fingering() == {"FINISHED"}


def main():
    ma.register()
    scene, rig, face, bell = build_scene()
    s = scene.midi_animator
    s.midi_path = MID
    s.fing_target = rig

    # Parser
    midi = ma.parse_midi(MID)
    assert len(midi.notes) == 14, len(midi.notes)
    assert approx(midi.notes[1].start, 0.6), midi.notes[1].start
    key = ma.detect_breath(midi)
    assert key is not None and key[2] == "CC" and key[3] == 2, key

    # Poses: value = pitch class / 100 for the main octave, distinct values for overrides
    pc_values = {n: (i + 1) / 100 for i, n in enumerate(ma.NOTE_NAMES)}
    for n, v in pc_values.items():
        save_pose(rig, n, v)
    save_pose(rig, "C4", 0.5)
    save_pose(rig, "D6", 0.7)
    save_pose(rig, "Rest", 0.0)
    save_pose(rig, "OctaveKey", 0.0, thumb_x=1.0)
    bpy.ops.object.mode_set(mode="OBJECT")

    assert bpy.ops.midianim.analyze() == {"FINISHED"}
    print("summary:", s.summary.replace("|", " / "))
    print("missing:", s.fing_missing)
    assert s.fing_missing == "", s.fing_missing  # A#3 resolves to the A# pitch-class pose

    for preset in ("CHEEKS", "BELL", "CHEST", "SWAY"):
        bpy.context.view_layer.objects.active = {"CHEEKS": face, "BELL": bell}.get(preset, rig)
        assert bpy.ops.midianim.effect_add(preset=preset) == {"FINISHED"}
    names = {e.name: e for e in s.effects}
    assert names["Cheeks"].target == face, names["Cheeks"].target
    assert names["Bell"].target == bell
    assert names["Chest"].data_path == 'pose.bones["chest"].rotation_quaternion', names["Chest"].data_path
    assert names["Sway"].data_path.startswith('pose.bones["spine"]'), names["Sway"].data_path

    assert bpy.ops.midianim.bake() == {"FINISHED"}
    fps = 24
    beat = 0.6 * fps  # frames per quarter note at 100 BPM

    def at(frame):
        scene.frame_set(int(frame), subframe=frame - int(frame))
        pb = rig.pose.bones
        return (pb["f_index.L"].location.x, pb["thumb.L"].location.x, face.data.shape_keys.key_blocks["CheekPuff"].value,
                bell.scale[0], pb["hand.L"].location.y)

    # Note 0 = D4 (frame 1): D pose, no octave key
    ix, th, cheek, bscale, idle_y = at(1 + 0.5 * beat)
    assert approx(ix, pc_values["D"]), ix
    assert approx(th, 0.0), th
    assert approx(idle_y, 0.25), ("idle action lost", idle_y)
    # Note 7 = D5 (beat 7): D pose + octave key
    ix, th, *_ = at(1 + 7.5 * beat)
    assert approx(ix, pc_values["D"]) and approx(th, 1.0), (ix, th)
    # Breath peak mid-phrase -> cheeks high, bell above rest scale 2
    _, _, cheek, bscale, _ = at(1 + 4.5 * beat)
    assert cheek > 0.8, cheek
    assert 2.4 < bscale <= 2.6 + 1e-3, bscale
    # During the 2-beat rest after phrase 1 (ends beat 9): relaxed hand, cheeks down
    ix, th, cheek, bscale, _ = at(1 + 10.5 * beat)
    assert approx(ix, 0.0) and approx(th, 0.0), (ix, th)
    assert cheek < 0.1, cheek
    assert approx(bscale, 2.0, 0.05), bscale
    # Phrase 3: C4 uses its own low pose, D6 its own palm pose (no octave key)
    p3 = 9 + 2 + 4 + 2  # phrase starts in beats
    ix, *_ = at(1 + (p3 + 0.5) * beat)
    assert approx(ix, 0.5), ix
    ix, th, *_ = at(1 + (p3 + 2.5) * beat)
    assert approx(ix, 0.7) and approx(th, 0.0), (ix, th)
    # Legato transition: halfway between E4 and F#4 is between their values
    ix, *_ = at(1 + 2 * beat - 1)
    assert pc_values["E"] - 1e-3 <= ix <= pc_values["F#"] + 1e-3, ix

    # Rebake is idempotent; clear removes everything we made
    n_tracks = len(rig.animation_data.nla_tracks)
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert len(rig.animation_data.nla_tracks) == n_tracks, (n_tracks, len(rig.animation_data.nla_tracks))
    assert approx(at(1 + 4.5 * beat)[3], bscale_peak := at(1 + 4.5 * beat)[3])
    assert 2.4 < bscale_peak <= 2.6 + 1e-3, ("rest scale drifted on rebake", bscale_peak)
    assert bpy.ops.midianim.clear() == {"FINISHED"}
    left = [t.name for t in rig.animation_data.nla_tracks]
    assert left == ["Base: Idle"], left
    assert not any(a.name.startswith("MIDI_") for a in bpy.data.actions), [a.name for a in bpy.data.actions]
    assert all(bpy.data.actions.get("Fingering_" + n) for n in ma.NOTE_NAMES), "saved poses were deleted"

    # Generic note -> action triggers still work (drums sample)
    s.midi_path = os.path.join(ROOT, "examples", "drums_piano_sample.mid")
    s.fing_enabled = False
    for e in s.effects:
        e.enabled = False
    bpy.ops.object.empty_add()
    drum = bpy.context.active_object
    drum.keyframe_insert("location", index=2, frame=1)
    drum.location.z = 1
    drum.keyframe_insert("location", index=2, frame=6)
    m = s.mappings.add()
    m.name, m.target, m.action = "Kick", drum, drum.animation_data.action
    m.note_low = m.note_high = 36
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    strips = [st for t in drum.animation_data.nla_tracks if t.name.startswith("MIDI:") for st in t.strips]
    assert len(strips) == 8, len(strips)

    ma.unregister()
    print("ALL TESTS PASSED")


main()
