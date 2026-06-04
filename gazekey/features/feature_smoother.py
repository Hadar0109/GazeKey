"""Short EMA on PCA eye features so runtime matches calibration window means."""

from __future__ import annotations

from dataclasses import replace
from typing import Optional

from gazekey.features.feature_types import FrameFeatures


class PcaFeatureSmoother:
    """
    Smooth u/v per eye before ridge predict.

    Calibration stores IQR-filtered means over ~1s fixation; per-frame features
  jitter more than those means. A light EMA narrows that gap without heavy lag.
    """

    def __init__(self, alpha: float = 0.28) -> None:
        self._alpha = float(alpha)
        self._u_l: Optional[float] = None
        self._v_l: Optional[float] = None
        self._u_r: Optional[float] = None
        self._v_r: Optional[float] = None

    def reset(self) -> None:
        self._u_l = self._v_l = self._u_r = self._v_r = None

    def _ema(self, prev: Optional[float], val: float) -> float:
        if prev is None:
            return float(val)
        a = self._alpha
        return float(a * val + (1.0 - a) * prev)

    def smooth(self, features: FrameFeatures) -> FrameFeatures:
        if (
            features.pca_uL is None
            or features.pca_vL is None
            or features.pca_uR is None
            or features.pca_vR is None
        ):
            return features

        u_l = self._ema(self._u_l, float(features.pca_uL))
        v_l = self._ema(self._v_l, float(features.pca_vL))
        u_r = self._ema(self._u_r, float(features.pca_uR))
        v_r = self._ema(self._v_r, float(features.pca_vR))
        self._u_l, self._v_l, self._u_r, self._v_r = u_l, v_l, u_r, v_r

        Lh = float(max(0.0, min(1.0, 0.5 + u_l)))
        Lv = float(max(0.0, min(1.0, 0.5 + v_l)))
        Rh = float(max(0.0, min(1.0, 0.5 + u_r)))
        Rv = float(max(0.0, min(1.0, 0.5 + v_r)))
        avg_h = (Lh + Rh) / 2.0
        avg_v = (Lv + Rv) / 2.0

        return replace(
            features,
            pca_uL=u_l,
            pca_vL=v_l,
            pca_uR=u_r,
            pca_vR=v_r,
            Lh=Lh,
            Lv=Lv,
            Rh=Rh,
            Rv=Rv,
            avg_h=avg_h,
            avg_v=avg_v,
        )
