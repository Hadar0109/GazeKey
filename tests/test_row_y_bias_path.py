"""Row-Y bias correction on the active PCA4 ridge path."""

from __future__ import annotations

from gazekey.calibration.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping import fit_calibration_mapper
from gazekey.mapping.base import MapperPrediction
from gazekey.mapping.row_bias import MapperWithRowBias, attach_row_y_bias


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


def _keyboard_targets_3x3() -> list[CalibrationTarget]:
    pts = [
        (0.0, 0.0), (100.0, 0.0), (200.0, 0.0),
        (0.0, 100.0), (100.0, 100.0), (200.0, 100.0),
        (0.0, 200.0), (100.0, 200.0), (200.0, 200.0),
    ]
    out = []
    for i, (x, y) in enumerate(pts):
        out.append(
            CalibrationTarget(
                target_id=f"T{i+1:02d}",
                label=f"r{i // 3}c{i % 3}",
                key_id="",
                screen_x=x,
                screen_y=y,
                grid_row=int(i // 3),
                grid_col=int(i % 3),
            )
        )
    return out


def _keyboard_samples() -> list:
    targets = _keyboard_targets_3x3()
    out = []
    for i, t in enumerate(targets):
        col = i % 3
        row = i // 3
        u = -0.3 + 0.3 * col
        v = 0.0 + 0.15 * row
        v_coupled = v - 0.25 * (u + u)
        out.append((_feat(u, v_coupled, u, v_coupled - 0.01), (t.screen_x, t.screen_y)))
    return out


class _StubInner:
    mapper_type = "pca4_baseline"
    alpha = 1.0
    clip_bounds = None

    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    def predict(self, _features: FrameFeatures) -> MapperPrediction:
        return MapperPrediction(x=self._x, y=self._y, quality=1.0)


def test_row_y_bias_corrects_y_only_not_x():
    inner = _StubInner(x=123.0, y=100.0)
    wrapped = attach_row_y_bias(
        inner,
        row_y_centers=(0.0, 100.0, 200.0),
        row_y_bias=(10.0, -5.0, 3.0),
    )
    pred = wrapped.predict(_feat(0.0, 0.0, 0.0, 0.0))
    assert pred is not None
    assert pred.y == 105.0
    assert pred.x == 123.0


def test_active_fit_does_not_wrap_pca4_when_row_bias_disabled():
    targets = _keyboard_targets_3x3()
    fit = fit_calibration_mapper(
        samples=_keyboard_samples(),
        targets=targets,
        calibration_mode="keyboard15",
        min_alpha=1.0,
    )
    assert fit.success and fit.model is not None
    assert not isinstance(fit.model, MapperWithRowBias)
    assert fit.model.mapper_type == "pca4_baseline"


def test_active_fit_wraps_pca4_with_row_y_bias_when_enabled(monkeypatch):
    import gazekey.mapping.ridge as ridge_mod

    monkeypatch.setattr(ridge_mod, "APPLY_ROW_Y_BIAS", True)
    targets = _keyboard_targets_3x3()
    fit = fit_calibration_mapper(
        samples=_keyboard_samples(),
        targets=targets,
        calibration_mode="keyboard15",
        min_alpha=1.0,
    )
    assert fit.success and fit.model is not None
    assert isinstance(fit.model, MapperWithRowBias)
    assert fit.model.mapper_type == "pca4_baseline"
