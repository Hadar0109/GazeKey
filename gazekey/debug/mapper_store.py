"""Persist fitted PCA4 ridge mappers for inspection (not loaded on startup)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import numpy as np

from gazekey.evaluation.session_paths import calibration_v2_path, ensure_session_dir
from gazekey.mapping.ridge import Pca4BaselineMapper, RidgeCalibrationMapper, _unwrap_core
from gazekey.mapping.row_bias import MapperWithRowBias, attach_row_y_bias
from gazekey.mvp_log import mvp_log

CALIBRATION_V2_FILE_VERSION = 7


def _arr_to_list(a: np.ndarray) -> List[float]:
    return [float(x) for x in np.asarray(a, dtype=np.float64).reshape(-1)]


def _bounds_to_json(bounds: Optional[Tuple[float, float, float, float]]) -> Optional[List[float]]:
    if bounds is None:
        return None
    return [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]


def _unwrap_wrappers(model: RidgeCalibrationMapper) -> tuple[Pca4BaselineMapper, dict[str, Any]]:
    meta: dict[str, Any] = {}
    m: Any = model
    if isinstance(m, MapperWithRowBias):
        meta["row_y_centers"] = [float(x) for x in m.row_y_centers]
        meta["row_y_bias"] = [float(x) for x in m.row_y_bias]
        m = m.inner
    core = _unwrap_core(model)
    if not isinstance(core, Pca4BaselineMapper):
        raise TypeError(f"Unsupported mapper type: {type(core)}")
    return core, meta


def mapper_to_dict(
    model: RidgeCalibrationMapper,
    *,
    calibration_mode: str,
    mapper_mode: str,
) -> dict[str, Any]:
    core, wrap_meta = _unwrap_wrappers(model)
    payload: dict[str, Any] = {
        "file_version": CALIBRATION_V2_FILE_VERSION,
        "mapper_type": core.mapper_type,
        "calibration_mode": calibration_mode,
        "mapper_mode": mapper_mode,
        "alpha": float(model.alpha),
        "clip_bounds": _bounds_to_json(model.clip_bounds),
        "train_u_l": _arr_to_list(model.train_u_l),
        "train_u_r": _arr_to_list(model.train_u_r),
        "train_v_l": _arr_to_list(model.train_v_l),
        "train_v_r": _arr_to_list(model.train_v_r),
        "train_Y": _arr_to_list(model.train_Y.reshape(-1)),
        "train_n": int(model.train_Y.shape[0]),
        "w_x": _arr_to_list(core.w_x),
        "b_x": float(core.b_x),
        "mu_x": _arr_to_list(core.mu_x),
        "sigma_x": _arr_to_list(core.sigma_x),
        "w_y": _arr_to_list(core.w_y),
        "b_y": float(core.b_y),
        "mu_y": _arr_to_list(core.mu_y),
        "sigma_y": _arr_to_list(core.sigma_y),
    }
    payload.update(wrap_meta)
    return payload


def save_calibration_mapper(
    model: RidgeCalibrationMapper,
    *,
    session_id: str,
    calibration_mode: str,
    mapper_mode: str,
    runs_dir: Optional[Union[Path, str]] = None,
) -> Path:
    """Write ``runs/<session_id>/calibration_v2.json``; returns the path."""
    ensure_session_dir(session_id, runs_dir=runs_dir)
    path = calibration_v2_path(session_id, runs_dir=runs_dir)
    payload = mapper_to_dict(
        model,
        calibration_mode=calibration_mode,
        mapper_mode=mapper_mode,
    )
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    mvp_log(f"[calib] saved mapper snapshot -> {path}")
    return path
