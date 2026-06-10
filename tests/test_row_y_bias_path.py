"""Phase 8 Iteration 3 — prove the row-Y bias correction path is wired and applied.

Scope: row-Y bias inside the active pca4_baseline path only.
- Correction adjusts Y (row) and never X.
- Active fit returns a row-Y-bias-wrapped pca4_baseline (no mapper-family change).
- Local-Y correction stays disabled.
- Save/load round-trip preserves the correction.
"""

from __future__ import annotations

from gazekey.calibration2.mapper_store import mapper_from_dict, mapper_to_dict
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping import fit_calibration_mapper
from gazekey.mapping.base import MapperPrediction
from gazekey.mapping.local_y_correction import MapperWithLocalYCorrection
from gazekey.mapping.row_bias import MapperWithRowBias, attach_row_y_bias
from gazekey.calibration2.targets import CalibrationTarget


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
    """Minimal inner mapper returning a fixed prediction (for predict-time bias test)."""

    mapper_type = "pca4_baseline"
    alpha = 1.0
    clip_bounds = None

    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    def predict(self, _features: FrameFeatures) -> MapperPrediction:
        return MapperPrediction(x=self._x, y=self._y, quality=1.0)


def test_row_y_bias_corrects_y_only_not_x():
    """Bias is subtracted from Y per nearest row; X is untouched."""
    inner = _StubInner(x=123.0, y=100.0)
    wrapped = attach_row_y_bias(
        inner,
        row_y_centers=(0.0, 100.0, 200.0),
        row_y_bias=(10.0, -5.0, 3.0),
    )
    pred = wrapped.predict(_feat(0.0, 0.0, 0.0, 0.0))
    assert pred is not None
    # Nearest row center to y=100 is index 1 (bias -5.0): py = 100 - (-5) = 105.
    assert pred.y == 105.0
    # X must be identical to the inner prediction.
    assert pred.x == 123.0


def test_row_y_bias_uses_nearest_row_center():
    inner = _StubInner(x=50.0, y=10.0)
    wrapped = attach_row_y_bias(
        inner,
        row_y_centers=(0.0, 100.0, 200.0),
        row_y_bias=(20.0, -5.0, 3.0),
    )
    pred = wrapped.predict(_feat(0.0, 0.0, 0.0, 0.0))
    # Nearest center to y=10 is top (index 0, bias 20): py = 10 - 20 = -10.
    assert pred.y == -10.0
    assert pred.x == 50.0


def test_active_fit_wraps_pca4_with_row_y_bias():
    """With APPLY_ROW_Y_BIAS=True, the active keyboard fit returns a row-Y-bias wrapper."""
    targets = _keyboard_targets_3x3()
    fit = fit_calibration_mapper(
        samples=_keyboard_samples(),
        targets=targets,
        calibration_mode="keyboard15",
        min_alpha=1.0,
    )
    assert fit.success and fit.model is not None
    # Row-Y bias layer is applied in the active path.
    assert isinstance(fit.model, MapperWithRowBias)
    # No mapper-family change: still pca4_baseline underneath.
    assert fit.model.mapper_type == "pca4_baseline"
    # Local-Y correction stays disabled (single lever this iteration).
    assert not isinstance(fit.model, MapperWithLocalYCorrection)
    assert not isinstance(fit.model.inner, MapperWithLocalYCorrection)


def test_row_y_bias_survives_save_load_round_trip():
    """mapper_to_dict/mapper_from_dict preserve row-Y centers/bias and predictions."""
    core_fit = fit_calibration_mapper(samples=_keyboard_samples(), min_alpha=1.0)
    assert core_fit.success and core_fit.model is not None
    # core_fit has no targets -> unwrapped core; wrap explicitly with known bias.
    wrapped = attach_row_y_bias(
        core_fit.model,
        row_y_centers=(0.0, 100.0, 200.0),
        row_y_bias=(12.0, -7.0, 4.0),
    )
    payload = mapper_to_dict(wrapped, calibration_mode="keyboard15", mapper_mode="keyboard15")
    assert payload["row_y_centers"] == [0.0, 100.0, 200.0]
    assert payload["row_y_bias"] == [12.0, -7.0, 4.0]

    restored = mapper_from_dict(payload)
    assert isinstance(restored, MapperWithRowBias)
    assert restored.row_y_centers == (0.0, 100.0, 200.0)
    assert restored.row_y_bias == (12.0, -7.0, 4.0)

    feat = _feat(0.1, 0.05, 0.1, 0.04)
    p_before = wrapped.predict(feat)
    p_after = restored.predict(feat)
    assert p_before is not None and p_after is not None
    assert abs(p_before.x - p_after.x) < 1e-6
    assert abs(p_before.y - p_after.y) < 1e-6
