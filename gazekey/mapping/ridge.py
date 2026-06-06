"""Ridge mappers for calibration v2 with LOOCV-based model selection.

Candidates:
- pca4_baseline: screen X from [uL,uR], screen Y from raw [vL,vR]
- pca4_decoupled_split: residualize v on [1,uL,uR], then split ridge X/Y
- poly12_ridge_split: screen X from 12D polynomial features; screen Y from either
  full 12D or decoupled [vL_res,vR_res] (chosen by LOOCV)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.features.poly_features import extract_uv_arrays, poly12_from_uv
from gazekey.features.vertical_decouple import (
    apply_v_residualizers,
    apply_v_residualizers_batch,
    coupling_report,
    fit_v_residualizers,
)
from gazekey.calibration2.region_quality import (
    assess_region_gates,
    compute_row_y_residuals,
    region_gate_limits,
)
from gazekey.mapping.base import MapperFitResult, MapperPrediction
from gazekey.mapping.local_y_correction import MapperWithLocalYCorrection, attach_local_y_correction
from gazekey.mapping.row_bias import MapperWithRowBias, attach_row_y_bias

if False:  # TYPE_CHECKING
    from gazekey.calibration2.targets import CalibrationTarget

ALPHA_GRID: Tuple[float, ...] = (1.0, 10.0, 50.0, 100.0, 200.0, 400.0)
# Among alphas with LOOCV RMS within this band of the grid minimum, pick the largest alpha.
ALPHA_SELECT_LOOCV_TOL_PX = 5.0
LOOCV_TIE_TOL_PX = 2.0
# Active runtime freeze: calibration always fits/selects this mapper only.
FROZEN_ACTIVE_MAPPER = "pca4_baseline"
MAPPER_SIMPLICITY: Tuple[str, ...] = (
    "pca4_baseline",
    "pca4_decoupled_split",
    "poly12_ridge",
    "poly12_ridge_split",
)


def _raw_uv(f: FrameFeatures) -> Optional[Tuple[float, float, float, float]]:
    u_l, v_l, u_r, v_r = f.pca_uL, f.pca_vL, f.pca_uR, f.pca_vR
    if u_l is None or v_l is None or u_r is None or v_r is None:
        return None
    return float(u_l), float(v_l), float(u_r), float(v_r)


def _fit_ridge_1d(
    X: np.ndarray,
    y: np.ndarray,
    *,
    alpha: float,
) -> Tuple[np.ndarray, float, np.ndarray, np.ndarray]:
    Y = np.asarray(y, dtype=np.float64).reshape(-1, 1)
    W, intercept, mu, sigma = _fit_ridge(np.asarray(X, dtype=np.float64), Y, alpha=alpha)
    return W.reshape(-1), float(intercept[0]), mu, sigma


def _predict_ridge_1d(
    x_raw: np.ndarray,
    *,
    w: np.ndarray,
    intercept: float,
    mu: np.ndarray,
    sigma: np.ndarray,
) -> float:
    xs = (np.asarray(x_raw, dtype=np.float64) - mu) / sigma
    return float(xs @ w + intercept)


def _predict_ridge_2d(
    x_raw: np.ndarray,
    *,
    w: np.ndarray,
    intercept: np.ndarray,
    mu: np.ndarray,
    sigma: np.ndarray,
) -> Tuple[float, float]:
    xs = (np.asarray(x_raw, dtype=np.float64) - mu) / sigma
    out = xs @ w + np.asarray(intercept, dtype=np.float64).reshape(-1)
    return float(out[0]), float(out[1])


def _fit_ridge(
    X: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    mu = np.mean(X, axis=0)
    sigma = np.maximum(np.std(X, axis=0), 1e-3)
    xs = (X - mu) / sigma
    mx = np.mean(xs, axis=0)
    my = np.mean(Y, axis=0)
    xc = xs - mx
    yc = Y - my
    d = X.shape[1]
    a = float(max(0.0, alpha))
    A = (xc.T @ xc) + (a * np.eye(d, dtype=np.float64))
    B = xc.T @ yc
    W = np.linalg.solve(A, B)
    intercept = my - (mx @ W)
    return W, intercept, mu, sigma


def _bounds_from_screen_rect(
    screen_rect: Optional[Tuple[float, float, float, float]],
) -> Optional[Tuple[float, float, float, float]]:
    if screen_rect is None:
        return None
    x, y, w, h = screen_rect
    return float(x), float(y), float(x + w), float(y + h)


def _clip_xy(
    px: float,
    py: float,
    bounds: Optional[Tuple[float, float, float, float]],
) -> Tuple[float, float]:
    if bounds is None:
        return px, py
    x0, y0, x1, y1 = bounds
    return float(max(x0, min(x1, px))), float(max(y0, min(y1, py)))


def _auto_alpha(
    loocv_fn,
    *,
    min_alpha: float = 1.0,
    candidate_label: str = "",
) -> float:
    """Pick ridge alpha: prefer stronger regularization when LOOCV is nearly tied."""
    label = str(candidate_label).strip() or "ridge"
    try:
        scored = [(float(loocv_fn(a)), float(a)) for a in ALPHA_GRID]
        scored = [t for t in scored if np.isfinite(t[0])]
        if scored:
            best_loocv = min(t[0] for t in scored)
            tol = float(ALPHA_SELECT_LOOCV_TOL_PX)
            near = [t for t in scored if t[0] <= best_loocv + tol]
            chosen_alpha = max(t[1] for t in near)
            chosen_loocv = min(t[0] for t in near if t[1] == chosen_alpha)
            chosen_alpha = float(max(float(min_alpha), chosen_alpha))
            parts = " ".join(f"a={a:.0f}:{rms:.1f}px" for rms, a in sorted(scored, key=lambda t: t[1]))
            print(
                f"[calib2] alpha grid {label}: {parts} "
                f"-> selected {chosen_alpha:.1f} "
                f"(best_loocv={best_loocv:.1f}px tol={tol:.1f}px "
                f"chosen_loocv={chosen_loocv:.1f}px)"
            )
            return chosen_alpha
    except Exception as e:
        print(f"[calib2] alpha grid {label}: failed ({e}), using min_alpha={min_alpha:.1f}")
    return float(min_alpha)


def _train_rms_px(model: "RidgeCalibrationMapper", samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]]) -> Optional[float]:
    errs: List[float] = []
    for f, (tx, ty) in samples:
        pred = model.predict(f)
        if pred is None:
            continue
        errs.append(float(np.hypot(pred.x - tx, pred.y - ty)))
    if not errs:
        return None
    return float(np.sqrt(np.mean(np.array(errs, dtype=np.float64) ** 2)))


@dataclass(frozen=True)
class MapperCandidateReport:
    mapper_type: str
    success: bool
    message: str
    train_rms_px: Optional[float]
    loocv_rms_px: Optional[float]
    worst_loocv_px: Optional[float]
    max_train_px: Optional[float]
    alpha: Optional[float]
    loocv_detail: Tuple[dict, ...] = ()
    model: Optional["RidgeCalibrationMapper"] = None
    quality_gates_passed: Optional[bool] = None
    quality_gate_reasons: Tuple[str, ...] = ()
    region_train_wrong: int = 0
    region_loocv_wrong: int = 0
    worst_train_label: str = ""
    worst_loocv_label: str = ""


def _loocv_from_detail(detail: Sequence[dict]) -> Tuple[Optional[float], Optional[float]]:
    if not detail:
        return None, None
    errs = [float(d["err"]) for d in detail]
    rms = float(np.sqrt(np.mean(np.array(errs, dtype=np.float64) ** 2)))
    return rms, float(max(errs))


def _max_train_from_samples(
    model: "RidgeCalibrationMapper",
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
) -> Optional[float]:
    errs: List[float] = []
    for f, (tx, ty) in samples:
        pred = model.predict(f)
        if pred is None:
            continue
        errs.append(float(np.hypot(pred.x - tx, pred.y - ty)))
    return max(errs) if errs else None


# ---------------------------------------------------------------------------
# LOOCV builders (refit decoupler inside each fold)
# ---------------------------------------------------------------------------


def _loocv_pca4_baseline(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> List[dict]:
    n = int(Y.shape[0])
    detail: List[dict] = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        x_tr = np.column_stack([u_l[mask], u_r[mask]])
        y_tr = np.column_stack([v_l[mask], v_r[mask]])
        wx, bx, mux, sigx = _fit_ridge_1d(x_tr, Y[mask, 0], alpha=alpha)
        wy, by, muy, sigy = _fit_ridge_1d(y_tr, Y[mask, 1], alpha=alpha)
        px = _predict_ridge_1d(np.array([u_l[i], u_r[i]]), w=wx, intercept=bx, mu=mux, sigma=sigx)
        py = _predict_ridge_1d(np.array([v_l[i], v_r[i]]), w=wy, intercept=by, mu=muy, sigma=sigy)
        px, py = _clip_xy(px, py, clip_bounds)
        detail.append({"i": i, "pred_x": px, "pred_y": py, "err": float(np.hypot(px - Y[i, 0], py - Y[i, 1]))})
    return detail


def _loocv_pca4_decoupled(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> List[dict]:
    n = int(Y.shape[0])
    detail: List[dict] = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        bl, br = fit_v_residualizers(u_l[mask], u_r[mask], v_l[mask], v_r[mask])
        vl_r, vr_r = apply_v_residualizers_batch(
            u_l[mask], u_r[mask], v_l[mask], v_r[mask], beta_l=bl, beta_r=br
        )
        x_tr = np.column_stack([u_l[mask], u_r[mask]])
        y_tr = np.column_stack([vl_r, vr_r])
        wx, bx, mux, sigx = _fit_ridge_1d(x_tr, Y[mask, 0], alpha=alpha)
        wy, by, muy, sigy = _fit_ridge_1d(y_tr, Y[mask, 1], alpha=alpha)
        vl_i, vr_i = apply_v_residualizers(
            float(u_l[i]), float(u_r[i]), float(v_l[i]), float(v_r[i]), beta_l=bl, beta_r=br
        )
        px = _predict_ridge_1d(np.array([u_l[i], u_r[i]]), w=wx, intercept=bx, mu=mux, sigma=sigx)
        py = _predict_ridge_1d(np.array([vl_i, vr_i]), w=wy, intercept=by, mu=muy, sigma=sigy)
        px, py = _clip_xy(px, py, clip_bounds)
        detail.append({"i": i, "pred_x": px, "pred_y": py, "err": float(np.hypot(px - Y[i, 0], py - Y[i, 1]))})
    return detail


def _loocv_poly12_joint(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> List[dict]:
    """Joint ridge: both screen axes from the same 12D polynomial features."""
    n = int(Y.shape[0])
    poly = poly12_from_uv(u_l, v_l, u_r, v_r)
    detail: List[dict] = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        w, intercept, mu, sigma = _fit_ridge(poly[mask], Y[mask], alpha=alpha)
        px, py = _predict_ridge_2d(poly[i], w=w, intercept=intercept, mu=mu, sigma=sigma)
        px, py = _clip_xy(px, py, clip_bounds)
        detail.append({"i": i, "pred_x": px, "pred_y": py, "err": float(np.hypot(px - Y[i, 0], py - Y[i, 1]))})
    return detail


def _loocv_poly12_split(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    y_mode: str,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> List[dict]:
    n = int(Y.shape[0])
    poly = poly12_from_uv(u_l, v_l, u_r, v_r)
    detail: List[dict] = []
    for i in range(n):
        mask = np.ones(n, dtype=bool)
        mask[i] = False
        wx, bx, mux, sigx = _fit_ridge_1d(poly[mask], Y[mask, 0], alpha=alpha)
        if y_mode == "poly12":
            wy, by, muy, sigy = _fit_ridge_1d(poly[mask], Y[mask, 1], alpha=alpha)
            x_y = poly[i]
        else:
            bl, br = fit_v_residualizers(u_l[mask], u_r[mask], v_l[mask], v_r[mask])
            vl_r, vr_r = apply_v_residualizers_batch(
                u_l[mask], u_r[mask], v_l[mask], v_r[mask], beta_l=bl, beta_r=br
            )
            y_tr = np.column_stack([vl_r, vr_r])
            wy, by, muy, sigy = _fit_ridge_1d(y_tr, Y[mask, 1], alpha=alpha)
            vl_i, vr_i = apply_v_residualizers(
                float(u_l[i]), float(u_r[i]), float(v_l[i]), float(v_r[i]), beta_l=bl, beta_r=br
            )
            x_y = np.array([vl_i, vr_i], dtype=np.float64)
        px = _predict_ridge_1d(poly[i], w=wx, intercept=bx, mu=mux, sigma=sigx)
        py = _predict_ridge_1d(x_y, w=wy, intercept=by, mu=muy, sigma=sigy)
        px, py = _clip_xy(px, py, clip_bounds)
        detail.append({"i": i, "pred_x": px, "pred_y": py, "err": float(np.hypot(px - Y[i, 0], py - Y[i, 1]))})
    return detail


def _loocv_rms_from_detail(detail: Sequence[dict]) -> float:
    errs = [float(d["err"]) for d in detail]
    return float(np.sqrt(np.mean(np.array(errs, dtype=np.float64) ** 2)))


def _pick_poly12_y_mode(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> str:
    d_poly = _loocv_poly12_split(u_l, u_r, v_l, v_r, Y, alpha=alpha, y_mode="poly12", clip_bounds=clip_bounds)
    d_dec = _loocv_poly12_split(
        u_l, u_r, v_l, v_r, Y, alpha=alpha, y_mode="decoupled_v", clip_bounds=clip_bounds
    )
    r_poly = _loocv_rms_from_detail(d_poly)
    r_dec = _loocv_rms_from_detail(d_dec)
    if r_dec < r_poly - 1e-6:
        print(f"[calib2] poly12 Y-mode: decoupled_v LOOCV={r_dec:.1f}px beats poly12={r_poly:.1f}px")
        return "decoupled_v"
    if r_poly < r_dec - 1e-6:
        print(f"[calib2] poly12 Y-mode: poly12 LOOCV={r_poly:.1f}px beats decoupled_v={r_dec:.1f}px")
        return "poly12"
    print(f"[calib2] poly12 Y-mode: tie ({r_poly:.1f}px) — using poly12")
    return "poly12"


# ---------------------------------------------------------------------------
# Mapper implementations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Pca4BaselineMapper:
    w_x: np.ndarray
    b_x: float
    mu_x: np.ndarray
    sigma_x: np.ndarray
    w_y: np.ndarray
    b_y: float
    mu_y: np.ndarray
    sigma_y: np.ndarray
    alpha: float
    train_u_l: np.ndarray
    train_u_r: np.ndarray
    train_v_l: np.ndarray
    train_v_r: np.ndarray
    train_Y: np.ndarray
    clip_bounds: Optional[Tuple[float, float, float, float]] = None

    @property
    def mapper_type(self) -> str:
        return "pca4_baseline"

    @property
    def train_X(self) -> np.ndarray:
        return np.column_stack([self.train_u_l, self.train_u_r, self.train_v_l, self.train_v_r])

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        raw = _raw_uv(features)
        if raw is None:
            return None
        u_l, v_l, u_r, v_r = raw
        px = _predict_ridge_1d(
            np.array([u_l, u_r]), w=self.w_x, intercept=self.b_x, mu=self.mu_x, sigma=self.sigma_x
        )
        py = _predict_ridge_1d(
            np.array([v_l, v_r]), w=self.w_y, intercept=self.b_y, mu=self.mu_y, sigma=self.sigma_y
        )
        px, py = _clip_xy(px, py, self.clip_bounds)
        return MapperPrediction(x=px, y=py, quality=1.0)

    def leave_one_out_detail_px(self) -> List[dict]:
        return _loocv_pca4_baseline(
            self.train_u_l,
            self.train_u_r,
            self.train_v_l,
            self.train_v_r,
            self.train_Y,
            alpha=float(self.alpha),
            clip_bounds=self.clip_bounds,
        )

    def leave_one_out_rms_px(self) -> Optional[float]:
        d = self.leave_one_out_detail_px()
        rms, _ = _loocv_from_detail(d)
        return rms


@dataclass(frozen=True)
class Pca4DecoupledSplitMapper:
    w_x: np.ndarray
    b_x: float
    mu_x: np.ndarray
    sigma_x: np.ndarray
    w_y: np.ndarray
    b_y: float
    mu_y: np.ndarray
    sigma_y: np.ndarray
    beta_v_l: np.ndarray
    beta_v_r: np.ndarray
    alpha: float
    train_u_l: np.ndarray
    train_u_r: np.ndarray
    train_v_l: np.ndarray
    train_v_r: np.ndarray
    train_Y: np.ndarray
    clip_bounds: Optional[Tuple[float, float, float, float]] = None

    @property
    def mapper_type(self) -> str:
        return "pca4_decoupled_split"

    @property
    def train_X(self) -> np.ndarray:
        return np.column_stack([self.train_u_l, self.train_u_r, self.train_v_l, self.train_v_r])

    def _decoupled_v(self, u_l: float, u_r: float, v_l: float, v_r: float) -> Tuple[float, float]:
        return apply_v_residualizers(u_l, u_r, v_l, v_r, beta_l=self.beta_v_l, beta_r=self.beta_v_r)

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        raw = _raw_uv(features)
        if raw is None:
            return None
        u_l, v_l, u_r, v_r = raw
        vl_r, vr_r = self._decoupled_v(u_l, u_r, v_l, v_r)
        px = _predict_ridge_1d(
            np.array([u_l, u_r]), w=self.w_x, intercept=self.b_x, mu=self.mu_x, sigma=self.sigma_x
        )
        py = _predict_ridge_1d(
            np.array([vl_r, vr_r]), w=self.w_y, intercept=self.b_y, mu=self.mu_y, sigma=self.sigma_y
        )
        px, py = _clip_xy(px, py, self.clip_bounds)
        return MapperPrediction(x=px, y=py, quality=1.0)

    def leave_one_out_detail_px(self) -> List[dict]:
        return _loocv_pca4_decoupled(
            self.train_u_l,
            self.train_u_r,
            self.train_v_l,
            self.train_v_r,
            self.train_Y,
            alpha=float(self.alpha),
            clip_bounds=self.clip_bounds,
        )

    def leave_one_out_rms_px(self) -> Optional[float]:
        d = self.leave_one_out_detail_px()
        rms, _ = _loocv_from_detail(d)
        return rms


@dataclass(frozen=True)
class Poly12RidgeMapper:
    """Single joint ridge model: (screen_x, screen_y) = f(poly12(u,v))."""

    w: np.ndarray
    intercept: np.ndarray
    mu: np.ndarray
    sigma: np.ndarray
    alpha: float
    train_u_l: np.ndarray
    train_u_r: np.ndarray
    train_v_l: np.ndarray
    train_v_r: np.ndarray
    train_Y: np.ndarray
    clip_bounds: Optional[Tuple[float, float, float, float]] = None

    @property
    def mapper_type(self) -> str:
        return "poly12_ridge"

    @property
    def train_X(self) -> np.ndarray:
        return poly12_from_uv(self.train_u_l, self.train_v_l, self.train_u_r, self.train_v_r)

    def _poly12(self, u_l: float, v_l: float, u_r: float, v_r: float) -> np.ndarray:
        return poly12_from_uv(
            np.array([u_l]), np.array([v_l]), np.array([u_r]), np.array([v_r])
        ).reshape(-1)

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        raw = _raw_uv(features)
        if raw is None:
            return None
        u_l, v_l, u_r, v_r = raw
        px, py = _predict_ridge_2d(
            self._poly12(u_l, v_l, u_r, v_r),
            w=self.w,
            intercept=self.intercept,
            mu=self.mu,
            sigma=self.sigma,
        )
        px, py = _clip_xy(px, py, self.clip_bounds)
        return MapperPrediction(x=px, y=py, quality=1.0)

    def leave_one_out_detail_px(self) -> List[dict]:
        return _loocv_poly12_joint(
            self.train_u_l,
            self.train_u_r,
            self.train_v_l,
            self.train_v_r,
            self.train_Y,
            alpha=float(self.alpha),
            clip_bounds=self.clip_bounds,
        )

    def leave_one_out_rms_px(self) -> Optional[float]:
        d = self.leave_one_out_detail_px()
        rms, _ = _loocv_from_detail(d)
        return rms


@dataclass(frozen=True)
class Poly12RidgeSplitMapper:
    w_x: np.ndarray
    b_x: float
    mu_x: np.ndarray
    sigma_x: np.ndarray
    w_y: np.ndarray
    b_y: float
    mu_y: np.ndarray
    sigma_y: np.ndarray
    y_feature_mode: str  # "poly12" | "decoupled_v"
    beta_v_l: Optional[np.ndarray]
    beta_v_r: Optional[np.ndarray]
    alpha: float
    train_u_l: np.ndarray
    train_u_r: np.ndarray
    train_v_l: np.ndarray
    train_v_r: np.ndarray
    train_Y: np.ndarray
    clip_bounds: Optional[Tuple[float, float, float, float]] = None

    @property
    def mapper_type(self) -> str:
        if self.y_feature_mode == "decoupled_v":
            return "poly12_ridge_split_decoupled_y"
        return "poly12_ridge_split"

    @property
    def train_X(self) -> np.ndarray:
        return poly12_from_uv(self.train_u_l, self.train_v_l, self.train_u_r, self.train_v_r)

    def _poly12(self, u_l: float, v_l: float, u_r: float, v_r: float) -> np.ndarray:
        return poly12_from_uv(
            np.array([u_l]), np.array([v_l]), np.array([u_r]), np.array([v_r])
        ).reshape(-1)

    def _y_features(self, u_l: float, u_r: float, v_l: float, v_r: float) -> np.ndarray:
        if self.y_feature_mode == "poly12":
            return self._poly12(u_l, v_l, u_r, v_r)
        assert self.beta_v_l is not None and self.beta_v_r is not None
        vl_r, vr_r = apply_v_residualizers(u_l, u_r, v_l, v_r, beta_l=self.beta_v_l, beta_r=self.beta_v_r)
        return np.array([vl_r, vr_r], dtype=np.float64)

    def predict(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        raw = _raw_uv(features)
        if raw is None:
            return None
        u_l, v_l, u_r, v_r = raw
        px = _predict_ridge_1d(
            self._poly12(u_l, v_l, u_r, v_r),
            w=self.w_x,
            intercept=self.b_x,
            mu=self.mu_x,
            sigma=self.sigma_x,
        )
        py = _predict_ridge_1d(
            self._y_features(u_l, u_r, v_l, v_r),
            w=self.w_y,
            intercept=self.b_y,
            mu=self.mu_y,
            sigma=self.sigma_y,
        )
        px, py = _clip_xy(px, py, self.clip_bounds)
        return MapperPrediction(x=px, y=py, quality=1.0)

    def leave_one_out_detail_px(self) -> List[dict]:
        return _loocv_poly12_split(
            self.train_u_l,
            self.train_u_r,
            self.train_v_l,
            self.train_v_r,
            self.train_Y,
            alpha=float(self.alpha),
            y_mode=self.y_feature_mode,
            clip_bounds=self.clip_bounds,
        )

    def leave_one_out_rms_px(self) -> Optional[float]:
        d = self.leave_one_out_detail_px()
        rms, _ = _loocv_from_detail(d)
        return rms


RidgeCalibrationMapper = Union[
    Pca4BaselineMapper,
    Pca4DecoupledSplitMapper,
    Poly12RidgeMapper,
    Poly12RidgeSplitMapper,
    MapperWithRowBias,
]

COUPLING_POLY12_THRESH = 0.55
POLY12_MAPPER_PREFIX = "poly12"


def _fit_pca4_baseline(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> Pca4BaselineMapper:
    x_tr = np.column_stack([u_l, u_r])
    y_tr = np.column_stack([v_l, v_r])
    wx, bx, mux, sigx = _fit_ridge_1d(x_tr, Y[:, 0], alpha=alpha)
    wy, by, muy, sigy = _fit_ridge_1d(y_tr, Y[:, 1], alpha=alpha)
    return Pca4BaselineMapper(
        w_x=wx,
        b_x=bx,
        mu_x=mux,
        sigma_x=sigx,
        w_y=wy,
        b_y=by,
        mu_y=muy,
        sigma_y=sigy,
        alpha=float(alpha),
        train_u_l=u_l,
        train_u_r=u_r,
        train_v_l=v_l,
        train_v_r=v_r,
        train_Y=Y,
        clip_bounds=clip_bounds,
    )


def _fit_pca4_decoupled(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
    log_coupling: bool,
) -> Pca4DecoupledSplitMapper:
    beta_l, beta_r = fit_v_residualizers(u_l, u_r, v_l, v_r)
    if log_coupling:
        coupling_report(u_l, u_r, v_l, v_r, beta_l=beta_l, beta_r=beta_r)
    vl_r, vr_r = apply_v_residualizers_batch(u_l, u_r, v_l, v_r, beta_l=beta_l, beta_r=beta_r)
    x_tr = np.column_stack([u_l, u_r])
    y_tr = np.column_stack([vl_r, vr_r])
    wx, bx, mux, sigx = _fit_ridge_1d(x_tr, Y[:, 0], alpha=alpha)
    wy, by, muy, sigy = _fit_ridge_1d(y_tr, Y[:, 1], alpha=alpha)
    return Pca4DecoupledSplitMapper(
        w_x=wx,
        b_x=bx,
        mu_x=mux,
        sigma_x=sigx,
        w_y=wy,
        b_y=by,
        mu_y=muy,
        sigma_y=sigy,
        beta_v_l=beta_l,
        beta_v_r=beta_r,
        alpha=float(alpha),
        train_u_l=u_l,
        train_u_r=u_r,
        train_v_l=v_l,
        train_v_r=v_r,
        train_Y=Y,
        clip_bounds=clip_bounds,
    )


def _fit_poly12_joint(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> Poly12RidgeMapper:
    poly = poly12_from_uv(u_l, v_l, u_r, v_r)
    w, intercept, mu, sigma = _fit_ridge(poly, Y, alpha=alpha)
    return Poly12RidgeMapper(
        w=w,
        intercept=np.asarray(intercept, dtype=np.float64).reshape(-1),
        mu=mu,
        sigma=sigma,
        alpha=float(alpha),
        train_u_l=u_l,
        train_u_r=u_r,
        train_v_l=v_l,
        train_v_r=v_r,
        train_Y=Y,
        clip_bounds=clip_bounds,
    )


def _fit_poly12_split(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    Y: np.ndarray,
    *,
    alpha: float,
    y_mode: str,
    clip_bounds: Optional[Tuple[float, float, float, float]],
) -> Poly12RidgeSplitMapper:
    poly = poly12_from_uv(u_l, v_l, u_r, v_r)
    wx, bx, mux, sigx = _fit_ridge_1d(poly, Y[:, 0], alpha=alpha)
    beta_l = beta_r = None
    if y_mode == "poly12":
        wy, by, muy, sigy = _fit_ridge_1d(poly, Y[:, 1], alpha=alpha)
    else:
        beta_l, beta_r = fit_v_residualizers(u_l, u_r, v_l, v_r)
        vl_r, vr_r = apply_v_residualizers_batch(u_l, u_r, v_l, v_r, beta_l=beta_l, beta_r=beta_r)
        y_tr = np.column_stack([vl_r, vr_r])
        wy, by, muy, sigy = _fit_ridge_1d(y_tr, Y[:, 1], alpha=alpha)
    return Poly12RidgeSplitMapper(
        w_x=wx,
        b_x=bx,
        mu_x=mux,
        sigma_x=sigx,
        w_y=wy,
        b_y=by,
        mu_y=muy,
        sigma_y=sigy,
        y_feature_mode=y_mode,
        beta_v_l=beta_l,
        beta_v_r=beta_r,
        alpha=float(alpha),
        train_u_l=u_l,
        train_u_r=u_r,
        train_v_l=v_l,
        train_v_r=v_r,
        train_Y=Y,
        clip_bounds=clip_bounds,
    )


def assess_mapper_error_gates(
    *,
    train_rms_px: Optional[float],
    loocv_rms_px: Optional[float],
    worst_loocv_px: Optional[float],
    max_train_px: Optional[float],
    max_loocv_rms_px: float = 150.0,
    max_target_loocv_px: float = 175.0,
    max_train_error_px: float = 100.0,
    keyboard_mode: bool = False,
) -> Tuple[bool, List[str], List[str]]:
    """Return (hard_pass, hard_fail_reasons, pixel_warnings)."""
    hard: List[str] = []
    warn: List[str] = []
    if loocv_rms_px is not None and loocv_rms_px > max_loocv_rms_px:
        msg = f"LOOCV RMS {loocv_rms_px:.1f}px > {max_loocv_rms_px:.1f}px"
        (warn if keyboard_mode else hard).append(msg)
    if worst_loocv_px is not None and worst_loocv_px > max_target_loocv_px:
        msg = f"worst LOOCV {worst_loocv_px:.1f}px > {max_target_loocv_px:.1f}px"
        (warn if keyboard_mode else hard).append(msg)
    if max_train_px is not None and max_train_px > max_train_error_px:
        msg = f"max train error {max_train_px:.1f}px > {max_train_error_px:.1f}px"
        (warn if keyboard_mode else hard).append(msg)
    return len(hard) == 0, hard, warn


def _is_poly12_mapper(mapper_type: str) -> bool:
    return str(mapper_type).startswith(POLY12_MAPPER_PREFIX)


def _unwrap_ridge_core(model: RidgeCalibrationMapper) -> RidgeCalibrationMapper:
    core: RidgeCalibrationMapper = model
    while isinstance(core, (MapperWithRowBias, MapperWithLocalYCorrection)):
        core = core.inner
    return core


def _keyboard_assessment_model(
    model: RidgeCalibrationMapper,
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence["CalibrationTarget"],
    verbose: bool = False,
) -> RidgeCalibrationMapper:
    """Apply row Y bias + local Y correction for region-gate evaluation (same as runtime)."""
    core = _unwrap_ridge_core(model)
    row_centers, row_bias = compute_row_y_residuals(
        model=core, samples=samples, targets=targets
    )
    wrapped: RidgeCalibrationMapper = attach_row_y_bias(
        core,
        row_y_centers=row_centers,
        row_y_bias=row_bias,
    )
    return attach_local_y_correction(wrapped, samples=samples, verbose=verbose)


def _evaluate_candidate(
    mapper_type: str,
    model: RidgeCalibrationMapper,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    *,
    targets: Optional[Sequence["CalibrationTarget"]] = None,
    calibration_mode: str = "keyboard9",
    max_loocv_rms_px: float = 150.0,
    max_target_loocv_px: float = 175.0,
    max_train_error_px: float = 100.0,
    half_key_height_px: float = 34.0,
) -> MapperCandidateReport:
    detail = tuple(model.leave_one_out_detail_px())
    loocv_rms, worst = _loocv_from_detail(detail)
    train_rms = _train_rms_px(model, samples)
    max_train = _max_train_from_samples(model, samples)
    keyboard_mode = str(calibration_mode).lower().startswith("keyboard")
    pixel_ok, pixel_hard, pixel_warn = assess_mapper_error_gates(
        train_rms_px=train_rms,
        loocv_rms_px=loocv_rms,
        worst_loocv_px=worst,
        max_train_px=max_train,
        max_loocv_rms_px=max_loocv_rms_px,
        max_target_loocv_px=max_target_loocv_px,
        max_train_error_px=max_train_error_px,
        keyboard_mode=keyboard_mode,
    )
    region_train_wrong = 0
    region_loocv_wrong = 0
    worst_train_label = ""
    worst_loocv_label = ""
    gate_reasons: List[str] = list(pixel_hard)
    if keyboard_mode and targets is not None and len(targets) >= len(samples):
        assess_model = _keyboard_assessment_model(
            model,
            samples=samples,
            targets=targets,
            verbose=False,
        )
        loocv_assess = tuple(assess_model.leave_one_out_detail_px())
        region = assess_region_gates(
            model=assess_model,
            samples=samples,
            targets=targets,
            loocv_detail=loocv_assess,
            keyboard_mode=True,
            half_key_height_px=half_key_height_px,
            calibration_mode=calibration_mode,
            verbose=False,
        )
        region_train_wrong = region.train_region_wrong
        region_loocv_wrong = region.loocv_region_wrong
        worst_train_label = region.worst_train_label
        worst_loocv_label = region.worst_loocv_label
        gate_reasons.extend(region.hard_fail_reasons)
        gate_reasons.extend(f"(warning) {w}" for w in pixel_warn)
        gates_ok = bool(region.passed)
    else:
        gate_reasons.extend(pixel_hard)
        gate_reasons.extend(f"(warning) {w}" for w in pixel_warn)
        gates_ok = pixel_ok

    return MapperCandidateReport(
        mapper_type=mapper_type,
        success=True,
        message="ok",
        train_rms_px=train_rms,
        loocv_rms_px=loocv_rms,
        worst_loocv_px=worst,
        max_train_px=max_train,
        alpha=float(getattr(model, "alpha", 0.0)),
        loocv_detail=detail,
        model=model,
        quality_gates_passed=gates_ok,
        quality_gate_reasons=tuple(gate_reasons),
        region_train_wrong=region_train_wrong,
        region_loocv_wrong=region_loocv_wrong,
        worst_train_label=worst_train_label,
        worst_loocv_label=worst_loocv_label,
    )


def print_mapper_candidate_reports(reports: Sequence[MapperCandidateReport]) -> None:
    print("[calib2] --- mapper candidate comparison (LOOCV refit per fold) ---")
    for r in reports:
        alpha_s = f"{r.alpha:.1f}" if r.alpha is not None else "n/a"
        gates_s = (
            "PASSED"
            if r.quality_gates_passed
            else ("FAILED" if r.quality_gates_passed is False else "n/a")
        )
        print(
            f"[calib2] candidate mapper_type={r.mapper_type} success={r.success} "
            f"train_RMS={_fmt_px(r.train_rms_px)} "
            f"LOOCV_RMS={_fmt_px(r.loocv_rms_px)} "
            f"worst_LOOCV={_fmt_px(r.worst_loocv_px)} "
            f"max_train={_fmt_px(r.max_train_px)} "
            f"alpha={alpha_s} quality_gates={gates_s}"
            + (f" msg={r.message}" if not r.success else "")
        )
        if r.quality_gate_reasons:
            for reason in r.quality_gate_reasons:
                tag = "warning" if str(reason).startswith("(warning)") else "gate"
                print(f"[calib2]   {tag}: {reason}")
        if r.worst_train_label or r.region_train_wrong or r.region_loocv_wrong:
            print(
                f"[calib2]   region: train_wrong={r.region_train_wrong} "
                f"loocv_wrong={r.region_loocv_wrong} "
                f"worst_train={r.worst_train_label or 'n/a'} "
                f"worst_loocv={r.worst_loocv_label or 'n/a'}"
            )


def _fmt_px(v: Optional[float]) -> str:
    return f"{v:.1f}px" if v is not None and np.isfinite(v) else "n/a"


def _simplicity_rank(mapper_type: str) -> int:
    base = mapper_type.split("_decoupled")[0]
    for i, name in enumerate(MAPPER_SIMPLICITY):
        if base == name or mapper_type.startswith(name):
            return i
    return len(MAPPER_SIMPLICITY)


def _rank_candidates(
    reports: Sequence[MapperCandidateReport],
    *,
    v_u_corr: float = 0.0,
    prefer_poly12_on_coupling: bool = True,
) -> List[MapperCandidateReport]:
    ok = [
        r
        for r in reports
        if r.success
        and r.model is not None
        and r.loocv_rms_px is not None
        and r.quality_gates_passed is True
    ]
    if not ok:
        ok = [r for r in reports if r.success and r.model is not None and r.loocv_rms_px is not None]
    if not ok:
        return list(reports)

    pool = list(ok)
    if prefer_poly12_on_coupling and abs(float(v_u_corr)) >= COUPLING_POLY12_THRESH:
        poly = [r for r in pool if _is_poly12_mapper(r.mapper_type)]
        if poly:
            print(
                f"[calib2] mapper pool: high v–u coupling (r={v_u_corr:.3f}) — "
                f"prefer poly12 candidates ({len(poly)}/{len(pool)})"
            )
            pool = poly

    def sort_key(r: MapperCandidateReport) -> Tuple[int, float, float, float, int]:
        region_wrong = int(r.region_train_wrong) + int(r.region_loocv_wrong)
        return (
            region_wrong,
            float(r.loocv_rms_px or float("inf")),
            float(r.worst_loocv_px or float("inf")),
            float(r.max_train_px or float("inf")),
            _simplicity_rank(r.mapper_type),
        )

    pool.sort(key=sort_key)
    best = pool[0]
    tied = [r for r in pool if abs(float(r.loocv_rms_px) - float(best.loocv_rms_px)) <= LOOCV_TIE_TOL_PX]
    if len(tied) > 1:
        tied.sort(key=sort_key)
        best = tied[0]
    ordered = [best] + [r for r in pool if r is not best]
    failed = [r for r in reports if r not in pool]
    return ordered + failed


def fit_calibration_mapper(
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Optional[Sequence["CalibrationTarget"]] = None,
    calibration_mode: str = "keyboard9",
    alpha: float = 10.0,
    screen_rect: Optional[Tuple[float, float, float, float]] = None,
    min_alpha: float = 1.0,
    max_loocv_rms_px: float = 150.0,
    max_target_loocv_px: float = 175.0,
    max_train_error_px: float = 100.0,
    half_key_height_px: float = 34.0,
) -> MapperFitResult:
    """
    Fit the frozen active mapper (pca4_baseline) and return it when quality gates pass.

    Other ridge candidates (decoupled, poly12, etc.) remain in this module but are not
    evaluated on the active calibration path while FROZEN_ACTIVE_MAPPER is set.
    """
    print(
        f"[calib2] mapper freeze: active path locked to {FROZEN_ACTIVE_MAPPER} "
        f"(LOOCV candidate ranking disabled)"
    )
    extracted = extract_uv_arrays(samples)
    if extracted is None:
        return MapperFitResult(success=False, message="Need at least 5 samples with PCA u/v for Ridge.")
    u_l, u_r, v_l, v_r, Y = extracted
    clip_bounds = _bounds_from_screen_rect(screen_rect)
    gate_kw = dict(
        targets=targets,
        calibration_mode=calibration_mode,
        max_loocv_rms_px=max_loocv_rms_px,
        max_target_loocv_px=max_target_loocv_px,
        max_train_error_px=max_train_error_px,
        half_key_height_px=half_key_height_px,
    )

    def alpha_for(candidate_label: str, loocv_builder):
        return _auto_alpha(
            lambda a: _loocv_rms_from_detail(loocv_builder(a)),
            min_alpha=min_alpha,
            candidate_label=candidate_label,
        )

    a_base = alpha_for(
        FROZEN_ACTIVE_MAPPER,
        lambda a: _loocv_pca4_baseline(u_l, u_r, v_l, v_r, Y, alpha=a, clip_bounds=clip_bounds),
    )

    reports: List[MapperCandidateReport] = []
    try:
        m_base = _fit_pca4_baseline(u_l, u_r, v_l, v_r, Y, alpha=a_base, clip_bounds=clip_bounds)
        reports.append(_evaluate_candidate(FROZEN_ACTIVE_MAPPER, m_base, samples, **gate_kw))
    except Exception as e:
        reports.append(
            MapperCandidateReport(FROZEN_ACTIVE_MAPPER, False, str(e), None, None, None, None, None, ())
        )

    print_mapper_candidate_reports(reports)
    winner = next(
        (r for r in reports if r.success and r.model is not None and r.quality_gates_passed is True),
        None,
    )
    if winner is None or winner.model is None:
        # Best-effort: accept frozen mapper when region gates are close enough (keyboard only).
        ok_reports = [r for r in reports if r.success and r.model is not None and r.loocv_rms_px is not None]
        if ok_reports and targets is not None and str(calibration_mode).lower().startswith("keyboard"):
            _n, _mt, max_loocv = region_gate_limits(targets, calibration_mode=calibration_mode)
            ok_reports.sort(
                key=lambda r: (
                    int(r.region_loocv_wrong),
                    int(r.region_train_wrong),
                    float(r.loocv_rms_px or 1e9),
                )
            )
            best = ok_reports[0]
            if int(best.region_loocv_wrong) <= max_loocv and int(best.region_train_wrong) <= _mt:
                print(
                    f"[calib2] region gates: using best-effort {FROZEN_ACTIVE_MAPPER} "
                    f"(loocv_region_wrong={best.region_loocv_wrong} train_region_wrong={best.region_train_wrong})"
                )
                winner = best

    if winner is None or winner.model is None:
        gated = [r for r in reports if r.success and r.quality_gates_passed is False]
        if gated:
            reasons = "; ".join(
                f"{r.mapper_type}: {', '.join(r.quality_gate_reasons)}" for r in gated[:2]
            )
            return MapperFitResult(
                success=False,
                message=(
                    f"{FROZEN_ACTIVE_MAPPER} did not pass quality gates ({reasons}). "
                    f"Recalibrate with steadier fixation."
                ),
            )
        return MapperFitResult(
            success=False,
            message=f"{FROZEN_ACTIVE_MAPPER} failed to fit.",
        )

    final_model: RidgeCalibrationMapper = winner.model
    if targets is not None and len(targets) >= len(samples):
        final_model = _keyboard_assessment_model(
            final_model,
            samples=samples,
            targets=targets,
            verbose=True,
        )
        if str(calibration_mode).lower().startswith("keyboard"):
            loocv_after = final_model.leave_one_out_detail_px()
            assess_region_gates(
                model=final_model,
                samples=samples,
                targets=targets,
                loocv_detail=loocv_after,
                keyboard_mode=True,
                half_key_height_px=half_key_height_px,
                calibration_mode=calibration_mode,
                verbose=True,
            )

    print(
        f"[calib2] SELECTED mapper_type={FROZEN_ACTIVE_MAPPER} "
        f"(frozen active mapper; inner_type={final_model.mapper_type}) "
        f"LOOCV_RMS={_fmt_px(winner.loocv_rms_px)} "
        f"worst_LOOCV={_fmt_px(winner.worst_loocv_px)} "
        f"worst_train={winner.worst_train_label or 'n/a'} "
        f"worst_loocv={winner.worst_loocv_label or 'n/a'} "
        f"train_RMS={_fmt_px(winner.train_rms_px)} "
        f"alpha={winner.alpha:.1f}"
    )
    return MapperFitResult(
        success=True,
        message=f"Selected {FROZEN_ACTIVE_MAPPER} (LOOCV={winner.loocv_rms_px:.1f}px).",
        model=final_model,
        rms_px=winner.train_rms_px,
        candidate_reports=tuple(reports),
    )


class RidgeRegressionMapper:
    """Backward-compatible entry point; delegates to fit_calibration_mapper."""

    @classmethod
    def fit(
        cls,
        *,
        samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
        alpha: float = 10.0,
        screen_rect: Optional[Tuple[float, float, float, float]] = None,
        min_alpha: float = 1.0,
    ) -> MapperFitResult:
        return fit_calibration_mapper(
            samples=samples,
            alpha=alpha,
            screen_rect=screen_rect,
            min_alpha=min_alpha,
        )
