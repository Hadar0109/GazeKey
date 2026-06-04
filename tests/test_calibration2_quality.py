"""Tests for calibration v2 quality gates."""

from __future__ import annotations

import numpy as np

from gazekey.calibration2.quality import (
    check_vertical_monotonicity,
    evaluate_calibration_quality,
)
from gazekey.calibration2.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperPrediction


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
        face_x=0.6,
        face_y=0.55,
        pca_uL=0.0,
        pca_vL=0.0,
        pca_uR=0.0,
        pca_vR=0.0,
    )
    base.update(kwargs)
    return FrameFeatures(**base)


def _targets_3x3():
    labels = [
        "top_left",
        "top",
        "top_right",
        "left",
        "center",
        "right",
        "bottom_left",
        "bottom",
        "bottom_right",
    ]
    pts = [
        (0, 0),
        (100, 0),
        (200, 0),
        (0, 100),
        (100, 100),
        (200, 100),
        (0, 200),
        (100, 200),
        (200, 200),
    ]
    return [
        CalibrationTarget(target_id=f"T{i+1:02d}", label=labels[i], key_id="", screen_x=float(x), screen_y=float(y))
        for i, (x, y) in enumerate(pts)
    ]


def test_monotonicity_valid():
    from gazekey.calibration2.quality import VerticalRowStats

    stats = [
        VerticalRowStats("top", ("a",), 0.1, -0.4, -0.4, -0.4, 0.5, 0.02),
        VerticalRowStats("mid", ("b",), 0.2, -0.2, -0.2, -0.2, 0.55, 0.02),
        VerticalRowStats("bottom", ("c",), 0.3, 0.0, 0.0, 0.0, 0.6, 0.02),
    ]
    r = check_vertical_monotonicity(stats, feature_attr="avg_v")
    assert r.valid


def test_monotonicity_invalid():
    from gazekey.calibration2.quality import VerticalRowStats

    stats = [
        VerticalRowStats("top", ("a",), 0.2, None, None, None, None, None),
        VerticalRowStats("mid", ("b",), 0.2, None, None, None, None, None),
        VerticalRowStats("bottom", ("c",), 0.21, None, None, None, None, None),
    ]
    r = check_vertical_monotonicity(stats, feature_attr="avg_v", min_separation=0.008)
    assert not r.valid


class _ExactTrainMapper:
    """Mock mapper: predict returns each sample's target (for gate tests)."""

    def __init__(
        self,
        samples: list,
        *,
        loocv_detail: list | None = None,
    ) -> None:
        self.samples = samples
        self.mapper_type = "mock_exact"
        self.alpha = 1.0
        self.clip_bounds = (0.0, 0.0, 500.0, 500.0)
        self._loocv_detail = loocv_detail

    def predict(self, feat: FrameFeatures) -> MapperPrediction | None:
        for f, (tx, ty) in self.samples:
            if f is feat:
                return MapperPrediction(x=float(tx), y=float(ty), quality=1.0)
        return None

    def leave_one_out_detail_px(self) -> list:
        if self._loocv_detail is not None:
            return self._loocv_detail
        out = []
        for i, (_f, (tx, ty)) in enumerate(self.samples):
            out.append(
                {
                    "i": i,
                    "pred_x": float(tx),
                    "pred_y": float(ty),
                    "err": 0.0,
                }
            )
        return out


def _keyboard_targets_3x3() -> list[CalibrationTarget]:
    labels = [
        "row0_left",
        "row0_center",
        "row0_right",
        "row1_left",
        "row1_center",
        "row1_right",
        "row2_left",
        "row2_center",
        "row2_right",
    ]
    pts = [
        (100.0, 100.0),
        (250.0, 100.0),
        (400.0, 100.0),
        (100.0, 200.0),
        (250.0, 200.0),
        (400.0, 200.0),
        (100.0, 300.0),
        (250.0, 300.0),
        (400.0, 300.0),
    ]
    out = []
    for i, (x, y) in enumerate(pts):
        out.append(
            CalibrationTarget(
                target_id=f"T{i+1:02d}",
                label=labels[i],
                key_id="",
                screen_x=x,
                screen_y=y,
                grid_row=int(i // 3),
                grid_col=int(i % 3),
            )
        )
    return out


def _keyboard_samples_from_avg_v(avg_vs: list[float]) -> list:
    """Build 9 samples with monotonic PCA v and distinct within-row spread."""
    targets = _keyboard_targets_3x3()
    samples = []
    for i, t in enumerate(targets):
        row = i // 3
        col = i % 3
        v = float(avg_vs[i])
        pca_v = v - 0.5
        u = -0.1 + 0.05 * col
        samples.append(
            (
                _feat(
                    avg_h=0.3 + 0.1 * col,
                    avg_v=v,
                    pca_uL=u,
                    pca_vL=pca_v - 0.02,
                    pca_uR=u + 0.01,
                    pca_vR=pca_v + 0.02,
                    face_y=0.5 + 0.05 * row,
                ),
                (t.screen_x, t.screen_y),
            )
        )
    return samples


def test_keyboard_avg_v_correlation_soft_warning():
    """0.15 <= r < 0.55 on keyboard: accept with warning, not hard fail."""
    # Tuned for r in soft band with repeated screen_y per row (keyboard15-like).
    avg_vs = [
        0.22,
        0.10,
        0.04,
        0.24,
        0.14,
        0.08,
        0.28,
        0.20,
        0.12,
    ]
    samples = _keyboard_samples_from_avg_v(avg_vs)
    targets = _keyboard_targets_3x3()
    ys = np.array([t.screen_y for t in targets], dtype=np.float64)
    vs = np.array(avg_vs, dtype=np.float64)
    corr = float(np.corrcoef(ys, vs)[0, 1])
    assert 0.15 <= corr < 0.55

    model = _ExactTrainMapper(samples)
    q = evaluate_calibration_quality(
        model=model,
        samples=samples,
        targets=targets,
        screen_rect=(0.0, 0.0, 500.0, 500.0),
        calibration_mode="keyboard15",
        loocv_detail=model.leave_one_out_detail_px(),
        require_any_vertical_monotonic=True,
        min_screen_y_avg_v_corr=0.55,
        min_catastrophic_screen_y_avg_v_corr=0.15,
    )
    assert q.accepted
    assert not q.reasons
    assert len(q.warnings) == 1
    assert "below preferred 0.55" in q.warnings[0]
    assert q.screen_y_avg_v_corr is not None
    assert abs(float(q.screen_y_avg_v_corr) - corr) < 1e-5


def test_keyboard_avg_v_correlation_catastrophic_fail():
    """r < 0.15 on keyboard: still hard fail."""
    avg_vs = [0.15] * 9
    samples = _keyboard_samples_from_avg_v(avg_vs)
    targets = _keyboard_targets_3x3()
    model = _ExactTrainMapper(samples)
    q = evaluate_calibration_quality(
        model=model,
        samples=samples,
        targets=targets,
        screen_rect=(0.0, 0.0, 500.0, 500.0),
        calibration_mode="keyboard15",
        loocv_detail=model.leave_one_out_detail_px(),
        require_any_vertical_monotonic=False,
        min_catastrophic_screen_y_avg_v_corr=0.15,
    )
    assert not q.accepted
    assert any("catastrophic" in r for r in q.reasons)
    assert not q.warnings


def test_fullscreen_avg_v_correlation_still_hard_fail():
    """Fullscreen keeps hard fail below 0.15 (not keyboard soft band)."""
    targets = _targets_3x3()
    samples = []
    for i, t in enumerate(targets):
        samples.append((_feat(avg_v=0.12), (t.screen_x, t.screen_y)))
    model = _ExactTrainMapper(samples)
    q = evaluate_calibration_quality(
        model=model,
        samples=samples,
        targets=targets,
        screen_rect=(0.0, 0.0, 300.0, 300.0),
        calibration_mode="fullscreen9",
        loocv_detail=model.leave_one_out_detail_px(),
        require_any_vertical_monotonic=False,
        min_catastrophic_screen_y_avg_v_corr=0.15,
    )
    assert not q.accepted
    assert any("avg_v poorly correlated" in r for r in q.reasons)


def test_quality_rejects_high_train_error():
    targets = _targets_3x3()
    # Synthetic features with clear vertical trend
    samples = []
    for i, t in enumerate(targets):
        row = i // 3
        v = 0.1 + 0.1 * row
        samples.append(
            (
                _feat(
                    avg_h=0.3 + 0.2 * (i % 3),
                    avg_v=v,
                    pca_vL=v - 0.5,
                    pca_vR=v - 0.5,
                    face_y=0.5 + 0.05 * row,
                ),
                (t.screen_x, t.screen_y),
            )
        )
    from gazekey.mapping.ridge import fit_calibration_mapper

    fit = fit_calibration_mapper(
        samples=samples,
        min_alpha=1.0,
        max_train_error_px=200.0,
        max_loocv_rms_px=500.0,
        max_target_loocv_px=500.0,
    )
    assert fit.success and fit.model is not None
    # Perturb one target to force huge train error by mislabeling screen y in samples
    bad_samples = list(samples)
    f, (x, y) = bad_samples[0]
    bad_samples[0] = (f, (x, 9999.0))
    q = evaluate_calibration_quality(
        model=fit.model,
        samples=bad_samples,
        targets=targets,
        screen_rect=(0.0, 0.0, 300.0, 300.0),
        max_train_error_px=50.0,
        max_loocv_rms_px=500.0,
        require_any_vertical_monotonic=False,
    )
    assert not q.accepted
