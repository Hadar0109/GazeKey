"""Tests for the frozen typing-candidate configuration."""

from __future__ import annotations

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping import ACTIVE_MAPPER, TYPING_CANDIDATE_ID, fit_calibration_mapper
from gazekey.mapping.ridge import FROZEN_ACTIVE_MAPPER
from gazekey.mapping.typing_candidate import (
    APPLY_LOCAL_Y_CORRECTION,
    APPLY_ROW_Y_BIAS,
    CALIBRATION_MODE,
    FEATURE_SMOOTHER_ALPHA,
    GAZE_SMOOTHER_ALPHA,
)


def _feat(u_l: float, v_l: float, u_r: float, v_r: float) -> FrameFeatures:
    return FrameFeatures(
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
        face_x=0.6,
        face_y=0.55,
        pca_uL=u_l,
        pca_vL=v_l,
        pca_uR=u_r,
        pca_vR=v_r,
    )


def _minimal_calibration_samples():
    pts = [
        (-0.3, 0.0, -0.3, 0.0, 0, 0),
        (0.0, 0.0, 0.0, 0.0, 100, 0),
        (0.3, 0.0, 0.3, 0.0, 200, 0),
        (-0.3, 0.15, -0.3, 0.15, 0, 100),
        (0.0, 0.15, 0.0, 0.15, 100, 100),
        (0.3, 0.15, 0.3, 0.15, 200, 100),
        (-0.3, 0.30, -0.3, 0.30, 0, 200),
        (0.0, 0.30, 0.0, 0.30, 100, 200),
        (0.3, 0.30, 0.3, 0.30, 200, 200),
    ]
    out = []
    for u_l, v_l, u_r, v_r, x, y in pts:
        v_coupled = v_l - 0.25 * (u_l + u_r)
        out.append((_feat(u_l, v_coupled, u_r, v_coupled - 0.01), (float(x), float(y))))
    return out


def test_typing_candidate_identity():
    assert TYPING_CANDIDATE_ID == "pca4_baseline_v1"
    assert ACTIVE_MAPPER == "pca4_baseline"
    assert FROZEN_ACTIVE_MAPPER == ACTIVE_MAPPER


def test_typing_candidate_pipeline_constants():
    from gazekey.mapping.typing_candidate import ENABLE_TYPING_ON_BEST_EFFORT

    assert CALIBRATION_MODE == "keyboard15"
    assert APPLY_ROW_Y_BIAS is False
    assert APPLY_LOCAL_Y_CORRECTION is False
    assert FEATURE_SMOOTHER_ALPHA == 0.28
    assert GAZE_SMOOTHER_ALPHA == 0.35
    assert ENABLE_TYPING_ON_BEST_EFFORT is False


def test_fit_calibration_mapper_only_evaluates_frozen_mapper():
    fit = fit_calibration_mapper(samples=_minimal_calibration_samples(), min_alpha=1.0)
    assert fit.success and fit.model is not None
    assert len(fit.candidate_reports) == 1
    assert fit.candidate_reports[0].mapper_type == ACTIVE_MAPPER
