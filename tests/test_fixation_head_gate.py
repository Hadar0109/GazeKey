"""Tests for per-target head drift rejection and PCA fixation gating.

The gate-vs-mapper representation tests below pin **as-built** behavior: the
fixation gate collapses the four PCA channels into a 2-D mean `u,v`, while the
mapper fits all four independently. That asymmetry is the T017 hypothesis
(`runs/_feature004/T017_4d_fixation_gate.md`), which is **inconclusive** and
whose product change was reverted for isolation under T059. Each test names
the desired 4-D behavior in its docstring so the intent is not lost, but
asserts what the code does today — pinning first, per the Feature 004
one-change-per-experiment contract.
"""

from __future__ import annotations

import numpy as np

from gazekey.calibration.fixation_gate import (
    FixationGate,
    FixationGateConfig,
    _pca_uv_mean,
)
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.ridge import _raw_uv, extract_uv_arrays


def _feat(**kwargs) -> FrameFeatures:
    base = dict(
        timestamp_ms=0,
        face_detected=True,
        blink=False,
        confidence=1.0,
        Lh=0.5,
        Lv=0.5,
        Rh=0.5,
        Rv=0.5,
        avg_h=0.5,
        avg_v=0.5,
        eye_box_w=0.04,
        eye_box_h=0.02,
        face_x=0.5,
        face_y=0.6,
        pca_uL=0.0,
        pca_vL=0.0,
        pca_uR=0.0,
        pca_vR=0.0,
    )
    base.update(kwargs)
    return FrameFeatures(**base)


def _lock_and_collect(gate: FixationGate, feat: FrameFeatures, *, n: int = 40, dt_ms: float = 20.0):
    for _ in range(n):
        gate.update(feat, dt_ms=dt_ms)


def test_head_drift_resets_collection():
    cfg = FixationGateConfig(
        lock_on_ms=100.0,
        complete_ms=500.0,
        min_samples=5,
        min_stability_window=4,
        max_std_ratio=1.0,
        max_std_pca=1.0,
        max_head_drift_face_xy=0.008,
    )
    gate = FixationGate(cfg=cfg)
    stable = _feat(face_x=0.50, face_y=0.60)
    _lock_and_collect(gate, stable, n=20)
    assert gate.state.value == "LOCKED_COLLECTING"

    drifted = _feat(face_x=0.52, face_y=0.60)
    state, accept, reason = gate.update(drifted, dt_ms=20.0)
    assert not accept
    assert reason == "head_drift"
    assert state.value == "WAIT_LOCK"


def test_head_drift_disabled_allows_shift():
    cfg = FixationGateConfig(
        lock_on_ms=100.0,
        complete_ms=500.0,
        min_samples=5,
        min_stability_window=4,
        max_std_ratio=1.0,
        max_std_pca=1.0,
        enable_head_drift_gate=False,
    )
    gate = FixationGate(cfg=cfg)
    stable = _feat(face_x=0.50, face_y=0.60)
    _lock_and_collect(gate, stable, n=20)
    drifted = _feat(face_x=0.52, face_y=0.60)
    _state, accept, _reason = gate.update(drifted, dt_ms=20.0)
    assert accept


def test_as_built_gate_collapses_pca4_to_binocular_mean_unlike_mapper():
    """As-built: the gate averages the eyes; the mapper does not.

    Desired (T017, unproven): the gate would evaluate the same 4-D vector
    `_raw_uv` hands the mapper, so per-eye motion cannot hide in the mean.
    """
    feat = _feat(pca_uL=0.11, pca_vL=-0.04, pca_uR=0.07, pca_vR=0.02)

    assert _raw_uv(feat) == (0.11, -0.04, 0.07, 0.02)
    assert _pca_uv_mean(feat) == (0.09, -0.01)
    assert len(_pca_uv_mean(feat)) == 2 < len(_raw_uv(feat))


def test_mapper_fit_consumes_four_independent_pca_channels_not_mean_uv():
    samples = [
        (
            _feat(pca_uL=0.01 * i, pca_vL=0.0, pca_uR=0.03 * i, pca_vR=-0.02 * i),
            (100.0 + 10 * i, 200.0),
        )
        for i in range(6)
    ]
    arrays = extract_uv_arrays(samples)
    assert arrays is not None
    u_l, u_r, v_l, v_r, _y = arrays
    assert u_l.shape == (6,)
    assert not np.allclose(u_l, u_r)
    assert not np.allclose(u_l, 0.5 * (u_l + u_r))


def _gate_for_pca_stability(*, jump: bool) -> FixationGate:
    return FixationGate(
        cfg=FixationGateConfig(
            lock_on_ms=80.0,
            complete_ms=400.0,
            min_samples=5,
            min_stability_window=4,
            max_std_ratio=1.0,
            max_std_pca=0.035,
            jump_threshold_ratio=1.0,
            jump_threshold_pca=0.10,
            enable_jump_reset=jump,
            enable_head_drift_gate=False,
        )
    )


def test_as_built_opposing_eye_jitter_locks_because_mean_uv_is_still():
    """As-built: left/right `u` that cancel in the mean look perfectly stable.

    Each frame swings each eye by 0.08 in opposite directions — motion the
    mapper's 4-D fit would see — yet the binocular mean never moves, so the
    gate locks and accepts these frames as a clean fixation.

    Desired (T017, unproven): this should never lock.
    """
    gate = _gate_for_pca_stability(jump=False)
    locked = False
    accepted = False
    for i in range(40):
        sign = 1.0 if i % 2 == 0 else -1.0
        feat = _feat(pca_uL=0.08 * sign, pca_uR=-0.08 * sign)
        state, accept, _reason = gate.update(feat, dt_ms=20.0)
        locked = locked or state.value == "LOCKED_COLLECTING"
        accepted = accepted or accept

    assert locked
    assert accepted


def test_as_built_one_eye_jump_is_halved_by_the_mean_and_escapes_reset():
    """As-built: a 0.15 left-eye jump becomes 0.075 in mean `u`.

    That is below the 0.10 `jump_threshold_pca`, so no reset fires and the
    frame is accepted into the target's samples.

    Desired (T017, unproven): per-eye jump distance would trigger `jump_pca`.
    """
    gate = _gate_for_pca_stability(jump=True)
    stable = _feat()
    _lock_and_collect(gate, stable, n=20)
    assert gate.state.value == "LOCKED_COLLECTING"

    jumped = _feat(pca_uL=0.15, pca_uR=0.0)
    state, accept, reason = gate.update(jumped, dt_ms=20.0)
    assert reason != "jump_pca"
    assert accept
    assert state.value == "LOCKED_COLLECTING"


def test_binocular_stable_gaze_still_collects():
    gate = _gate_for_pca_stability(jump=True)
    feat = _feat(pca_uL=0.02, pca_vL=-0.01, pca_uR=0.02, pca_vR=-0.01)
    _lock_and_collect(gate, feat, n=20)
    state, accept, reason = gate.update(feat, dt_ms=20.0)
    assert state.value == "LOCKED_COLLECTING"
    assert accept
    assert reason == ""
