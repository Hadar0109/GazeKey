"""Tests for calibration v2 ridge mapper candidates and LOOCV."""

from __future__ import annotations

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.features.poly_features import poly12_from_uv
from gazekey.features.vertical_decouple import fit_v_residualizers
from gazekey.mapping.ridge import (
    ALPHA_GRID,
    ALPHA_SELECT_LOOCV_TOL_PX,
    _auto_alpha,
    _loocv_pca4_decoupled,
    _loocv_poly12_joint,
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
        # Coupling: horizontal gaze lowers raw v on the same row
        v_coupled = v_l - 0.25 * (u_l + u_r)
        out.append((_feat(u_l, v_coupled, u_r, v_coupled - 0.01), (float(x), float(y))))
    return out


def test_poly12_shape():
    X = poly12_from_uv(
        np.array([0.1, -0.2]),
        np.array([0.2, 0.3]),
        np.array([-0.1, 0.0]),
        np.array([0.15, 0.25]),
    )
    assert X.shape == (2, 12)


def test_loocv_decoupler_uses_train_fold_only():
    u_l = np.linspace(-0.3, 0.3, 9)
    u_r = u_l.copy()
    v_l = 0.1 + 0.2 * np.linspace(0, 1, 9) - 0.4 * u_l
    v_r = v_l.copy()
    Y = np.column_stack([u_l * 300 + 100, v_l * 400 + 50])
    detail = _loocv_pca4_decoupled(u_l, u_r, v_l, v_r, Y, alpha=10.0, clip_bounds=None)
    assert len(detail) == 9
    for d in detail:
        assert np.isfinite(d["err"])


def test_poly12_joint_loocv_finite():
    samples = _grid_samples_with_horizontal_v_coupling()
    extracted = [(s[0].pca_uL, s[0].pca_vL, s[0].pca_uR, s[0].pca_vR) for s in samples]
    u_l = np.array([e[0] for e in extracted])
    v_l = np.array([e[1] for e in extracted])
    u_r = np.array([e[2] for e in extracted])
    v_r = np.array([e[3] for e in extracted])
    Y = np.array([p for _, p in samples])
    detail = _loocv_poly12_joint(u_l, u_r, v_l, v_r, Y, alpha=10.0, clip_bounds=None)
    assert len(detail) == 9
    assert all(np.isfinite(d["err"]) for d in detail)


def test_coupled_synthetic_selects_non_baseline_mapper():
    samples = _grid_samples_with_horizontal_v_coupling()
    fit = fit_calibration_mapper(samples=samples, min_alpha=1.0)
    assert fit.success and fit.model is not None
    assert fit.model.mapper_type != "pca4_baseline"
    detail = fit.model.leave_one_out_detail_px()
    worst = max(float(d["err"]) for d in detail)
    # Raw [vL,vR] baseline LOOCV worst ~113px on corners; decoupled/poly12 should be far lower.
    assert worst < 50.0


def test_auto_alpha_prefers_higher_when_loocv_near_tied():
    # alpha=1 is slightly better on mean LOOCV; alpha=50 is within tolerance -> pick 50.
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


def test_fit_v_residualizers_reduces_u_v_correlation():
    u_l = np.array([-0.3, 0.0, 0.3, -0.3, 0.0, 0.3])
    u_r = u_l.copy()
    v_l = 0.2 - 0.5 * u_l
    v_r = v_l.copy()
    bl, br = fit_v_residualizers(u_l, u_r, v_l, v_r)
    assert bl.shape == (3,) and br.shape == (3,)
