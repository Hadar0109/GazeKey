"""Active MVP mapping API: PCA4 ridge calibration and predict (T054).

Dormant mapper variants (IDW, row_aware) live under `archive/mapping_variants/`
for offline tests; poly12 helpers remain in `gazekey.mapping.poly_features`.
"""

from gazekey.mapping.base import Mapper, MapperFitResult, MapperPrediction
from gazekey.mapping.ridge import (
    FROZEN_ACTIVE_MAPPER,
    Pca4BaselineMapper,
    RidgeCalibrationMapper,
    RidgeRegressionMapper,
    fit_calibration_mapper,
)
from gazekey.mapping.typing_candidate import ACTIVE_MAPPER, TYPING_CANDIDATE_ID

__all__ = [
    "ACTIVE_MAPPER",
    "FROZEN_ACTIVE_MAPPER",
    "Mapper",
    "MapperFitResult",
    "MapperPrediction",
    "Pca4BaselineMapper",
    "RidgeCalibrationMapper",
    "RidgeRegressionMapper",
    "TYPING_CANDIDATE_ID",
    "fit_calibration_mapper",
]
