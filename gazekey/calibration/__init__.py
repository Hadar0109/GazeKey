"""Calibration package for gaze-to-screen mapping."""

from gazekey.calibration.affine_mapper import AffineGazeMapper
from gazekey.calibration.gaze_mapper import (
    InterpolationGazeMapper,
    fit_gaze_mapper,
    GazeMapper,
)
from gazekey.calibration.calibration_session import (
    CalibrationResult,
    CalibrationSession,
    COLLECT_MS,
    PREPARE_MS,
    compute_calibration_targets,
)
from gazekey.calibration.calibration_store import CalibrationStore, StoredCalibration
from gazekey.calibration.gaze_features import average_iris_pixels, iris_span_across_points
from gazekey.calibration.tracking_bridge import TrackingBridge

__all__ = [
    "AffineGazeMapper",
    "InterpolationGazeMapper",
    "GazeMapper",
    "fit_gaze_mapper",
    "CalibrationResult",
    "CalibrationSession",
    "CalibrationStore",
    "StoredCalibration",
    "TrackingBridge",
    "average_iris_pixels",
    "iris_span_across_points",
    "compute_calibration_targets",
    "COLLECT_MS",
    "PREPARE_MS",
]
