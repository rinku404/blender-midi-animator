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


def test_lung_drains_then_refills():
    blowing = [1.0] * (3 * FPS) + [0.0] * FPS
    times = [i / FPS for i in range(len(blowing))]
    v = S.lung(blowing, times, capacity=6.0, refill_time=0.3)
    assert v[0] == 1.0
    assert v[3 * FPS - 1] == pytest.approx(0.5, abs=0.03)    # 3 s of full blow = half empty
    assert v[-1] > 0.95                                     # refilled during the rest


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
