"""Evaluation-only unclamped vs clamped mapped-xy (research R7).

Does **not** change ``Pca4BaselineMapper._clip_xy`` or ``MapperRuntime.clamp_xy``.
Recomputes ridge coordinates from public mapper weights, skipping clip bounds.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures


def _core_mapper(model: Any) -> Any:
    core = model
    while hasattr(core, "inner"):
        core = core.inner
    return core


def _ridge_xy(core: Any, features: FrameFeatures) -> Optional[Tuple[float, float]]:
    u_l, v_l, u_r, v_r = features.pca_uL, features.pca_vL, features.pca_uR, features.pca_vR
    if u_l is None or v_l is None or u_r is None or v_r is None:
        return None
    w_x = getattr(core, "w_x", None)
    w_y = getattr(core, "w_y", None)
    if w_x is None or w_y is None:
        return None
    xs = (np.asarray([float(u_l), float(u_r)], dtype=np.float64) - core.mu_x) / core.sigma_x
    ys = (np.asarray([float(v_l), float(v_r)], dtype=np.float64) - core.mu_y) / core.sigma_y
    px = float(xs @ core.w_x + core.b_x)
    py = float(ys @ core.w_y + core.b_y)
    return px, py


def _apply_row_bias(model: Any, px: float, py: float) -> Tuple[float, float]:
    centers = getattr(model, "row_y_centers", None)
    bias = getattr(model, "row_y_bias", None)
    if centers is None or bias is None:
        return px, py
    ys = np.array(centers, dtype=np.float64)
    ri = int(np.argmin(np.abs(ys - float(py))))
    return px, float(py) - float(bias[ri])


def unclamped_xy_from_model(model: Any, features: FrameFeatures) -> Optional[Tuple[float, float]]:
    """Ridge (and optional row-Y bias) without clip. Diagnostic only."""
    if model is None:
        return None
    core = _core_mapper(model)
    raw = _ridge_xy(core, features)
    if raw is None:
        return None
    px, py = raw
    if model is not core:
        px, py = _apply_row_bias(model, px, py)
    return float(px), float(py)


def clip_bounds_of(model: Any) -> Optional[Tuple[float, float, float, float]]:
    bounds = getattr(model, "clip_bounds", None) if model is not None else None
    if bounds is None:
        return None
    try:
        x0, y0, x1, y1 = bounds
        return float(x0), float(y0), float(x1), float(y1)
    except (TypeError, ValueError):
        return None


def make_eval_predict_fns(host: Any) -> Tuple[Any, Any]:
    """Product clamped predict + matching unclamped diagnostic (one smoother step).

    Clamped callback is ``host._predict_screen_xy`` →
    ``MapperRuntime.key_accuracy_predict_screen_xy``. Unclamped reuses the
    smoother state after that call so EMA is not advanced twice.
    """
    last_smooth: dict[str, Optional[FrameFeatures]] = {"feat": None}

    def clamped(feat: FrameFeatures) -> Optional[Tuple[float, float]]:
        xy = host._predict_screen_xy(feat)
        sm = getattr(host, "_feature_smoother", None)
        if sm is not None and getattr(sm, "_u_l", None) is not None:
            last_smooth["feat"] = FrameFeatures(
                timestamp_ms=feat.timestamp_ms,
                face_detected=feat.face_detected,
                blink=feat.blink,
                confidence=feat.confidence,
                Lh=feat.Lh,
                Lv=feat.Lv,
                Rh=feat.Rh,
                Rv=feat.Rv,
                avg_h=feat.avg_h,
                avg_v=feat.avg_v,
                eye_box_w=feat.eye_box_w,
                eye_box_h=feat.eye_box_h,
                face_x=feat.face_x,
                face_y=feat.face_y,
                pca_uL=sm._u_l,
                pca_vL=sm._v_l,
                pca_uR=sm._u_r,
                pca_vR=sm._v_r,
            )
        else:
            last_smooth["feat"] = feat
        return xy

    def unclamped(feat: FrameFeatures) -> Optional[Tuple[float, float]]:
        del feat
        model = getattr(host, "_gaze_mapper", None)
        smooth = last_smooth["feat"]
        if smooth is None:
            return None
        xy = unclamped_xy_from_model(model, smooth)
        if xy is None:
            return None
        bx = float(getattr(host, "_gaze_bias_x", 0.0) or 0.0)
        by = float(getattr(host, "_gaze_bias_y", 0.0) or 0.0)
        return float(xy[0]) + bx, float(xy[1]) + by

    return clamped, unclamped
