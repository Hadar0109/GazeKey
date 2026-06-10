"""Tests for per-target head drift rejection during calibration collection."""

from __future__ import annotations

from gazekey.calibration.fixation_gate import FixationGate, FixationGateConfig
from gazekey.features.feature_types import FrameFeatures


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
