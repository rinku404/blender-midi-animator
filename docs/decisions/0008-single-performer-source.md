# 0008. One performer track/channel for everything

Status: accepted (2026-11-06)

## Context

v0.2 repeated track/channel filters on fingering and on every effect.

## Decision

One **Performer** track/channel and **Transpose** at the top drive fingering, blow and the HUD. An effect can override the source under Advanced (*Own Track/Channel*). The performer's notes are made monophonic: a note ends where the next starts, and simultaneous starts keep the highest note.

## Consequences

One setting in the common case. *Transpose* converts file (concert) pitch to written (fingered) pitch.
