"""Tests for active PCA4 ridge calibration path (mapper freeze + alpha selection)."""

from __future__ import annotations

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.ridge import (
    ALPHA_GRID,
    ALPHA_SELECT_LOOCV_TOL_PX,
    _auto_alpha,
    fit_calibration_mapper,
)


def _feat(u_l: float, v_l: float, u_r: float, v_r: float, **kwargs) -> FrameFeatures:
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
        face_x=0.6,
        face_y=0.55,
        pca_uL=u_l,
        pca_vL=v_l,
        pca_uR=u_r,
        pca_vR=v_r,
    )
    base.update(kwargs)
    return FrameFeatures(**base)


def _grid_samples_with_horizontal_v_coupling():
    """Same screen row, v feature shifts with horizontal u (webcam coupling)."""
    labels_pts = [
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
    for u_l, v_l, u_r, v_r, x, y in labels_pts:
        v_coupled = v_l - 0.25 * (u_l + u_r)
        out.append((_feat(u_l, v_coupled, u_r, v_coupled - 0.01), (float(x), float(y))))
    return out


def test_frozen_active_mapper_is_pca4_baseline():
    samples = _grid_samples_with_horizontal_v_coupling()
    fit = fit_calibration_mapper(samples=samples, min_alpha=1.0)
    assert fit.success and fit.model is not None
    assert fit.model.mapper_type == "pca4_baseline"
    assert len(fit.candidate_reports) == 1
    assert fit.candidate_reports[0].mapper_type == "pca4_baseline"


def test_auto_alpha_prefers_higher_when_loocv_near_tied():
    loocv_by_alpha = {a: 60.0 for a in ALPHA_GRID}
    loocv_by_alpha.update({1.0: 40.0, 10.0: 41.0, 50.0: 44.0, 100.0: 55.0})
    chosen = _auto_alpha(lambda a: loocv_by_alpha[a], candidate_label="test")
    assert chosen == 50.0
    assert 44.0 - 40.0 <= ALPHA_SELECT_LOOCV_TOL_PX


def test_auto_alpha_picks_highest_when_only_one_near_best():
    loocv_by_alpha = {a: 50.0 for a in ALPHA_GRID}
    loocv_by_alpha[1.0] = 40.0
    chosen = _auto_alpha(lambda a: loocv_by_alpha[a], candidate_label="test")
    assert chosen == 1.0
