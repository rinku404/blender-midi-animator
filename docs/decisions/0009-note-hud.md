# 0009. Note HUD: horizontal highway, one layout for preview and export

Status: accepted (2026-11-06)

## Context

The user wants an Ocarina-of-Time / Guitar-Hero style overlay to put on a video.

## Decision

- Layout (`core/hud.py`): a "now playing" band on top and a highway below. Notes scroll right → left to a hit line, pitch is vertical, bar length is duration. Upcoming bars are dim, the sounding bar lights up and fills to the hit line while its name pops with a held-time counter, and played bars keep their length and fade. Bars have a minimum height so names fit.
- Names default to **written** pitch with letters. Options: concert pitch, flats, solfège (Dó Ré Mi), octave number on/off.
- The same primitives drive the **live viewport preview** (gpu/blf draw handler), **export** (GPU offscreen → PNG with straight alpha, default; ProRes 4444 via a temporary sequencer scene, optional), and a **composite scene** (scene strip + HUD image strip).

## Consequences

Export needs Blender's UI (GPU), not `-b`. A fingering diagram in the HUD is deferred.
