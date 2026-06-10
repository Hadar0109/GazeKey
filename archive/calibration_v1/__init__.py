"""v1 calibration package archived from gazekey.calibration (T056).

Import example (repo root on PYTHONPATH):

    from archive.calibration_v1 import CalibrationSession, fit_gaze_mapper
"""

from archive.calibration_v1.affine_mapper import AffineGazeMapper
from archive.calibration_v1.calibration_session import (
    COLLECT_MS,
    PREPARE_MS,
    CalibrationResult,
    CalibrationSession,
    compute_calibration_targets,
)
from archive.calibration_v1.calibration_store import CalibrationStore, StoredCalibration
from archive.calibration_v1.gaze_features import (
    average_iris_pixels,
    gaze_ratios,
    iris_span_across_points,
)
from archive.calibration_v1.gaze_mapper import (
    GazeMapper,
    InterpolationGazeMapper,
    fit_gaze_mapper,
)

__all__ = [
    "AffineGazeMapper",
    "CalibrationResult",
    "CalibrationSession",
    "CalibrationStore",
    "GazeMapper",
    "InterpolationGazeMapper",
    "StoredCalibration",
    "average_iris_pixels",
    "COLLECT_MS",
    "PREPARE_MS",
    "compute_calibration_targets",
    "fit_gaze_mapper",
    "gaze_ratios",
    "iris_span_across_points",
]
