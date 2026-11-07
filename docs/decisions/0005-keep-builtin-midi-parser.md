# 0005. Keep the built-in MIDI parser (no mido)

Status: accepted (2026-11-06)

## Context

Vendoring `mido` was considered. The existing parser already handles format 0/1, tempo maps, running status and SMPTE, and is correct on the samples.

## Decision

Keep the parser, move it to `core/midi.py`, and cover it with unit tests (running status, tempo change, bad file, monophonic reduction, performer filtering).

## Consequences

No third-party dependency. Any new MIDI edge cases are fixed in our code.
