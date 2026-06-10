"""PCA4 ridge mapper: fit, LOOCV alpha selection, and predict (active MVP path only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple, Union

import numpy as np

from gazekey.calibration.region_quality import (
    assess_region_gates,
    compute_row_y_residuals,
)
from gazekey.calibration.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperFitResult, MapperPrediction
from gazekey.mapping.config import (
    ACTIVE_MAPPER,
    ALPHA_GRID,
    ALPHA_SELECT_LOOCV_TOL_PX,
    APPLY_ROW_Y_BIAS,
    MIN_ALPHA,
)
from gazekey.mapping.row_bias import MapperWithRowBias, attach_row_y_bias
from gazekey.mvp_log import mvp_log, mvp_verbose

FROZEN_ACTIVE_MAPPER = ACTIVE_MAPPER


def extract_uv_arrays(
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Return (u_l, u_r, v_l, v_r, Y) or None if insufficient PCA data."""
    u_l_list: list[float] = []
    u_r_list: list[float] = []
    v_l_list: list[float] = []
    v_r_list: list[float] = []
    ys: list[np.ndarray] = []
    for f, (x, y) in samples:
        if f.pca_uL is None or f.pca_vL is None or f.pca_uR is None or f.pca_vR is None:
            continue
        u_l_list.append(float(f.pca_uL))
        u_r_list.append(float(f.pca_uR))
        v_l_list.append(float(f.pca_vL))
        v_r_list.append(float(f.pca_vR))
        ys.append(np.array([float(x), float(y)], dtype=np.float64))
    if len(ys) < 5:
        return None
    return (
        np.array(u_l_list, dtype=np.float64),
        np.array(u_r_list, dtype=np.float64),
        np.array(v_l_list, dtype=np.float64),
        np.array(v_r_list, dtype=np.float64),
        np.stack(ys, axis=0),
    )


def _raw_uv(f: FrameFeatures) -> Optional[Tuple[float, float, float, float]]:
    u_l, v_l, u_r, v_r = f.pca_uL, f.pca_vL, f.pca_uR, f.pca_vR
    if u_l is None or v_l is None or u_r is None or v_r is None:
        return None
    return float(u_l), float(v_l), float(u_r), float(v_r)


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


def _loocv_rms_from_detail(detail: Sequence[dict]) -> float:
    errs = [float(d["err"]) for d in detail]
    return float(np.sqrt(np.mean(np.array(errs, dtype=np.float64) ** 2)))


def _loocv_from_detail(detail: Sequence[dict]) -> Tuple[Optional[float], Optional[float]]:
    if not detail:
        return None, None
    errs = [float(d["err"]) for d in detail]
    return float(np.sqrt(np.mean(np.array(errs, dtype=np.float64) ** 2))), float(max(errs))


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


def _auto_alpha(
    loocv_fn,
    *,
    min_alpha: float = MIN_ALPHA,
) -> float:
    try:
        scored = [(float(loocv_fn(a)), float(a)) for a in ALPHA_GRID]
        scored = [t for t in scored if np.isfinite(t[0])]
        if scored:
            best_loocv = min(t[0] for t in scored)
            tol = float(ALPHA_SELECT_LOOCV_TOL_PX)
            near = [t for t in scored if t[0] <= best_loocv + tol]
            chosen_alpha = max(t[1] for t in near)
            chosen_alpha = float(max(float(min_alpha), chosen_alpha))
            if mvp_verbose():
                parts = " ".join(f"a={a:.0f}:{rms:.1f}px" for rms, a in sorted(scored, key=lambda t: t[1]))
                mvp_log(f"[calib] alpha grid pca4_baseline: {parts} -> selected {chosen_alpha:.1f}")
            return chosen_alpha
    except Exception as e:
        mvp_log(f"[calib] alpha grid failed ({e}), using min_alpha={min_alpha:.1f}")
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


RidgeCalibrationMapper = Union[Pca4BaselineMapper, MapperWithRowBias]


def _unwrap_core(model: RidgeCalibrationMapper) -> Pca4BaselineMapper:
    core: RidgeCalibrationMapper = model
    while isinstance(core, MapperWithRowBias):
        core = core.inner
    return core  # type: ignore[return-value]


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


def _apply_row_bias_if_enabled(
    model: Pca4BaselineMapper,
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
) -> RidgeCalibrationMapper:
    if not APPLY_ROW_Y_BIAS:
        return model
    row_centers, row_bias = compute_row_y_residuals(model=model, samples=samples, targets=targets)
    return attach_row_y_bias(model, row_y_centers=row_centers, row_y_bias=row_bias)


def fit_calibration_mapper(
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Optional[Sequence[CalibrationTarget]] = None,
    calibration_mode: str = "keyboard15",
    alpha: float = 10.0,
    screen_rect: Optional[Tuple[float, float, float, float]] = None,
    min_alpha: float = MIN_ALPHA,
    max_loocv_rms_px: float = 150.0,
    max_target_loocv_px: float = 175.0,
    max_train_error_px: float = 100.0,
    half_key_height_px: float = 34.0,
) -> MapperFitResult:
    """Fit PCA4 baseline ridge and optional row-Y bias for keyboard calibration."""
    del alpha  # LOOCV grid selects alpha; kept for API compatibility.
    mvp_log(f"[calib] fitting active mapper: {FROZEN_ACTIVE_MAPPER}")
    extracted = extract_uv_arrays(samples)
    if extracted is None:
        return MapperFitResult(success=False, message="Need at least 5 samples with PCA u/v for Ridge.")
    u_l, u_r, v_l, v_r, Y = extracted
    clip_bounds = _bounds_from_screen_rect(screen_rect)
    chosen_alpha = _auto_alpha(
        lambda a: _loocv_rms_from_detail(
            _loocv_pca4_baseline(u_l, u_r, v_l, v_r, Y, alpha=a, clip_bounds=clip_bounds)
        ),
        min_alpha=min_alpha,
    )
    try:
        core = _fit_pca4_baseline(u_l, u_r, v_l, v_r, Y, alpha=chosen_alpha, clip_bounds=clip_bounds)
    except Exception as e:
        return MapperFitResult(success=False, message=str(e))

    train_rms = _train_rms_px(core, samples)
    loocv_detail = core.leave_one_out_detail_px()
    loocv_rms, worst_loocv = _loocv_from_detail(loocv_detail)
    max_train = _max_train_from_samples(core, samples)
    keyboard_mode = str(calibration_mode).lower().startswith("keyboard")

    if mvp_verbose():
        mvp_log(
            f"[calib] pca4_baseline train_RMS={train_rms:.1f}px "
            f"LOOCV_RMS={loocv_rms:.1f}px alpha={chosen_alpha:.1f}"
            if train_rms is not None and loocv_rms is not None
            else f"[calib] pca4_baseline alpha={chosen_alpha:.1f}"
        )
        if loocv_rms is not None and loocv_rms > max_loocv_rms_px:
            mvp_log(f"[calib]   warning: LOOCV RMS {loocv_rms:.1f}px > {max_loocv_rms_px:.1f}px")
        if worst_loocv is not None and worst_loocv > max_target_loocv_px:
            mvp_log(f"[calib]   warning: worst LOOCV {worst_loocv:.1f}px > {max_target_loocv_px:.1f}px")
        if max_train is not None and max_train > max_train_error_px:
            mvp_log(f"[calib]   warning: max train {max_train:.1f}px > {max_train_error_px:.1f}px")

    final_model: RidgeCalibrationMapper = core
    if keyboard_mode and targets is not None and len(targets) >= len(samples):
        final_model = _apply_row_bias_if_enabled(core, samples=samples, targets=targets)
        loocv_after = final_model.leave_one_out_detail_px()
        assess_region_gates(
            model=final_model,
            samples=samples,
            targets=targets,
            loocv_detail=loocv_after,
            keyboard_mode=True,
            half_key_height_px=half_key_height_px,
            calibration_mode=calibration_mode,
            verbose=mvp_verbose(),
        )

    msg = f"Fitted {FROZEN_ACTIVE_MAPPER}"
    if loocv_rms is not None:
        msg += f" (LOOCV={loocv_rms:.1f}px)"
    return MapperFitResult(success=True, message=msg, model=final_model, rms_px=train_rms)


class RidgeRegressionMapper:
    """Backward-compatible entry point; delegates to fit_calibration_mapper."""

    @classmethod
    def fit(
        cls,
        *,
        samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
        alpha: float = 10.0,
        screen_rect: Optional[Tuple[float, float, float, float]] = None,
        min_alpha: float = MIN_ALPHA,
    ) -> MapperFitResult:
        return fit_calibration_mapper(
            samples=samples,
            alpha=alpha,
            screen_rect=screen_rect,
            min_alpha=min_alpha,
        )
