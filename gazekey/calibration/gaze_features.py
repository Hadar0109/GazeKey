"""Extract gaze features from eye tracking data."""

from typing import Optional, Tuple

from gazekey.tracking.eye_detector import EyeData


def average_iris_pixels(
    eye_data: EyeData,
    frame_w: int,
    frame_h: int,
    flip_x: bool = False,
) -> Optional[Tuple[float, float]]:
    """
    Average left and right iris centers and convert to camera pixel coordinates.

    MediaPipe returns normalized (0-1) coordinates; multiply by frame dimensions
    to get raw iris position in the camera image.

    flip_x: mirror horizontal axis (common for front-facing webcams vs screen coords).
    """
    if not eye_data.face_detected:
        return None

    left = eye_data.left_iris_center
    right = eye_data.right_iris_center
    if left is None or right is None:
        return None

    norm_x = (left[0] + right[0]) / 2.0
    norm_y = (left[1] + right[1]) / 2.0
    if flip_x:
        norm_x = 1.0 - norm_x
    pixel_x = norm_x * frame_w
    pixel_y = norm_y * frame_h
    return (pixel_x, pixel_y)


def iris_span_across_points(
    iris_means: list[Tuple[float, float]],
) -> Tuple[float, float]:
    """Return (horizontal span, vertical span) across calibration iris means."""
    if not iris_means:
        return 0.0, 0.0
    xs = [p[0] for p in iris_means]
    ys = [p[1] for p in iris_means]
    return max(xs) - min(xs), max(ys) - min(ys)
