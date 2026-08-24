"""Backend-agnostic GazeSample handoff (data-model.md / contracts/gaze-sample.md)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GazeSample:
    """Official GazeFollower → GazeKey pointing record.

    Pointing ``x,y`` are filtered screen coordinates after the documented
    identity/origin/DPR transform only. ``features``, ``raw_gaze_coordinates``,
    ``event``, and invented confidence are not part of this contract.
    """

    timestamp_ns: int
    valid: bool
    x: float
    y: float
    calibrated_x: float | None
    calibrated_y: float | None
    tracking_state: str
    left_openness: float | None
    right_openness: float | None
