"""Mapper interfaces for calibration v2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence, Tuple

from gazekey.features.feature_types import FrameFeatures


@dataclass(frozen=True)
class MapperPrediction:
    x: float
    y: float
    quality: float


@dataclass(frozen=True)
class MapperFitResult:
    success: bool
    message: str
    model: Optional["Mapper"] = None
    rms_px: Optional[float] = None
    # Ridge selection only: all fitted candidates from the same calibration session.
    candidate_reports: Tuple[object, ...] = ()
    # True when mapper is returned despite failing quality gates (typing evaluation mode).
    best_effort: bool = False


class Mapper(Protocol):
    @property
    def mapper_type(self) -> str: ...

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]: ...

    @classmethod
    def fit(
        cls,
        *,
        samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    ) -> MapperFitResult: ...

