"""Extract gaze features from eye tracking data."""

from typing import List, Optional, Tuple

from gazekey.tracking.eye_detector import EyeData

# GazeTracking uses pupil / (2*center - 10px) in a cropped eye (~80px wide).
# Scale the 10px margin as a fraction of each eye's width/height so far faces
# (small eyes in frame) get the same ratio sensitivity as close faces.
_GAZETRACKING_OFFSET_FRAC = 10.0 / 80.0  # 0.125
_MIN_DENOM_FRAC = 0.5  # never shrink divisor below half the eye span


def _eye_divisor(axis_span: float) -> float:
    """Effective divisor for one eye axis; scales with measured eye size."""
    return max(axis_span * (1.0 - _GAZETRACKING_OFFSET_FRAC), axis_span * _MIN_DENOM_FRAC)


def _gaze_tracking_ratios_one(
    eye_landmarks: List[Tuple[float, float]],
    iris_center: Tuple[float, float],
) -> Optional[Tuple[float, float]]:
    """
    Gaze ratios per eye (GazeTracking-style semantics).

    pupil_axis / (eye_span - margin), margin = 12.5% of eye span (10px on 80px crop).
    README: horizontal right=0, center≈0.5, left=1; vertical top=0, bottom=1.
    """
    xs = [p[0] for p in eye_landmarks]
    ys = [p[1] for p in eye_landmarks]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = max_x - min_x
    height = max_y - min_y
    denom_x = _eye_divisor(width)
    denom_y = _eye_divisor(height)
    if denom_x < 1e-5 or denom_y < 1e-5:
        return None

    local_x = iris_center[0] - min_x
    local_y = iris_center[1] - min_y
    return local_x / denom_x, local_y / denom_y


def gaze_ratios(eye_data: EyeData) -> Optional[Tuple[float, float]]:
    """
    Average left/right horizontal and vertical gaze ratios in [0, 1].

    Compatible with GazeTracking horizontal_ratio() / vertical_ratio() semantics.
    """
    if not eye_data.face_detected:
        return None

    left_iris = eye_data.left_iris_center
    right_iris = eye_data.right_iris_center
    left_eye = eye_data.left_eye_landmarks
    right_eye = eye_data.right_eye_landmarks
    if left_iris is None or right_iris is None or left_eye is None or right_eye is None:
        return None

    left_ratio = _gaze_tracking_ratios_one(left_eye, left_iris)
    right_ratio = _gaze_tracking_ratios_one(right_eye, right_iris)
    if left_ratio is None or right_ratio is None:
        return None

    h = (left_ratio[0] + right_ratio[0]) / 2.0
    v = (left_ratio[1] + right_ratio[1]) / 2.0
    h = max(0.0, min(1.0, h))
    v = max(0.0, min(1.0, v))
    return h, v


def average_iris_pixels(
    eye_data: EyeData,
    frame_w: int,
    frame_h: int,
) -> Optional[Tuple[float, float]]:
    """
    Average left and right iris centers and convert to camera pixel coordinates.

    Returns raw camera-space coordinates. Prefer gaze_ratios() for calibration.
    """
    if not eye_data.face_detected:
        return None

    left = eye_data.left_iris_center
    right = eye_data.right_iris_center
    if left is None or right is None:
        return None

    norm_x = (left[0] + right[0]) / 2.0
    norm_y = (left[1] + right[1]) / 2.0
    pixel_x = norm_x * frame_w
    pixel_y = norm_y * frame_h
    return (pixel_x, pixel_y)


def iris_span_across_points(
    iris_means: list[Tuple[float, float]],
) -> Tuple[float, float]:
    """Return (horizontal span, vertical span) across calibration gaze samples."""
    if not iris_means:
        return 0.0, 0.0
    xs = [p[0] for p in iris_means]
    ys = [p[1] for p in iris_means]
    return max(xs) - min(xs), max(ys) - min(ys)
