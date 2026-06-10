"""Shared mapper types for the active PCA4 ridge path."""

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
