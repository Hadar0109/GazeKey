"""Thin GazeFollower adapter. The only new production gaze package.

Must not import gazekey.features, gazekey.mapping, gazekey.calibration,
or gazekey.tracking.
"""

from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.geometry import GeometryConfig, GeometryStopError

__all__ = [
    "GazeSample",
    "GeometryConfig",
    "GeometryStopError",
]
