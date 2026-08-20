"""Per-target calibration collection: retry on timeout, reject partial samples."""

from __future__ import annotations

import pytest

from gazekey.calibration.fixation_gate import FixationGateConfig
from gazekey.calibration.session import CalibrationSession
from gazekey.calibration.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures


def _targets(n: int = 1) -> list[CalibrationTarget]:
    return [
        CalibrationTarget(
            target_id=f"T{i+1:02d}",
            label=f"p{i}",
            key_id="",
            screen_x=100.0 + i * 50,
            screen_y=200.0,
        )
        for i in range(n)
    ]


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


def _fast_gate(**overrides) -> FixationGateConfig:
    cfg = dict(
        lock_on_ms=40.0,
        complete_ms=120.0,
        point_timeout_ms=300.0,
        min_samples=6,
        min_stability_window=3,
        max_std_ratio=1.0,
        max_std_pca=1.0,
        enable_jump_reset=False,
    )
    cfg.update(overrides)
    return FixationGateConfig(**cfg)


def test_timeout_retries_same_target_and_clears_partial_samples():
    session = CalibrationSession(
        targets=_targets(1),
        session_id="timeout-retry",
        gate_cfg=_fast_gate(min_samples=20, complete_ms=500.0),
        max_timeouts_per_target=2,
    )
    feat = _feat()
    session.begin_target()
    for _ in range(100):
        session.process(feat, dt_ms=20.0)
        if session._timeouts_for_target[0] >= 1:
            break

    assert not session.is_finished
    assert session.target_index == 0
    assert session._timeouts_for_target[0] == 1
    assert session.samples_used_for_target_mean(0) == 0


def test_timeout_exceeding_limit_fails_calibration():
    session = CalibrationSession(
        targets=_targets(1),
        session_id="timeout-fail",
        gate_cfg=_fast_gate(min_samples=20, complete_ms=500.0),
        max_timeouts_per_target=1,
    )
    result = None
    feat = _feat()
    session.begin_target()
    for _ in range(40):
        result = session.process(feat, dt_ms=20.0)
        if result is not None:
            break

    assert result is not None
    assert not result.success
    assert "timed out" in result.message.lower()
    assert session.is_finished


def test_clean_collection_advances_and_produces_training_sample():
    session = CalibrationSession(
        targets=_targets(2),
        session_id="clean-collect",
        gate_cfg=_fast_gate(min_samples=5, complete_ms=100.0, point_timeout_ms=5000.0),
        max_timeouts_per_target=1,
    )
    result = None
    feat = _feat(avg_h=0.4, avg_v=0.3)
    session.begin_target()
    for _ in range(80):
        result = session.process(feat, dt_ms=20.0)
        if result is not None:
            break

    assert result is not None
    assert result.success
    assert session.accepted_count_for_target(0) == 1
    assert session.accepted_count_for_target(1) == 1
    samples = session.get_training_samples()
    assert len(samples) == 2


def test_partial_collection_does_not_finish_target():
    session = CalibrationSession(
        targets=_targets(1),
        session_id="partial",
        gate_cfg=_fast_gate(min_samples=20, complete_ms=100.0, point_timeout_ms=5000.0),
    )
    feat = _feat()
    session.begin_target()
    for _ in range(8):
        session.process(feat, dt_ms=20.0)

    assert session.target_index == 0
    assert session.accepted_count_for_target(0) == 0
    assert session.samples_used_for_target_mean(0) < session.gate.cfg.min_samples


def test_as_built_independent_channel_means_can_invent_unobserved_vector():
    """Pin T019: IQR+mean per channel can yield a 4-D vector no accepted frame had.

    Half the frames are (uL=1, vL=0, …); half are (uL=0, vL=1, …). The as-built
    aggregator stores the channel-wise mean (0.5, 0.5, 0, 0), which was never
    observed. Coherent aggregation (T019) must keep or reject whole frames.
    """
    session = CalibrationSession(
        targets=_targets(1),
        session_id="frankenstein-mean",
        gate_cfg=_fast_gate(),
    )
    frames = []
    for _ in range(4):
        frames.append(_feat(pca_uL=1.0, pca_vL=0.0, pca_uR=0.0, pca_vR=0.0))
    for _ in range(4):
        frames.append(_feat(pca_uL=0.0, pca_vL=1.0, pca_uR=0.0, pca_vR=0.0))
    session._accepted_frames[0] = frames
    session._accepted_ratios[0] = [(0.5, 0.5)] * len(frames)
    session._finalize_target_training_feature(0)

    aggregated = session._accepted_features[0][-1]
    observed = {(fr.pca_uL, fr.pca_vL, fr.pca_uR, fr.pca_vR) for fr in frames}
    invented = (aggregated.pca_uL, aggregated.pca_vL, aggregated.pca_uR, aggregated.pca_vR)
    assert aggregated.pca_uL == pytest.approx(0.5)
    assert aggregated.pca_vL == pytest.approx(0.5)
    assert invented not in observed
