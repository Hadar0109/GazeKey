"""Multi-feature IDW mapper (v1) for keyboard-local calibration.

Design decision:
- Keep the feature vector small and reliable initially:
  Lh,Lv,Rh,Rv,avg_h,avg_v,eye_box_w,eye_box_h,face_x,face_y
- Fit stores one feature mean per target, then predicts by IDW over feature space.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import Mapper, MapperFitResult, MapperPrediction


def _vec(f: FrameFeatures) -> Optional[np.ndarray]:
    vals = [
        f.Lh,
        f.Lv,
        f.Rh,
        f.Rv,
        f.avg_h,
        f.avg_v,
        f.eye_box_w,
        f.eye_box_h,
        f.face_x,
        f.face_y,
    ]
    if any(v is None for v in vals):
        return None
    return np.array([float(v) for v in vals], dtype=np.float64)


@dataclass(frozen=True)
class IDWFeatureMapper:
    feature_means: List[np.ndarray]
    screen_points: List[Tuple[float, float]]
    feature_scale: np.ndarray
    power: float = 2.0
    eps: float = 1e-6

    @property
    def mapper_type(self) -> str:
        return "idw_feature_v1"

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        v = _vec(features)
        if v is None:
            return None
        v = v / self.feature_scale

        weights: List[float] = []
        for i, m in enumerate(self.feature_means):
            d = float(np.linalg.norm(v - m))
            if d < self.eps:
                x, y = self.screen_points[i]
                return MapperPrediction(x=float(x), y=float(y), quality=1.0)
            weights.append(1.0 / (d**self.power))

        wsum = float(sum(weights))
        if wsum <= 0:
            return None
        x = sum(w * self.screen_points[i][0] for i, w in enumerate(weights)) / wsum
        y = sum(w * self.screen_points[i][1] for i, w in enumerate(weights)) / wsum
        quality = float(max(weights) / (wsum + 1e-9))
        return MapperPrediction(x=float(x), y=float(y), quality=quality)

    @classmethod
    def fit(
        cls,
        *,
        samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    ) -> MapperFitResult:
        if len(samples) < 5:
            return MapperFitResult(success=False, message="Need at least 5 samples.")

        feats: List[np.ndarray] = []
        pts: List[Tuple[float, float]] = []
        for f, p in samples:
            v = _vec(f)
            if v is None:
                continue
            feats.append(v)
            pts.append((float(p[0]), float(p[1])))

        if len(feats) < 5:
            return MapperFitResult(success=False, message="Too few complete feature vectors.")

        F = np.stack(feats, axis=0)
        # Scale per feature by robust std (avoid tiny scales).
        scale = np.std(F, axis=0)
        scale = np.maximum(scale, 1e-3)
        F_scaled = F / scale

        # Collapse samples per unique point (target): mean in feature space.
        # Caller should ideally pass one mean per target; we still handle duplicates.
        groups: dict[Tuple[float, float], List[np.ndarray]] = {}
        for v, p in zip(F_scaled, pts):
            groups.setdefault((p[0], p[1]), []).append(v)

        screen_points = list(groups.keys())
        feature_means = [np.mean(np.stack(groups[p], axis=0), axis=0) for p in screen_points]

        model = cls(feature_means=feature_means, screen_points=screen_points, feature_scale=scale)
        # Compute RMS on training pairs.
        errs = []
        for f, (x, y) in samples:
            pred = model.predict(f)
            if pred is None:
                continue
            errs.append(float(np.hypot(pred.x - x, pred.y - y)))
        rms = float(np.sqrt(np.mean(np.array(errs) ** 2))) if errs else None

        return MapperFitResult(success=True, message="Mapper fit complete.", model=model, rms_px=rms)

