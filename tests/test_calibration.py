"""Unit tests for calibration math and session validation."""

import numpy as np
import pytest

from gazekey.calibration.gaze_mapper import InterpolationGazeMapper, fit_gaze_mapper
from gazekey.calibration.calibration_validation import validate_calibration_gaze
from gazekey.calibration.calibration_session import (
    CalibrationSession,
    MIN_SAMPLES,
    MIN_SHIFT_FROM_PREVIOUS_PX,
    compute_calibration_targets,
)
from gazekey.calibration.calibration_store import CalibrationStore
from gazekey.calibration.gaze_features import average_iris_pixels
from gazekey.tracking.eye_detector import EyeData


def test_average_iris_pixels():
    eye_data = EyeData(
        face_detected=True,
        subject_left_iris_center=(0.2, 0.3),
        subject_right_iris_center=(0.4, 0.5),
    )
    result = average_iris_pixels(eye_data, 640, 480)
    assert abs(result[0] - 192.0) < 0.01


def test_reject_static_gaze():
    """Same iris at all five dots should fail validation."""
    screen = compute_calibration_targets(0, 0, 1280, 720)
    static = (345.0, 220.0)
    iris_means = [static] * 5
    msg = validate_calibration_gaze(iris_means, screen, 640.0)
    assert msg is not None
    assert "barely moved" in msg or "did not match" in msg


def test_accept_realistic_gaze_pattern():
    screen = compute_calibration_targets(0, 0, 1280, 720)
    iris_means = [
        (330.0, 210.0),
        (360.0, 212.0),
        (345.0, 225.0),
        (332.0, 245.0),
        (358.0, 248.0),
    ]
    msg = validate_calibration_gaze(iris_means, screen, 640.0)
    assert msg is None
    result = fit_gaze_mapper(list(zip(iris_means, screen)), 640, 480)
    assert result.success


def test_session_rejects_no_shift_between_points():
    targets = compute_calibration_targets(0, 0, 1920, 1080)
    session = CalibrationSession(targets, frame_w=640, frame_h=480)
    session.begin_collect()
    for _ in range(MIN_SAMPLES + 5):
        session.add_sample(320.0, 240.0)
    session.finish_collect()
    session.begin_collect()
    for _ in range(MIN_SAMPLES + 5):
        session.add_sample(320.0, 240.0)
    result = session.finish_collect()
    assert result is not None
    assert not result.success
    assert "did not move" in result.message.lower()


def test_interpolation_exact_at_calibration_points():
    targets = compute_calibration_targets(0, 0, 1920, 1080)
    iris_pts = [(310, 235), (330, 232), (320, 240), (312, 248), (328, 250)]
    pairs = list(zip(iris_pts, targets))
    assert validate_calibration_gaze(iris_pts, targets, 640.0) is None
    result = fit_gaze_mapper(pairs, 640, 480)
    assert result.success
    for (ix, iy), (sx, sy) in pairs:
        mx, my = result.mapper.map_point(ix, iy)
        assert np.hypot(mx - sx, my - sy) < 0.01


def test_store_roundtrip(tmp_path):
    targets = compute_calibration_targets(0, 0, 1920, 1080)
    iris_pts = [(310, 235), (330, 232), (320, 240), (312, 248), (328, 250)]
    pairs = list(zip(iris_pts, targets))
    result = fit_gaze_mapper(pairs, 640, 480)
    assert result.success
    store = CalibrationStore(tmp_path / "calibration_data.json")
    assert store.save(result.mapper, targets, iris_pts)
    loaded = store.load()
    assert loaded is not None
