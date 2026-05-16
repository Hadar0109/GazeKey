"""Validate that calibration samples reflect real gaze shifts toward each dot."""

from typing import List, Optional, Tuple

import numpy as np

from gazekey.calibration.gaze_features import iris_span_across_points

# Minimum iris movement across all five dots (camera pixels)
MIN_GLOBAL_SPAN_X = 10.0
MIN_GLOBAL_SPAN_Y = 8.0
MIN_DIAGONAL_SPAN = 12.0

# Minimum |correlation| between iris axis and screen axis (proves look-left vs look-right)
MIN_CORR_HORIZONTAL = 0.55
MIN_CORR_VERTICAL = 0.45

# Minimum iris shift between consecutive dots
MIN_CONSECUTIVE_SHIFT = 4.0


def _corr(a: List[float], b: List[float]) -> float:
    if len(a) < 2:
        return 0.0
    c = np.corrcoef(np.array(a, dtype=np.float64), np.array(b, dtype=np.float64))[0, 1]
    if np.isnan(c):
        return 0.0
    return float(c)


def _check_correlation(
    iris_means: List[Tuple[float, float]],
    screen_targets: List[Tuple[float, float]],
    frame_w: float,
) -> bool:
    """True if iris X/Y track screen X/Y in either normal or mirrored X."""
    sxs = [p[0] for p in screen_targets]
    sys = [p[1] for p in screen_targets]
    iys = [p[1] for p in iris_means]

    for flip in (False, True):
        ixs = [
            (frame_w - p[0]) if flip else p[0]
            for p in iris_means
        ]
        corr_x = _corr(ixs, sxs)
        corr_y = _corr(iys, sys)
        if abs(corr_x) >= MIN_CORR_HORIZONTAL and corr_y >= MIN_CORR_VERTICAL:
            return True
    return False


def _check_consecutive_shifts(
    iris_means: List[Tuple[float, float]],
) -> Optional[str]:
    for i in range(1, len(iris_means)):
        dx = iris_means[i][0] - iris_means[i - 1][0]
        dy = iris_means[i][1] - iris_means[i - 1][1]
        shift = float(np.hypot(dx, dy))
        if shift < MIN_CONSECUTIVE_SHIFT:
            from gazekey.calibration.calibration_session import POINT_NAMES

            return (
                f"Point {i + 1} ({POINT_NAMES[i]}): eyes did not move enough from the "
                f"previous dot ({shift:.1f}px). Look clearly at each white dot."
            )
    return None


def validate_calibration_gaze(
    iris_means: List[Tuple[float, float]],
    screen_targets: List[Tuple[float, float]],
    frame_w: float,
) -> Optional[str]:
    """
    Return an error message if calibration iris data does not show real gaze changes.
    Return None if validation passes.
    """
    if len(iris_means) != 5 or len(screen_targets) != 5:
        return "Internal error: expected 5 calibration points."

    span_x, span_y = iris_span_across_points(iris_means)
    if span_x < MIN_GLOBAL_SPAN_X or span_y < MIN_GLOBAL_SPAN_Y:
        return (
            "Calibration failed: iris barely moved in the camera view "
            f"({span_x:.1f}px horizontal, {span_y:.1f}px vertical; "
            f"need at least {MIN_GLOBAL_SPAN_X:.0f}px and {MIN_GLOBAL_SPAN_Y:.0f}px). "
            "Look at each corner dot with your eyes only — keep your head still."
        )

    tl, br = iris_means[0], iris_means[4]
    diagonal = float(np.hypot(tl[0] - br[0], tl[1] - br[1]))
    if diagonal < MIN_DIAGONAL_SPAN:
        return (
            f"Calibration failed: not enough difference between top-left and bottom-right "
            f"({diagonal:.1f}px in camera; need at least {MIN_DIAGONAL_SPAN:.0f}px). "
            "Look all the way to each corner dot."
        )

    step_err = _check_consecutive_shifts(iris_means)
    if step_err is not None:
        return f"Calibration failed: {step_err}"

    if not _check_correlation(iris_means, screen_targets, frame_w):
        return (
            "Calibration failed: iris movement did not match the dot positions. "
            "You must look directly at each white dot when it appears — "
            "do not keep staring at the center of the screen."
        )

    return None
