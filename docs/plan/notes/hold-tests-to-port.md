# Hold assertions to port (from PR #2, `tests/test_chart_and_hold.py` on `main`)

For step 2. Written against the old single-file add-on (`import midi_animator as ma`, settings
`s.hold_instrument`, `s.hold_chest_bone`, `s.hold_hand_l/r`, operators `midianim.guess_hold_bones`,
`lock_hands`, `unlock_hands`). Adapt names to v1 (`s.instrument`, `s.hold_strap_bone`, ...), and
add the new step-2 check: after a bake with the Chest effect, the instrument's world scale stays
constant (+-1e-4). The per-finger chart tests from that file are not ported: v1's chart is tested in
`tests/core/test_fingering.py`.

## Assertions (verbatim from PR #2)

```python
    # ---- Hold: sax hangs from chest, hands locked to it ----
    s.hold_instrument = sax
    assert bpy.ops.midianim.guess_hold_bones() == {"FINISHED"}
    assert (s.hold_chest_bone, s.hold_hand_l, s.hold_hand_r) == ("chest", "hand.L", "hand.R"), \
        (s.hold_chest_bone, s.hold_hand_l, s.hold_hand_r)
    scene.frame_set(1)
    bpy.context.view_layer.update()
    pb = rig.pose.bones
    hand_before = (rig.matrix_world @ pb["hand.L"].head).copy()
    elbow_before = (rig.matrix_world @ pb["forearm.L"].head).copy()
    sax_before = sax.matrix_world.translation.copy()
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}
    bpy.context.view_layer.update()
    assert sax.parent == rig and sax.parent_bone == "chest"
    assert (sax.matrix_world.translation - sax_before).length < 1e-4, "sax moved when parented"
    assert ((rig.matrix_world @ pb["hand.L"].head) - hand_before).length < 1e-3, "hand moved on lock"
    assert ((rig.matrix_world @ pb["forearm.L"].head) - elbow_before).length < 1e-2, "elbow drifted"

    # Bend the chest: the sax follows, and the hands stay on the sax
    pb["chest"].rotation_mode = "XYZ"
    pb["chest"].rotation_euler.x = math.radians(20)
    bpy.context.view_layer.update()
    tgt = bpy.data.objects["MIDI Hold L"]
    hand_now = rig.matrix_world @ pb["hand.L"].head
    assert (sax.matrix_world.translation - sax_before).length > 0.01, "sax did not follow chest"
    assert (hand_now - tgt.matrix_world.translation).length < 1e-3, (hand_now, tgt.matrix_world.translation)

    # Rebake still works with the lock on; unlock cleans up
    assert bpy.ops.midianim.bake() == {"FINISHED"}
    assert bpy.ops.midianim.lock_hands() == {"FINISHED"}   # idempotent
    n_ik = sum(1 for b in pb for c in b.constraints if c.name.startswith("MIDI Hold"))
    assert n_ik == 4, n_ik
    assert bpy.ops.midianim.unlock_hands() == {"FINISHED"}
    assert not any(c.name.startswith("MIDI Hold") for b in pb for c in b.constraints)
    assert "MIDI Hold L" not in bpy.data.objects

```

Notes: `rig`, `sax`, `scene`, `s` come from `build()` below; the hold block runs after the chart bake.
The old script also bakes with the lock on (`midianim.bake`) before checking idempotence.

## Test rig used by PR #2 (`build()`)

```python
def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = 24
    arm = bpy.data.armatures.new("Rig")
    rig = bpy.data.objects.new("Rig", arm)
    scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones

    def bone(name, head, tail, parent=None, connect=False):
        b = eb.new(name)
        b.head, b.tail = head, tail
        if parent:
            b.parent = eb[parent]
            b.use_connect = connect
        return b

    bone("spine", (0, 0, 0), (0, 0, 1))
    bone("chest", (0, 0, 1), (0, 0, 1.4), "spine", True)
    for side, x in (("L", 1), ("R", -1)):
        bone(f"upper_arm.{side}", (0.2 * x, 0, 1.35), (0.5 * x, 0.05, 1.1), "chest")
        bone(f"forearm.{side}", (0.5 * x, 0.05, 1.1), (0.3 * x, -0.25, 1.0), f"upper_arm.{side}", True)
        bone(f"hand.{side}", (0.3 * x, -0.25, 1.0), (0.25 * x, -0.33, 1.0), f"forearm.{side}", True)
        bone(f"thumb.{side}", (0.3 * x, -0.27, 1.0), (0.28 * x, -0.3, 0.98), f"hand.{side}")
        for f in ("index", "middle", "ring", "pinky"):
            prev = f"hand.{side}"
            for j in range(3):
                n = f"{f}{'' if j == 0 else j}.{side}"
                y0 = -0.33 - 0.02 * j
                bone(n, (0.25 * x, y0, 1.0), (0.25 * x, y0 - 0.02, 1.0), prev, j > 0)
                prev = n
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.mesh.primitive_cylinder_add(radius=0.03, depth=0.6, location=(0, -0.3, 1.0))
    sax = bpy.context.active_object
    sax.name = "Saxophone"
    return scene, rig, sax


```
