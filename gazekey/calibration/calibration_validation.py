"""Validate that calibration samples reflect real gaze shifts toward each dot.

Supports both:
- 5-point: TL, TR, center, BL, BR
- 9-point: 3x3 grid in row-major order
"""

from typing import List, Optional, Tuple

import numpy as np

from gazekey.calibration.gaze_features import iris_span_across_points

# Minimum gaze-ratio movement across all dots (0–1 scale)
MIN_GLOBAL_SPAN_X = 0.015
MIN_GLOBAL_SPAN_Y = 0.015
MIN_DIAGONAL_SPAN = 0.025

# Corner dots must differ from each other by at least this much on each axis
MIN_CORNER_SEPARATION = 0.012

# Minimum gaze-ratio shift between consecutive dots
MIN_CONSECUTIVE_SHIFT = 0.012


def _check_corner_ordering(gaze_means: List[Tuple[float, float]]) -> bool:
    """
  True if left-side dots (TL, BL) differ from right-side (TR, BR) on horizontal
    and top dots (TL, TR) differ from bottom (BL, BR) on vertical — either polarity.
    """
    if len(gaze_means) == 5:
        # TL, TR, C, BL, BR
        tl, tr, _, bl, br = gaze_means
    elif len(gaze_means) == 9:
        # 3x3 row-major:
        # 0 TL, 2 TR, 6 BL, 8 BR
        tl, tr, bl, br = gaze_means[0], gaze_means[2], gaze_means[6], gaze_means[8]
    else:
        # Fallback: approximate corners by extrema in ratio space.
        xs = np.array([p[0] for p in gaze_means], dtype=np.float64)
        ys = np.array([p[1] for p in gaze_means], dtype=np.float64)
        tl = gaze_means[int(np.argmin(xs + ys))]
        br = gaze_means[int(np.argmax(xs + ys))]
        tr = gaze_means[int(np.argmax(xs - ys))]
        bl = gaze_means[int(np.argmin(xs - ys))]

    left_h = (tl[0] + bl[0]) / 2.0
    right_h = (tr[0] + br[0]) / 2.0
    top_v = (tl[1] + tr[1]) / 2.0
    bottom_v = (bl[1] + br[1]) / 2.0

    h_sep = abs(left_h - right_h)
    v_sep = abs(top_v - bottom_v)
    return h_sep >= MIN_CORNER_SEPARATION and v_sep >= MIN_CORNER_SEPARATION


def _check_consecutive_shifts(
    gaze_means: List[Tuple[float, float]],
) -> Optional[str]:
    for i in range(1, len(gaze_means)):
        dx = gaze_means[i][0] - gaze_means[i - 1][0]
        dy = gaze_means[i][1] - gaze_means[i - 1][1]
        shift = float(np.hypot(dx, dy))
        if shift < MIN_CONSECUTIVE_SHIFT:
            return (
                f"Point {i + 1}: eyes did not move enough from the previous dot "
                f"({shift:.2f}). Look clearly at each white dot."
            )
    return None


def validate_calibration_gaze(
    gaze_means: List[Tuple[float, float]],
    screen_targets: List[Tuple[float, float]],
    frame_w: float = 640.0,
) -> Optional[str]:
    """
    Return an error message if calibration gaze data does not show real gaze changes.
    Return None if validation passes.
    """
    del frame_w

    if len(gaze_means) < 5 or len(gaze_means) != len(screen_targets):
        return "Internal error: invalid calibration point count."

    span_x, span_y = iris_span_across_points(gaze_means)
    if span_x < MIN_GLOBAL_SPAN_X or span_y < MIN_GLOBAL_SPAN_Y:
        return (
            "Calibration failed: gaze barely moved within the eyes "
            f"({span_x:.2f} horizontal, {span_y:.2f} vertical; "
            f"need at least {MIN_GLOBAL_SPAN_X:.2f} and {MIN_GLOBAL_SPAN_Y:.2f}). "
            "Look at each corner dot with your eyes only — keep your head still."
        )

    if len(gaze_means) == 5:
        tl, br = gaze_means[0], gaze_means[4]
    elif len(gaze_means) == 9:
        tl, br = gaze_means[0], gaze_means[8]
    else:
        tl, br = gaze_means[0], gaze_means[-1]
    diagonal = float(np.hypot(tl[0] - br[0], tl[1] - br[1]))
    if diagonal < MIN_DIAGONAL_SPAN:
        return (
            f"Calibration failed: not enough difference between top-left and bottom-right "
            f"({diagonal:.2f}; need at least {MIN_DIAGONAL_SPAN:.2f}). "
            "Look all the way to each corner dot."
        )

    step_err = _check_consecutive_shifts(gaze_means)
    if step_err is not None:
        return f"Calibration failed: {step_err}"

    if not _check_corner_ordering(gaze_means):
        return (
            "Calibration failed: corner dots did not show enough left/right or up/down "
            "eye movement. Look directly at each white dot — especially the four corners."
        )

    return None
