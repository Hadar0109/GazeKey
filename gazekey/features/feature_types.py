"""Core datatypes for gaze feature extraction (Phase 0 minimal set)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FrameFeatures:
    timestamp_ms: int
    face_detected: bool
    blink: bool
    confidence: float

    # Per-eye ratios (None if missing)
    Lh: Optional[float]
    Lv: Optional[float]
    Rh: Optional[float]
    Rv: Optional[float]

    # Averages (None if neither eye available)
    avg_h: Optional[float]
    avg_v: Optional[float]

    # Eye box size proxy in normalized coordinates (0..1)
    eye_box_w: Optional[float]
    eye_box_h: Optional[float]

    # Face center proxy in normalized coordinates (0..1)
    face_x: Optional[float]
    face_y: Optional[float]

    # PCA eye-local coordinates (normalized, roughly in [-1..1], may exceed).
    # These are intended for geometric mappers (e.g. RidgeRegression) and should
    # not be assumed to lie within [0..1].
    pca_uL: Optional[float] = None
    pca_vL: Optional[float] = None
    pca_uR: Optional[float] = None
    pca_vR: Optional[float] = None

