"""T020-C: pin corrected eyelid ring slices for aperture; surrounding behavior unchanged.

Product change is the two lid slices in `_eye_uv_one_eye`. These tests lock
that semantics and assert Candidate A/B/T061/gate knobs were not restacked.
"""

from __future__ import annotations

import numpy as np
import pytest

from gazekey.calibration.fixation_gate import FixationGateConfig
from gazekey.features.extractor import _eye_uv_one_eye
from gazekey.mapping.config import MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR
from gazekey.tracking.eye_detector import EyeDetector


def _perp_down(x_hat: np.ndarray) -> np.ndarray:
    y_hat = np.array([-float(x_hat[1]), float(x_hat[0])], dtype=np.float64)
    if float(y_hat[1]) < 0.0:
        y_hat = -y_hat
    return y_hat


def _eye_ring(
    *,
    origin=(0.0, 0.0),
    x_hat=(1.0, 0.0),
    eye_w: float = 2.0,
    lower_v: np.ndarray,
    upper_v: np.ndarray,
) -> list:
    """16-point ring in the same local basis `_eye_uv_one_eye` uses."""
    x_hat = np.asarray(x_hat, dtype=np.float64)
    x_hat = x_hat / float(np.linalg.norm(x_hat))
    y_hat = _perp_down(x_hat)
    origin = np.asarray(origin, dtype=np.float64)
    pts: list = [None] * 16
    pts[0] = tuple(origin - 0.5 * eye_w * x_hat)
    pts[8] = tuple(origin + 0.5 * eye_w * x_hat)
    fracs = np.linspace(-0.4, 0.4, 7)
    for i, (f, v) in enumerate(zip(fracs, lower_v)):
        p = origin + f * eye_w * x_hat + float(v) * y_hat
        pts[1 + i] = (float(p[0]), float(p[1]))
    for i, (f, v) in enumerate(zip(fracs[::-1], upper_v)):
        p = origin + f * eye_w * x_hat + float(v) * y_hat
        pts[9 + i] = (float(p[0]), float(p[1]))
    return pts


def _old_aperture(lower_v: np.ndarray, upper_v: np.ndarray) -> float:
    """Pre-C slices: upper=pos 1-4, lower=pos 5-7 ∪ 9-12."""
    ring_y = np.concatenate([[0.0], lower_v, [0.0], upper_v])
    old_upper = ring_y[1:5]
    old_lower = np.concatenate([ring_y[5:8], ring_y[9:13]])
    return float(abs(np.median(old_lower) - np.median(old_upper)))


def test_detector_ring_maps_lower_1_7_and_upper_9_15():
    left = EyeDetector.LEFT_EYE_INDICES
    right = EyeDetector.RIGHT_EYE_INDICES
    assert left[1:8] == [7, 163, 144, 145, 153, 154, 155]
    assert left[9:16] == [173, 157, 158, 159, 160, 161, 246]
    assert right[1:8] == [382, 381, 380, 374, 373, 390, 249]
    assert right[9:16] == [466, 388, 387, 386, 385, 384, 398]
    assert left[0] == 33 and left[8] == 133
    assert right[0] == 362 and right[8] == 263


def test_aperture_uses_full_lid_arcs_not_the_pre_c_mix():
    lower_v = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07])
    upper_v = np.array([-0.10, -0.20, -0.30, -0.40, -0.50, -0.60, -0.70])
    expected = float(abs(np.median(lower_v) - np.median(upper_v)))
    old = _old_aperture(lower_v, upper_v)
    assert abs(expected - old) > 0.2

    eye_w = 2.0
    raw_v = 0.088
    pts = _eye_ring(eye_w=eye_w, lower_v=lower_v, upper_v=upper_v)
    uv = _eye_uv_one_eye(pts, (0.0, raw_v))
    assert uv is not None
    u_n, v_n = uv
    assert u_n == pytest.approx(0.0, abs=1e-9)
    assert v_n == pytest.approx(raw_v / expected, abs=1e-9)
    assert v_n != pytest.approx(raw_v / old, abs=1e-6)
    assert v_n != pytest.approx(raw_v / eye_w, abs=1e-6)


def test_v_is_iris_over_aperture_u_is_iris_over_eye_width():
    lower_v = np.full(7, 0.15)
    upper_v = np.full(7, -0.15)
    aperture = 0.30
    eye_w = 2.0
    pts = _eye_ring(eye_w=eye_w, lower_v=lower_v, upper_v=upper_v)
    du, dv = 0.40, 0.06
    uv = _eye_uv_one_eye(pts, (du, dv))
    assert uv is not None
    u_n, v_n = uv
    assert u_n == pytest.approx(du / eye_w, abs=1e-9)
    assert v_n == pytest.approx(dv / aperture, abs=1e-9)


def test_vertical_axis_is_still_perp_x_hat_not_image_down():
    theta = np.deg2rad(5.0)
    x_hat = (float(np.cos(theta)), float(np.sin(theta)))
    y_hat = _perp_down(np.asarray(x_hat))
    assert abs(float(y_hat[0])) > 0.08

    pts = _eye_ring(
        x_hat=x_hat,
        eye_w=2.0,
        lower_v=np.full(7, 0.15),
        upper_v=np.full(7, -0.15),
    )
    iris = (0.20, 0.0)
    uv = _eye_uv_one_eye(pts, iris)
    assert uv is not None
    _u_n, v_n = uv
    raw_v = float(np.asarray(iris, dtype=np.float64) @ y_hat)
    assert abs(raw_v) > 1e-6
    assert v_n == pytest.approx(raw_v / 0.30, abs=1e-9)


def test_identical_ring_geometry_gives_matching_aperture_both_eyes():
    lower_v = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07])
    upper_v = np.array([-0.10, -0.20, -0.30, -0.40, -0.50, -0.60, -0.70])
    left = _eye_ring(origin=(-0.3, 0.0), lower_v=lower_v, upper_v=upper_v)
    right = _eye_ring(origin=(0.3, 0.0), lower_v=lower_v, upper_v=upper_v)
    uv_l = _eye_uv_one_eye(left, (-0.3, 0.05))
    uv_r = _eye_uv_one_eye(right, (0.3, 0.05))
    assert uv_l is not None and uv_r is not None
    assert uv_l[1] == pytest.approx(uv_r[1], abs=1e-9)


def test_short_contour_still_falls_back_to_quantile_height():
    pts = [(float(i), 0.04 if i % 2 else -0.04) for i in range(12)]
    uv = _eye_uv_one_eye(pts, (4.0, -0.04))
    assert uv is not None
    u_n, v_n = uv
    assert u_n == pytest.approx(0.0, abs=1e-9)
    assert v_n == pytest.approx(0.0, abs=1e-9)


def test_candidate_c_does_not_retune_gates_or_ear():
    cfg = FixationGateConfig()
    assert cfg.max_std_pca == 0.035
    assert cfg.jump_threshold_pca == 0.10
    assert MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR == 0.15
    assert EyeDetector._EAR_CONTOUR_OFFSETS == (0, 4, 3, 8, 5, 11)
