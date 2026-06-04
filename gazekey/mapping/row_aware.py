"""Row-aware gaze mapping prototype.

Idea:
- Vertical: classify into one of a small number of keyboard row regions using avg_v.
- Horizontal: map avg_h -> x, optionally per-row.
- Once a row is chosen, only score keys in that row (or adjacent rows with lower weight).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperFitResult, MapperPrediction


@dataclass(frozen=True)
class RowStats:
    name: str
    mu_v: float
    sigma_v: float
    center_y: float


@dataclass(frozen=True)
class RowAwareFitReport:
    row_names: List[str]
    confusion: List[List[int]]
    x_mae_px: Optional[float]
    row_accuracy: Optional[float]


def _hv(features: FrameFeatures) -> Optional[Tuple[float, float]]:
    if features.avg_h is None or features.avg_v is None:
        return None
    return float(features.avg_h), float(features.avg_v)


def _gauss(v: float, mu: float, sigma: float) -> float:
    s = max(float(sigma), 1e-4)
    z = (v - float(mu)) / s
    return exp(-0.5 * z * z)


@dataclass(frozen=True)
class RowAwareMapper:
    rows: List[RowStats]  # ordered top->bottom semantic
    # Linear x mapping per row: x = a*h + b (in screen pixels)
    x_linear: Dict[str, Tuple[float, float]]
    # Global fallback x mapping
    x_global: Tuple[float, float]
    x_bias: float = 0.0
    report: Optional[RowAwareFitReport] = None

    @property
    def mapper_type(self) -> str:
        return "row_aware_v1"

    def row_scores(self, avg_v: float) -> List[Tuple[str, float]]:
        scores = [(r.name, _gauss(avg_v, r.mu_v, r.sigma_v)) for r in self.rows]
        total = sum(s for _, s in scores)
        if total <= 1e-12:
            return [(n, 0.0) for n, _ in scores]
        return [(n, float(s / total)) for n, s in scores]

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        hv = _hv(features)
        if hv is None:
            return None
        h, v = hv
        rs = self.row_scores(v)
        if not rs:
            return None
        best_name, best_p = max(rs, key=lambda t: t[1])
        a, b = self.x_linear.get(best_name, self.x_global)
        x = a * h + b + float(self.x_bias)
        # Use row center_y as a stable y output for downstream scoring/preview.
        row = next((r for r in self.rows if r.name == best_name), None)
        if row is None:
            return None
        return MapperPrediction(x=float(x), y=float(row.center_y), quality=float(best_p))

    @classmethod
    def fit(
        cls,
        *,
        samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
        row_centers_y: Dict[str, float],
        target_row_for_point: Dict[Tuple[float, float], str],
        row_names_ordered: List[str],
        min_sigma: float = 0.010,
    ) -> MapperFitResult:
        # Collect v values per row from samples.
        by_row_v: Dict[str, List[float]] = {n: [] for n in row_names_ordered}
        by_row_xh: Dict[str, List[Tuple[float, float]]] = {n: [] for n in row_names_ordered}  # (h,x)
        all_xh: List[Tuple[float, float]] = []

        for f, (x, y) in samples:
            hv = _hv(f)
            if hv is None:
                continue
            h, v = hv
            row = target_row_for_point.get((float(x), float(y)))
            if row is None:
                continue
            by_row_v.setdefault(row, []).append(float(v))
            by_row_xh.setdefault(row, []).append((float(h), float(x)))
            all_xh.append((float(h), float(x)))

        # Build RowStats
        rows: List[RowStats] = []
        for n in row_names_ordered:
            vs = by_row_v.get(n, [])
            if not vs:
                mu = 0.5
                sigma = min_sigma
            else:
                a = np.array(vs, dtype=np.float64)
                mu = float(np.mean(a))
                sigma = float(np.std(a))
                sigma = max(sigma, float(min_sigma))
            cy = float(row_centers_y.get(n, 0.0))
            rows.append(RowStats(name=n, mu_v=mu, sigma_v=sigma, center_y=cy))

        # Fit global linear x = a*h + b.
        if len(all_xh) >= 2:
            H = np.array([p[0] for p in all_xh], dtype=np.float64)
            X = np.array([p[1] for p in all_xh], dtype=np.float64)
            A = np.vstack([H, np.ones_like(H)]).T
            a_g, b_g = np.linalg.lstsq(A, X, rcond=None)[0]
            x_global = (float(a_g), float(b_g))
        else:
            x_global = (0.0, 0.0)

        # Fit per-row x linears.
        x_linear: Dict[str, Tuple[float, float]] = {}
        for n, pts in by_row_xh.items():
            if len(pts) < 2:
                continue
            H = np.array([p[0] for p in pts], dtype=np.float64)
            X = np.array([p[1] for p in pts], dtype=np.float64)
            A = np.vstack([H, np.ones_like(H)]).T
            a_r, b_r = np.linalg.lstsq(A, X, rcond=None)[0]
            x_linear[n] = (float(a_r), float(b_r))

        model = cls(rows=rows, x_linear=x_linear, x_global=x_global, x_bias=0.0, report=None)

        # Compute basic validation on calibration points: row accuracy + confusion + x MAE.
        idx_of = {n: i for i, n in enumerate(row_names_ordered)}
        confusion = [[0 for _ in row_names_ordered] for _ in row_names_ordered]
        x_errs: List[float] = []
        correct = 0
        total = 0
        for f, (x, y) in samples:
            hv = _hv(f)
            if hv is None:
                continue
            h, v = hv
            true_row = target_row_for_point.get((float(x), float(y)))
            if true_row is None:
                continue
            scores = model.row_scores(v)
            pred_row = max(scores, key=lambda t: t[1])[0] if scores else None
            if pred_row is not None:
                confusion[idx_of[true_row]][idx_of[pred_row]] += 1
                total += 1
                if pred_row == true_row:
                    correct += 1

            # x error using true row's x mapping
            a, b = model.x_linear.get(true_row, model.x_global)
            x_pred = a * h + b
            x_errs.append(abs(float(x_pred) - float(x)))

        # Compute global x bias correction from signed residuals.
        signed = []
        for f, (x, y) in samples:
            hv = _hv(f)
            if hv is None:
                continue
            h, _v = hv
            true_row = target_row_for_point.get((float(x), float(y)))
            if true_row is None:
                continue
            a, b = model.x_linear.get(true_row, model.x_global)
            x_pred = a * h + b
            signed.append(float(x) - float(x_pred))
        x_bias = float(np.mean(np.array(signed))) if signed else 0.0

        row_acc = float(correct / total) if total else None
        x_mae = float(np.mean(np.array(x_errs))) if x_errs else None

        report = RowAwareFitReport(
            row_names=row_names_ordered,
            confusion=confusion,
            x_mae_px=x_mae,
            row_accuracy=row_acc,
        )
        model = cls(rows=rows, x_linear=x_linear, x_global=x_global, x_bias=x_bias, report=report)

        # No single RMS pixel metric here; return x_mae as rms_px for compatibility.
        return MapperFitResult(success=True, message="Row-aware mapper fit complete.", model=model, rms_px=x_mae)

