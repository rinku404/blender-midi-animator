import os

import pytest

from midi_animator.core import signal as S

FPS = 24
TIMES = [f / FPS for f in range(0, 24 * 4)]


def test_sample_hold():
    assert S.sample_hold([(1.0, 50), (2.0, 100)], [0.5, 1.0, 1.5, 2.5]) == [0, 50, 50, 100]
    assert S.sample_hold([], [0, 1]) == [0, 0]


def test_smooth_attack_faster_than_release():
    step = [0.0] * 10 + [100.0] * 30 + [0.0] * 30
    times = [i / FPS for i in range(len(step))]
    y = S.smooth(step, times, attack=0.02, release=0.5)
    assert y[12] > 90            # fast rise
    assert y[45] > 50            # slow fall


def test_shape_threshold_and_curve():
    assert S.shape([0, 6, 127], 127, threshold=0.05, curve=1.0) == pytest.approx([0, 0, 1])
    soft = S.shape([64], 127, 0.0, 0.5)[0]
    hard = S.shape([64], 127, 0.0, 2.0)[0]
    assert soft > 0.5 > hard


def test_velocity_envelope_decays_to_sustain():
    env = S.velocity_envelope([(0.0, 2.0, 100)], [0.0, 1.9, 2.1], sustain=0.6, decay=0.2)
    assert env[0] == pytest.approx(100)
    assert env[1] == pytest.approx(60, abs=0.1)
    assert env[2] == 0


def test_blow_curve_from_cc_and_velocity():
    params = S.BlowParams(attack=0.0, release=0.0, threshold=0.0)
    x = S.blow_curve([0.0, 1.0], params, events=[(0.0, 0), (0.5, 127)])
    assert x == pytest.approx([0.0, 1.0])
    x = S.blow_curve([0.0, 0.1, 3.0], params, notes=[(0.0, 1.0, 64)])
    assert x[0] == pytest.approx(1.0)        # normalized to the take's loudest note
    assert 0.6 < x[1] < 0.9                  # already decaying toward sustain
    assert x[2] == 0


def test_remap():
    assert S.remap([0.0, 0.5, 1.0], 1.0, 2.0) == [1.0, 1.5, 2.0]


# --- the breath planner --------------------------------------------------------------------------------------

def _take(notes, length=None):
    """(spans, times, blow) for [(start, end)] notes: blow 1 while a note sounds, a little smoothed."""
    end = max(e for _, e in notes)
    times = [i / FPS for i in range(int(((length or end) + 1.0) * FPS) + 1)]
    raw = [1.0 if any(s <= t < e for s, e in notes) else 0.0 for t in times]
    return notes, times, S.smooth(raw, times, 0.05, 0.1)


def _phrases(n_notes, note=0.4, gap=0.25, start=0.2):
    notes, t = [], start
    for _ in range(n_notes):
        notes.append((t, t + note))
        t += note + gap
    return notes


def test_plan_breathes_in_at_every_gap_and_stays_above_the_reserve():
    spans, times, blow = _take(_phrases(40))
    plan = S.plan_breaths(spans, times, blow)
    assert len(plan.breaths) == 39                      # one per gap
    assert all(b.end > b.start for b in plan.breaths)
    assert plan.minimum >= S.RESERVE - 0.01
    assert min(plan.curve[: int(spans[-1][1] * FPS)]) >= S.RESERVE - 0.01
    assert max(plan.curve) == pytest.approx(1.0)


def test_plan_refills_toward_full_at_each_break():
    spans, times, blow = _take(_phrases(3, note=2.0, gap=1.0))
    plan = S.plan_breaths(spans, times, blow)
    for b in plan.breaths:
        assert b.end == pytest.approx(1.0)              # a 1 s gap is plenty for a full breath
    gap_start = int(spans[0][1] * FPS)
    assert plan.curve[gap_start + FPS // 2] > plan.curve[gap_start]      # coming up mid-gap


def test_inhale_is_limited_by_the_gap():
    # a long drain, then a 0.2 s gap: room for 3 lungs/s * 0.16 s = 0.48 of a lung, not a whole one
    spans, times, blow = _take([(0.1, 8.1), (8.3, 9.0)])
    plan = S.plan_breaths(spans, times, blow)
    (b,) = plan.breaths
    assert b.t1 - b.t0 == pytest.approx(0.2 - 2 * S.EDGE, abs=1e-6)
    assert b.end - b.start == pytest.approx(S.INHALE_RATE * (b.t1 - b.t0), abs=1e-6)
    assert b.end < 1.0


def test_legato_runs_breathe_at_blow_dips_and_short_gaps_do_not():
    # 0.05 s gaps are no breath points; a 0.4 s dip of the blow inside legato is
    notes = [(0.0, 1.0), (1.05, 2.5), (2.5, 4.0)]
    times = [i / FPS for i in range(int(5 * FPS))]
    blow = [0.0 if 2.3 <= t < 2.7 else 0.9 for t in times]
    plan = S.plan_breaths(notes, times, blow)
    assert len(plan.breaths) == 1
    assert 2.3 < plan.breaths[0].t0 < 2.45 and 2.6 < plan.breaths[0].t1 < 2.8


def test_plan_prepares_a_late_first_note_and_breathes_tidally_after_the_end():
    spans, times, blow = _take([(1.5, 2.0), (2.5, 3.0)], length=15.0)
    plan = S.plan_breaths(spans, times, blow)
    assert plan.breaths[0].kind == "prep" and plan.breaths[0].t1 < 1.5
    tail = plan.curve[int(6.0 * FPS):]
    assert min(tail) > 0.3 and max(tail) < 0.7
    assert max(tail) - min(tail) > 0.05                 # it keeps moving, slowly
    assert max(abs(b - a) for a, b in zip(tail, tail[1:])) < 0.01       # and never jumps


def test_plan_without_notes_or_samples():
    plan = S.plan_breaths([], [i / FPS for i in range(48)], [0.0] * 48)
    assert plan.breaths == [] and min(plan.curve) > 0.3 and max(plan.curve) < 0.7
    assert S.plan_breaths([(0, 1)], [0.0], [0.0]).curve == [S.TIDAL_LEVEL]


def test_lung_mode_in_blow_curve_uses_the_planner():
    notes = [(0.0, 1.0, 100), (1.5, 2.5, 100)]
    times = [i / FPS for i in range(int(4 * FPS))]
    direct = S.blow_curve(times, S.BlowParams(mode="DIRECT"), notes=notes)
    lung = S.blow_curve(times, S.BlowParams(mode="LUNG"), notes=notes)
    assert lung == S.plan_breaths([(0.0, 1.0), (1.5, 2.5)], times, direct).curve
    assert S.blow_curve(times, S.BlowParams(mode="LUNG"), notes=notes, spans=[(0.0, 9.0)]) != lung
    # without notes, the spans come from where the blow is up
    ev = [(0.0, 100), (1.0, 0), (1.5, 100), (2.5, 0)]
    assert S.blow_curve(times, S.BlowParams(mode="LUNG"), events=ev)[0] > 0.9


TAKE = os.environ.get("MIDI_ANIMATOR_TAKE", r"D:\3D\blender_projects\midi_trial\src\zelda_recorded_v1_b.mid")


@pytest.mark.skipif(not os.path.exists(TAKE), reason="the user's recording is outside the repo")
def test_the_users_take_breathes_eight_times_and_is_never_empty():
    from midi_animator.core import midi
    d = midi.parse_midi(TAKE)
    spans = sorted((n.start, n.end) for n in d.notes)
    times = [i / FPS for i in range(int((d.length + 8.0) * FPS) + 1)]
    blow = S.blow_curve(times, S.BlowParams(attack=0.15, release=0.4), events=list(d.controller_events("CC", 2)))
    plan = S.plan_breaths(spans, times, blow)
    assert len(plan.breaths) == 8
    assert plan.lung_size == pytest.approx(7.0, abs=0.2)
    assert plan.minimum == pytest.approx(0.154, abs=0.01) and plan.minimum > 0.14
    assert min(plan.curve[: int(spans[-1][1] * FPS)]) > 0.14
    tail = plan.curve[int((spans[-1][1] + 3.0) * FPS):]
    assert max(tail) - min(tail) > 0.02                 # not frozen after the last note
