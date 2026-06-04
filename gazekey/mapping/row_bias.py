"""Per-row Y bias correction applied after ridge fit."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, List, Optional, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperPrediction


def _nearest_row_index(py: float, row_y_centers: Tuple[float, float, float]) -> int:
    ys = np.array(row_y_centers, dtype=np.float64)
    return int(np.argmin(np.abs(ys - float(py))))


def attach_row_y_bias(
    model: Any,
    *,
    row_y_centers: Tuple[float, float, float],
    row_y_bias: Tuple[float, float, float],
) -> "MapperWithRowBias":
    return MapperWithRowBias(
        inner=model,
        row_y_centers=row_y_centers,
        row_y_bias=row_y_bias,
    )


class MapperWithRowBias:
    """Wraps a ridge mapper and subtracts a row-specific Y bias at predict time."""

    def __init__(
        self,
        *,
        inner: Any,
        row_y_centers: Tuple[float, float, float],
        row_y_bias: Tuple[float, float, float],
    ) -> None:
        self.inner = inner
        self.row_y_centers = row_y_centers
        self.row_y_bias = row_y_bias

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
        ri = _nearest_row_index(float(pred.y), self.row_y_centers)
        dy = float(self.row_y_bias[ri])
        py = float(pred.y) - dy
        return replace(pred, y=py)

    def leave_one_out_detail_px(self) -> List[dict]:
        detail = self.inner.leave_one_out_detail_px()
        out: List[dict] = []
        for d in detail:
            py = float(d["pred_y"])
            ri = _nearest_row_index(py, self.row_y_centers)
            py -= float(self.row_y_bias[ri])
            px = float(d["pred_x"])
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
