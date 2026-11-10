# 0012. Target: CJ playing a B♭ clarinet

Status: accepted (2026-11-10)

## Context

v1 was designed and tested around a saxophone and a rig with five fingers per hand (ADRs 0002–0004). During the
first real trial (plan step 6), the user set the actual goal: the video is **CJ** (`carl_johnson_cj.glb`) playing a
**B♭ clarinet**. CJ's hands have two three-joint fingers each and no clear thumb. The user's take
(`zelda_recorded_v1_b.mid`) goes down to MIDI 50 (concert D3), which is exactly the B♭ clarinet's lowest note
(written E3).

## Decision

- The clarinet becomes a first-class instrument: a **B♭ Clarinet** profile with a Boehm fingering chart keyed by written
  pitch (plan step 10). The sax profile stays.
- Profiles get a default Transpose: sax 0, B♭ clarinet **+2** (written = concert + 2). The HUD can show **Concert**
  pitch, so it displays the notes as recorded.
- Rigs with fewer than five fingers are supported by letting several finger slots **share one bone chain**
  (plan step 11). The rule for disagreeing slots is decided with the user in step 11.
- The real-rig trial is split: the pipeline on CJ now (step 6), and fingering after the clarinet profile and shared
  slots exist (step 12).

## Consequences

The plan grows by three steps (10, 11, 12) before the fixes and the release. The sax remains supported and tested,
but the clarinet on CJ is now what decides whether v1 is done.
