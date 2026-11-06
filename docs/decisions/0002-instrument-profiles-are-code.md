# 0002. Instrument profiles are Python classes

Status: accepted (2026-11-06)

## Context

The tool must support several instrument families (a dropdown). v0.2 hard-coded saxophone logic.

## Decision

A **profile** is a Python object registered with `@register` in `core/profiles.py`. It defines the finger slots and the keys each can press, the built-in fingering chart, blow-effect presets, and whether it is monophonic. v1 ships only **Monophonic Wind / Brass** (sax chart, also the Aerophone default). Users customise through the note map, not by writing profiles.

## Consequences

Adding Polyphonic or Percussion later means a new class plus any new overlap handling. Profiles aren't user-editable data files.
