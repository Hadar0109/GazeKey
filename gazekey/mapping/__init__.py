"""Mapping gaze features to typing-region coordinates (calibration v2)."""

from gazekey.mapping.base import Mapper, MapperFitResult, MapperPrediction
from gazekey.mapping.idw_local import IDWFeatureMapper
from gazekey.mapping.idw_ratio import IDWRatioMapper
from gazekey.mapping.ridge import (
    RidgeCalibrationMapper,
    RidgeRegressionMapper,
    fit_calibration_mapper,
)
from gazekey.mapping.row_aware import RowAwareMapper

__all__ = [
    "Mapper",
    "MapperFitResult",
    "MapperPrediction",
    "IDWFeatureMapper",
    "IDWRatioMapper",
    "RidgeRegressionMapper",
    "RidgeCalibrationMapper",
    "fit_calibration_mapper",
    "RowAwareMapper",
]

