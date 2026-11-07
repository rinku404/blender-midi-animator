# 0006. Bake to `MIDI: …` NLA tracks

Status: accepted (2026-11-06)

## Context

Baked keyframes are editable and render deterministically. Live drivers or handlers are fragile.

## Decision

Everything is baked into actions prefixed `MIDI_` and NLA tracks named `MIDI: …` (Fingering, Hand Poses, one per blow effect). Re-baking removes only those tracks. With *Keep Active Actions as Base*, the target's active action (e.g. an idle) is moved to a `Base:` track **before** MIDI tracks are created, so it sits underneath. Hand bones outside the fingers are only driven during Rest or override poses (strip influence goes to 0 otherwise).

## Consequences

Re-bake is safe and repeatable. The user's own animation is untouched.
