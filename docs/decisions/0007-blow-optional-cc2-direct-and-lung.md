# 0007. Blow is optional: CC2 by default, never a silent fallback, Direct or Lung mode

Status: accepted (2026-11-06). The Lung mode and Chest preset parts are superseded by [0014](0014-breathing-planned-signal-and-live-drivers.md) (2026-11-12).

## Context

Blow data may be absent. v0.2 silently fell back to velocity. Real chests fill on the inhale and empty while blowing.

## Decision

- The source per effect is a CC (default **CC2**), aftertouch, or velocity.
- If the chosen controller isn't in the file, Analyze flags the effect and offers **Use Velocity** or **Turn Off**. Until you choose, Bake skips it **with a warning**.
- The velocity shape rises over *attack*, decays toward *Sustain* (default 0.6) while held, then releases.
- **Mode:** *Direct* (output follows intensity, the Cheeks default) or *Lung* (lung volume drains with blow over *Lung Capacity* seconds and refills in rests, the Chest default).
- Targets are picked as Object → Shape Key | Bone → Channel | Property, with the raw data path under Advanced. Bone values are deltas: rotations in degrees, scale added to 1, blended with *Combine*.

## Consequences

Every effect's source is explicit. The chest looks like breathing rather than mirroring the cheeks.
