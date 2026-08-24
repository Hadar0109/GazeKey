"""Official GazeInfo → GazeSample mapping. Does not copy features."""

from __future__ import annotations

import math
from typing import Any

from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.geometry import GeometryConfig, apply_geometry

# Official DefaultConfig.eye_blink_threshold
OPENNESS_THRESHOLD = 10.0
SUCCESS_STATE = "SUCCESS"


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _finite_xy(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    try:
        if len(value) != 2:
            return None
        x = float(value[0])
        y = float(value[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(x) or not math.isfinite(y):
        return None
    return x, y


def _tracking_name(tracking_state: Any) -> str:
    if tracking_state is None:
        return "UNKNOWN"
    name = getattr(tracking_state, "name", None)
    if isinstance(name, str) and name:
        return name
    return str(tracking_state)


def gaze_info_to_sample(
    gaze_info: Any,
    geometry: GeometryConfig | None = None,
) -> GazeSample:
    """Map official GazeInfo to GazeSample.

    ``valid`` is True iff status is True, tracking_state is SUCCESS, filtered
    xy is a finite length-2 vector, and both openness values are > 10.
    Invalid samples MUST NOT hold-last: each call returns a fresh sample.
    ``GazeInfo.features`` is never copied.
    """
    config = geometry if geometry is not None else GeometryConfig()
    filtered = _finite_xy(getattr(gaze_info, "filtered_gaze_coordinates", None))
    if filtered is not None:
        x, y = apply_geometry(filtered[0], filtered[1], config)
    else:
        x, y = 0.0, 0.0

    calibrated = _finite_xy(getattr(gaze_info, "calibrated_gaze_coordinates", None))
    if calibrated is not None:
        calibrated_x, calibrated_y = apply_geometry(
            calibrated[0], calibrated[1], config
        )
    else:
        calibrated_x, calibrated_y = None, None

    left = _as_float(getattr(gaze_info, "left_openness", None))
    right = _as_float(getattr(gaze_info, "right_openness", None))
    status = bool(getattr(gaze_info, "status", False))
    tracking_state = _tracking_name(getattr(gaze_info, "tracking_state", None))
    timestamp = getattr(gaze_info, "timestamp", 0) or 0

    valid = (
        status is True
        and tracking_state == SUCCESS_STATE
        and filtered is not None
        and left is not None
        and right is not None
        and left > OPENNESS_THRESHOLD
        and right > OPENNESS_THRESHOLD
    )

    return GazeSample(
        timestamp_ns=int(timestamp),
        valid=valid,
        x=x,
        y=y,
        calibrated_x=calibrated_x,
        calibrated_y=calibrated_y,
        tracking_state=tracking_state,
        left_openness=left,
        right_openness=right,
    )
