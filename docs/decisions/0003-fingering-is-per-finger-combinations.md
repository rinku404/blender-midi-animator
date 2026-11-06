# 0003. Fingering is a combination of per-finger states

Status: accepted (2026-11-06)

## Context

v0.2 used one whole-hand pose per pitch class, plus an octave-key layer, found by action name. The user wants fingers up or down per note, reusable across notes.

## Decision

Each finger slot has a state: **Up** or **Down on key X**. A note maps to a **combination** of these, stored per note in an explicit, editable table (`NoteMapping.combination`, e.g. `L1=B;L2=A`). It can be bulk-filled from the profile chart. A note may instead use a **whole-hand override pose**. A **Rest** pose is used between phrases.

Motion: only fingers whose state changes move. Pressing fingers arrive at note onset over *Transition* frames, lifting fingers leave *Lift Lead* frames earlier (a setting, default 1). Short rests hold the fingering; rests longer than *Relax After* go to Rest. A lifted finger hovers over the last key it pressed.

## Consequences

Far fewer poses to author (one per finger per key, not one per note). The timeline logic lives in `core/fingering.py` and is unit-tested.
