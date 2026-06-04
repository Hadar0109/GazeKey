"""2D IDW mapper for gaze ratios (avg_h/avg_v) -> screen coords.

This is a deliberately minimal, robust baseline:
- uses only avg_h/avg_v (2D) to avoid high-D instability
- trains on one representative point per calibration target (window-mean)
- provides simple leave-one-out validation helpers
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperFitResult, MapperPrediction


def _hv(features: FrameFeatures) -> Optional[Tuple[float, float]]:
    if features.avg_h is None or features.avg_v is None:
        return None
    return float(features.avg_h), float(features.avg_v)


@dataclass(frozen=True)
class IDWRatioMapper:
    """IDW interpolation in 2D ratio space."""

    ratio_points: List[Tuple[float, float]]  # (avg_h, avg_v) per target
    screen_points: List[Tuple[float, float]]  # (x, y) per target
    ratio_scale: Tuple[float, float]  # (scale_h, scale_v) for normalization
    power: float = 2.0
    eps: float = 1e-6

    @property
    def mapper_type(self) -> str:
        return "idw_ratio_v1"

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        hv = _hv(features)
        if hv is None:
            return None

        sh, sv = self.ratio_scale
        sh = max(float(sh), 1e-3)
        sv = max(float(sv), 1e-3)
        v = np.array([hv[0] / sh, hv[1] / sv], dtype=np.float64)

        weights: List[float] = []
        for i, (h, vv) in enumerate(self.ratio_points):
            m = np.array([h / sh, vv / sv], dtype=np.float64)
            d = float(np.linalg.norm(v - m))
            if d < self.eps:
                x, y = self.screen_points[i]
                return MapperPrediction(x=float(x), y=float(y), quality=1.0)
            weights.append(1.0 / (d**self.power))

        wsum = float(sum(weights))
        if wsum <= 0.0:
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
        require_unique_points: bool = True,
    ) -> MapperFitResult:
        pts_by_screen: Dict[Tuple[float, float], List[Tuple[float, float]]] = {}
        for f, (x, y) in samples:
            hv = _hv(f)
            if hv is None:
                continue
            pts_by_screen.setdefault((float(x), float(y)), []).append(hv)

        if require_unique_points and len(pts_by_screen) < 5:
            return MapperFitResult(success=False, message="Need at least 5 unique targets with avg_h/avg_v.")

        screen_points: List[Tuple[float, float]] = []
        ratio_points: List[Tuple[float, float]] = []
        for sp, hvs in pts_by_screen.items():
            hs = np.array([p[0] for p in hvs], dtype=np.float64)
            vs = np.array([p[1] for p in hvs], dtype=np.float64)
            ratio_points.append((float(np.mean(hs)), float(np.mean(vs))))
            screen_points.append((float(sp[0]), float(sp[1])))

        H = np.array([p[0] for p in ratio_points], dtype=np.float64)
        V = np.array([p[1] for p in ratio_points], dtype=np.float64)
        sh = float(np.std(H))
        sv = float(np.std(V))
        sh = max(sh, 1e-3)
        sv = max(sv, 1e-3)

        model = cls(
            ratio_points=ratio_points,
            screen_points=screen_points,
            ratio_scale=(sh, sv),
        )

        errs = []
        for f, (x, y) in samples:
            pred = model.predict(f)
            if pred is None:
                continue
            errs.append(float(np.hypot(pred.x - float(x), pred.y - float(y))))
        rms = float(np.sqrt(np.mean(np.array(errs) ** 2))) if errs else None

        return MapperFitResult(success=True, message="Mapper fit complete.", model=model, rms_px=rms)

    def leave_one_out_errors_px(self) -> List[float]:
        """Return per-target LOOCV error (target held out of fit)."""
        if len(self.screen_points) <= 1:
            return []

        errs: List[float] = []
        for i in range(len(self.screen_points)):
            rp = [p for j, p in enumerate(self.ratio_points) if j != i]
            sp = [p for j, p in enumerate(self.screen_points) if j != i]
            H = np.array([p[0] for p in rp], dtype=np.float64)
            V = np.array([p[1] for p in rp], dtype=np.float64)
            sh = float(np.std(H)) if H.size else 1e-3
            sv = float(np.std(V)) if V.size else 1e-3
            tmp = IDWRatioMapper(ratio_points=rp, screen_points=sp, ratio_scale=(max(sh, 1e-3), max(sv, 1e-3)))
            f = FrameFeatures(
                timestamp_ms=0,
                face_detected=True,
                blink=False,
                confidence=1.0,
                Lh=None,
                Lv=None,
                Rh=None,
                Rv=None,
                avg_h=self.ratio_points[i][0],
                avg_v=self.ratio_points[i][1],
                eye_box_w=None,
                eye_box_h=None,
                face_x=None,
                face_y=None,
            )
            pred = tmp.predict(f)
            if pred is None:
                continue
            x, y = self.screen_points[i]
            errs.append(float(np.hypot(pred.x - x, pred.y - y)))
        return errs

    def leave_one_out_rms_px(self) -> Optional[float]:
        errs = self.leave_one_out_errors_px()
        if not errs:
            return None
        a = np.array(errs, dtype=np.float64)
        return float(np.sqrt(np.mean(a**2)))

