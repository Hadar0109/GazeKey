"""FR-030: mapper fit is spatial only (features → x,y). No key_id / label / row in X."""

from __future__ import annotations

import inspect

import pytest

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import Mapper
from gazekey.mapping.ridge import RidgeRegressionMapper, fit_calibration_mapper


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


def _grid_samples():
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
    return [(_feat(u_l, v_l, u_r, v_r), (float(x), float(y))) for u_l, v_l, u_r, v_r, x, y in pts]


def test_fit_signatures_reject_key_id_label_row_as_regression_inputs():
    for fn in (fit_calibration_mapper, RidgeRegressionMapper.fit):
        params = inspect.signature(fn).parameters
        assert "key_id" not in params
        assert "label" not in params
        assert "row" not in params
        assert "grid_row" not in params
        assert "grid_col" not in params


def test_mapper_fit_protocol_is_features_to_xy_only():
    pred = inspect.signature(Mapper.predict)
    assert list(pred.parameters) == ["self", "features"]


def test_fit_raises_if_key_id_passed_as_kwarg():
    samples = _grid_samples()
    with pytest.raises(TypeError):
        RidgeRegressionMapper.fit(samples=samples, key_id="Q")
    with pytest.raises(TypeError):
        fit_calibration_mapper(samples=samples, label="key_q")


def test_trained_matrices_are_uv_features_and_screen_xy():
    fit = fit_calibration_mapper(samples=_grid_samples(), min_alpha=1.0)
    assert fit.success and fit.model is not None
    model = fit.model
    assert model.train_X.shape[1] == 4
    assert model.train_Y.shape[1] == 2
    assert not hasattr(model, "train_key_id")
    assert not hasattr(model, "train_labels")
