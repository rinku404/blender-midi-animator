# 0010. Scope cuts for v1

Status: accepted (2026-11-06)

## Context

v0.2 also imported models, added Rigify metarigs, bound meshes, had drum/piano note triggers and a special bell effect.

## Decision

Removed: the model import / Rigify / bind panel (Blender already does this), drum/piano triggers (they come back as future Percussion / Polyphonic profiles), and the bell special case (it's just a blow target now).

## Consequences

A smaller v1 focused on doing one instrument well.
