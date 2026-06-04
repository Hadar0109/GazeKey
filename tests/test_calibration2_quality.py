"""Tests for calibration v2 quality gates."""

from __future__ import annotations

import numpy as np

from gazekey.calibration2.quality import (
    check_vertical_monotonicity,
    evaluate_calibration_quality,
)
from gazekey.calibration2.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.ridge import RidgeRegressionMapper


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
