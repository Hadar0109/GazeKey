"""Piecewise Y correction interpolated along screen X.

Ridge mappers often tilt rows: bottom-left and bottom-right share target Y but get
different predicted Y because vertical eye features correlate with horizontal gaze.
We fit residual dy = pred_y - target_y at calibration points and subtract dy(px)
via linear interpolation in X (clamped at edges).
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperPrediction


def fit_x_interpolated_y_residuals(
    *,
    model: Any,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (train_x sorted, residual_dy) from inner-model predictions."""
    xs: List[float] = []
    dys: List[float] = []
    for feat, (_tx, ty) in samples:
        pred = model.predict(feat)
        if pred is None:
            continue
        xs.append(float(pred.x))
        dys.append(float(pred.y) - float(ty))
    if not xs:
        return np.zeros(0, dtype=np.float64), np.zeros(0, dtype=np.float64)
    order = np.argsort(np.asarray(xs, dtype=np.float64))
    x_arr = np.asarray(xs, dtype=np.float64)[order]
    dy_arr = np.asarray(dys, dtype=np.float64)[order]
    return x_arr, dy_arr


def interpolate_y_residual(px: float, train_x: np.ndarray, train_dy: np.ndarray) -> float:
    if train_x.size == 0:
        return 0.0
    if train_x.size == 1:
        return float(train_dy[0])
    return float(np.interp(float(px), train_x, train_dy))


class MapperWithLocalYCorrection:
    """Wraps a mapper; subtracts X-interpolated training residual on Y."""

    def __init__(
        self,
        *,
        inner: Any,
        train_x: np.ndarray,
        train_dy: np.ndarray,
    ) -> None:
        self.inner = inner
        self.train_x = np.asarray(train_x, dtype=np.float64).reshape(-1)
        self.train_dy = np.asarray(train_dy, dtype=np.float64).reshape(-1)

    @property
    def mapper_type(self) -> str:
        return str(self.inner.mapper_type)

    @property
    def alpha(self) -> float:
        return float(self.inner.alpha)

    @property
    def clip_bounds(self):
        return self.inner.clip_bounds

    @property
    def train_X(self) -> np.ndarray:
        return self.inner.train_X

    @property
    def train_u_l(self) -> np.ndarray:
        return self.inner.train_u_l

    @property
    def train_u_r(self) -> np.ndarray:
        return self.inner.train_u_r

    @property
    def train_v_l(self) -> np.ndarray:
        return self.inner.train_v_l

    @property
    def train_v_r(self) -> np.ndarray:
        return self.inner.train_v_r

    @property
    def train_Y(self) -> np.ndarray:
        return self.inner.train_Y

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        pred = self.inner.predict(features)
        if pred is None:
            return None
        dy = interpolate_y_residual(float(pred.x), self.train_x, self.train_dy)
        py = float(pred.y) - dy
        return replace(pred, y=py)

    def leave_one_out_detail_px(self) -> List[dict]:
        detail = self.inner.leave_one_out_detail_px()
        out: List[dict] = []
        for d in detail:
            px = float(d["pred_x"])
            py = float(d["pred_y"])
            py -= interpolate_y_residual(px, self.train_x, self.train_dy)
            i = int(d["i"])
            tx = float(self.train_Y[i, 0])
            ty = float(self.train_Y[i, 1])
            err = float(np.hypot(px - tx, py - ty))
            out.append({**d, "pred_y": py, "err": err})
        return out

    def leave_one_out_rms_px(self) -> Optional[float]:
        d = self.leave_one_out_detail_px()
        if not d:
            return None
        errs = [float(x["err"]) for x in d]
        return float(np.sqrt(np.mean(np.array(errs, dtype=np.float64) ** 2)))


def attach_local_y_correction(
    model: Any,
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    verbose: bool = True,
) -> Any:
    """Fit and wrap model with X-interpolated Y residual correction."""
    tx, tdy = fit_x_interpolated_y_residuals(model=model, samples=samples)
    if tx.size < 3:
        if verbose:
            print("[calib2] local Y correction skipped (need >=3 calibration points)")
        return model
    wrapped = MapperWithLocalYCorrection(inner=model, train_x=tx, train_dy=tdy)
    if verbose:
        print(
            f"[calib2] local Y correction: {int(tx.size)} anchors "
            f"dy range [{float(np.min(tdy)):+.1f}, {float(np.max(tdy)):+.1f}] px"
        )
    return wrapped
