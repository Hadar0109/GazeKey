"""Unit tests for calibration math and session validation."""

import numpy as np
import pytest

from gazekey.calibration.gaze_mapper import InterpolationGazeMapper, fit_gaze_mapper
from gazekey.calibration.calibration_validation import validate_calibration_gaze
from gazekey.calibration.calibration_session import (
    CalibrationSession,
    MIN_SAMPLES,
    MIN_SHIFT_FROM_PREVIOUS,
    compute_calibration_targets,
)
from gazekey.calibration.calibration_store import CalibrationStore
from gazekey.calibration.gaze_features import average_iris_pixels, gaze_ratios
from gazekey.tracking.eye_detector import EyeData

# Realistic gaze-ratio pattern (eye-relative, not camera pixels)
_GAZE_TL_TR_CENTER_BL_BR = [
    (0.38, 0.38),
    (0.62, 0.38),
    (0.50, 0.50),
    (0.40, 0.62),
    (0.60, 0.63),
]

_GAZE_INTERP_POINTS = [
    (0.36, 0.37),
    (0.64, 0.37),
    (0.50, 0.50),
    (0.38, 0.63),
    (0.62, 0.64),
]


def _eye_data_with_landmarks(
    left_iris: tuple[float, float],
    right_iris: tuple[float, float],
) -> EyeData:
    """Build minimal eye contours around each iris for ratio tests."""
    lx, ly = left_iris
    rx, ry = right_iris
    left_eye = [
        (lx - 0.08, ly - 0.04),
        (lx + 0.08, ly - 0.04),
        (lx + 0.08, ly + 0.04),
        (lx - 0.08, ly + 0.04),
    ]
    right_eye = [
        (rx - 0.08, ry - 0.04),
        (rx + 0.08, ry - 0.04),
        (rx + 0.08, ry + 0.04),
        (rx - 0.08, ry + 0.04),
    ]
    return EyeData(
        face_detected=True,
        subject_left_iris_center=left_iris,
        subject_right_iris_center=right_iris,
        subject_left_eye_landmarks=left_eye,
        subject_right_eye_landmarks=right_eye,
    )


def test_average_iris_pixels():
    eye_data = EyeData(
        face_detected=True,
        subject_left_iris_center=(0.2, 0.3),
        subject_right_iris_center=(0.4, 0.5),
    )
    result = average_iris_pixels(eye_data, 640, 480)
    assert abs(result[0] - 192.0) < 0.01


def test_gaze_ratios_in_range():
    eye_data = _eye_data_with_landmarks((0.5, 0.5), (0.5, 0.5))
    ratios = gaze_ratios(eye_data)
    assert ratios is not None
    assert 0.0 <= ratios[0] <= 1.0
    assert 0.0 <= ratios[1] <= 1.0


def test_gaze_ratio_stable_across_eye_sizes():
    """Same relative iris position → similar ratio for close vs far face sizes."""

    def _box(iris: tuple[float, float], half_w: float, half_h: float) -> EyeData:
        ix, iy = iris
        eye = [
            (ix - half_w, iy - half_h),
            (ix + half_w, iy - half_h),
            (ix + half_w, iy + half_h),
            (ix - half_w, iy + half_h),
        ]
        return EyeData(
            face_detected=True,
            subject_left_iris_center=iris,
            subject_right_iris_center=iris,
            subject_left_eye_landmarks=eye,
            subject_right_eye_landmarks=eye,
        )

    # Iris 25% across the eye box (same relative position, different absolute size)
    close = _box((0.5, 0.5), half_w=0.08, half_h=0.04)
    far = _box((0.5, 0.5), half_w=0.03, half_h=0.015)
    # Offset iris toward top-left corner of box by 25% of span
    for half_w, half_h in ((0.08, 0.04), (0.03, 0.015)):
        ix = 0.5 - half_w + 0.25 * (2 * half_w)
        iy = 0.5 - half_h + 0.25 * (2 * half_h)
        if half_w == 0.08:
            close = _box((ix, iy), half_w, half_h)
        else:
            far = _box((ix, iy), half_w, half_h)

    r_close = gaze_ratios(close)
    r_far = gaze_ratios(far)
    assert r_close is not None and r_far is not None
    assert abs(r_close[0] - r_far[0]) < 0.02
    assert abs(r_close[1] - r_far[1]) < 0.02


def test_validation_accepts_small_span():
    """Spans that failed at normal laptop distance should pass after tuning."""
    screen = compute_calibration_targets(0, 0, 1280, 720)
    gaze_means = [
        (0.48, 0.48),
        (0.52, 0.48),
        (0.50, 0.50),
        (0.48, 0.52),
        (0.52, 0.52),
    ]
    msg = validate_calibration_gaze(gaze_means, screen, 640.0)
    assert msg is None


def test_reject_static_gaze():
    """Same gaze ratio at all five dots should fail validation."""
    screen = compute_calibration_targets(0, 0, 1280, 720)
    static = (0.5, 0.5)
    gaze_means = [static] * 5
    msg = validate_calibration_gaze(gaze_means, screen, 640.0)
    assert msg is not None
    assert "barely moved" in msg or "did not match" in msg


def test_accept_realistic_gaze_pattern():
    screen = compute_calibration_targets(0, 0, 1280, 720)
    gaze_means = list(_GAZE_TL_TR_CENTER_BL_BR)
    msg = validate_calibration_gaze(gaze_means, screen, 640.0)
    assert msg is None
    result = fit_gaze_mapper(list(zip(gaze_means, screen)), 640, 480)
    assert result.success


def test_session_rejects_no_shift_between_points():
    targets = compute_calibration_targets(0, 0, 1920, 1080)
    session = CalibrationSession(targets, frame_w=640, frame_h=480)
    session.begin_collect()
    for _ in range(MIN_SAMPLES + 5):
        session.add_sample(0.5, 0.5)
    session.finish_collect()
    session.begin_collect()
    for _ in range(MIN_SAMPLES + 5):
        session.add_sample(0.5, 0.5)
    result = session.finish_collect()
    assert result is not None
    assert not result.success
    assert "did not move" in result.message.lower()


def test_interpolation_exact_at_calibration_points():
    targets = compute_calibration_targets(0, 0, 1920, 1080)
    gaze_pts = list(_GAZE_INTERP_POINTS)
    pairs = list(zip(gaze_pts, targets))
    assert validate_calibration_gaze(gaze_pts, targets, 640.0) is None
    result = fit_gaze_mapper(pairs, 640, 480)
    assert result.success
    for (gh, gv), (sx, sy) in pairs:
        mx, my = result.mapper.map_point(gh, gv)
        assert np.hypot(mx - sx, my - sy) < 0.01


def test_store_roundtrip(tmp_path):
    targets = compute_calibration_targets(0, 0, 1920, 1080)
    gaze_pts = list(_GAZE_INTERP_POINTS)
    pairs = list(zip(gaze_pts, targets))
    result = fit_gaze_mapper(pairs, 640, 480)
    assert result.success
    store = CalibrationStore(tmp_path / "calibration_data.json")
    assert store.save(result.mapper, targets, gaze_pts)
    loaded = store.load()
    assert loaded is not None
    assert isinstance(loaded.mapper, InterpolationGazeMapper)
    for (gh, gv), (sx, sy) in pairs:
        mx, my = loaded.mapper.map_point(gh, gv)
        assert np.hypot(mx - sx, my - sy) < 0.01
