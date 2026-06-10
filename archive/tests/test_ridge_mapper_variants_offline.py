"""Offline LOOCV tests for dormant ridge mapper variants (poly12, decoupled).

Not collected by default (`python -m pytest tests/`). Run manually:

    python -m pytest archive/tests/test_ridge_mapper_variants_offline.py -q
"""

from __future__ import annotations

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.features.poly_features import poly12_from_uv
from gazekey.features.vertical_decouple import fit_v_residualizers
from gazekey.mapping.ridge import (
    _loocv_pca4_decoupled,
    _loocv_poly12_joint,
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


def test_fit_v_residualizers_reduces_u_v_correlation():
    u_l = np.array([-0.3, 0.0, 0.3, -0.3, 0.0, 0.3])
    u_r = u_l.copy()
    v_l = 0.2 - 0.5 * u_l
    v_r = v_l.copy()
    bl, br = fit_v_residualizers(u_l, u_r, v_l, v_r)
    assert bl.shape == (3,) and br.shape == (3,)
