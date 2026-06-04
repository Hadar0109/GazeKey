"""Persist calibration v2 ridge mappers (version 7 JSON, separate from legacy v1 store)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional, Tuple

import numpy as np

from gazekey.mapping.ridge import (
    Pca4BaselineMapper,
    Pca4DecoupledSplitMapper,
    Poly12RidgeMapper,
    Poly12RidgeSplitMapper,
    RidgeCalibrationMapper,
)
from gazekey.mapping.local_y_correction import MapperWithLocalYCorrection
from gazekey.mapping.row_bias import MapperWithRowBias, attach_row_y_bias

CALIBRATION_V2_FILE_VERSION = 7
DEFAULT_CALIBRATION_V2_PATH = Path(__file__).resolve().parents[2] / "calibration_v2.json"


def _arr_to_list(a: np.ndarray) -> List[float]:
    return [float(x) for x in np.asarray(a, dtype=np.float64).reshape(-1)]


def _list_to_arr(v: Any, shape: Optional[Tuple[int, ...]] = None) -> np.ndarray:
    a = np.asarray(v, dtype=np.float64)
    if shape is not None:
        a = a.reshape(shape)
    return a


def _bounds_to_json(bounds: Optional[Tuple[float, float, float, float]]) -> Optional[List[float]]:
    if bounds is None:
        return None
    return [float(bounds[0]), float(bounds[1]), float(bounds[2]), float(bounds[3])]


def _bounds_from_json(v: Any) -> Optional[Tuple[float, float, float, float]]:
    if v is None:
        return None
    xs = [float(x) for x in v]
    if len(xs) != 4:
        return None
    return xs[0], xs[1], xs[2], xs[3]


def _train_arrays(model: RidgeCalibrationMapper) -> dict[str, List[float]]:
    return {
        "train_u_l": _arr_to_list(model.train_u_l),
        "train_u_r": _arr_to_list(model.train_u_r),
        "train_v_l": _arr_to_list(model.train_v_l),
        "train_v_r": _arr_to_list(model.train_v_r),
        "train_Y": _arr_to_list(model.train_Y.reshape(-1)),
        "train_n": int(model.train_Y.shape[0]),
    }


def _unwrap_mappers(model: RidgeCalibrationMapper) -> tuple[RidgeCalibrationMapper, dict]:
    """Return (core ridge mapper, wrapper metadata for save)."""
    meta: dict = {}
    m: RidgeCalibrationMapper = model
    if isinstance(m, MapperWithLocalYCorrection):
        meta["local_y_train_x"] = [float(x) for x in m.train_x]
        meta["local_y_train_dy"] = [float(x) for x in m.train_dy]
        m = m.inner
    if isinstance(m, MapperWithRowBias):
        meta["row_y_centers"] = [float(x) for x in m.row_y_centers]
        meta["row_y_bias"] = [float(x) for x in m.row_y_bias]
        m = m.inner
    return m, meta


def _core_mapper(model: RidgeCalibrationMapper) -> RidgeCalibrationMapper:
    core, _ = _unwrap_mappers(model)
    return core


def mapper_to_dict(
    model: RidgeCalibrationMapper,
    *,
    calibration_mode: str,
    mapper_mode: str,
) -> dict[str, Any]:
    """Serialize a fitted ridge mapper for JSON storage."""
    core, wrap_meta = _unwrap_mappers(model)
    base: dict[str, Any] = {
        "file_version": CALIBRATION_V2_FILE_VERSION,
        "mapper_type": core.mapper_type,
        "calibration_mode": calibration_mode,
        "mapper_mode": mapper_mode,
        "alpha": float(model.alpha),
        "clip_bounds": _bounds_to_json(model.clip_bounds),
    }
    base.update(_train_arrays(model))
    base.update(wrap_meta)

    if isinstance(core, Pca4BaselineMapper):
        base.update(
            {
                "w_x": _arr_to_list(core.w_x),
                "b_x": float(core.b_x),
                "mu_x": _arr_to_list(core.mu_x),
                "sigma_x": _arr_to_list(core.sigma_x),
                "w_y": _arr_to_list(core.w_y),
                "b_y": float(core.b_y),
                "mu_y": _arr_to_list(core.mu_y),
                "sigma_y": _arr_to_list(core.sigma_y),
            }
        )
    elif isinstance(core, Pca4DecoupledSplitMapper):
        base.update(
            {
                "w_x": _arr_to_list(core.w_x),
                "b_x": float(core.b_x),
                "mu_x": _arr_to_list(core.mu_x),
                "sigma_x": _arr_to_list(core.sigma_x),
                "w_y": _arr_to_list(core.w_y),
                "b_y": float(core.b_y),
                "mu_y": _arr_to_list(core.mu_y),
                "sigma_y": _arr_to_list(core.sigma_y),
                "beta_v_l": _arr_to_list(core.beta_v_l),
                "beta_v_r": _arr_to_list(core.beta_v_r),
            }
        )
    elif isinstance(core, Poly12RidgeMapper):
        base.update(
            {
                "w": _arr_to_list(core.w.reshape(-1)),
                "w_shape": list(core.w.shape),
                "intercept": _arr_to_list(core.intercept),
                "mu": _arr_to_list(core.mu),
                "sigma": _arr_to_list(core.sigma),
            }
        )
    elif isinstance(core, Poly12RidgeSplitMapper):
        base.update(
            {
                "w_x": _arr_to_list(core.w_x),
                "b_x": float(core.b_x),
                "mu_x": _arr_to_list(core.mu_x),
                "sigma_x": _arr_to_list(core.sigma_x),
                "w_y": _arr_to_list(core.w_y),
                "b_y": float(core.b_y),
                "mu_y": _arr_to_list(core.mu_y),
                "sigma_y": _arr_to_list(core.sigma_y),
                "y_feature_mode": core.y_feature_mode,
                "beta_v_l": _arr_to_list(core.beta_v_l) if core.beta_v_l is not None else None,
                "beta_v_r": _arr_to_list(core.beta_v_r) if core.beta_v_r is not None else None,
            }
        )
    else:
        raise TypeError(f"Unsupported mapper type: {type(core)}")
    return base


def _apply_wrappers_from_dict(
    model: RidgeCalibrationMapper, data: dict[str, Any]
) -> RidgeCalibrationMapper:
    centers = data.get("row_y_centers")
    bias = data.get("row_y_bias")
    if centers is not None and bias is not None and len(centers) == 3 and len(bias) == 3:
        model = attach_row_y_bias(
            model,
            row_y_centers=(float(centers[0]), float(centers[1]), float(centers[2])),
            row_y_bias=(float(bias[0]), float(bias[1]), float(bias[2])),
        )
    lx = data.get("local_y_train_x")
    ldy = data.get("local_y_train_dy")
    if lx is not None and ldy is not None and len(lx) >= 3 and len(lx) == len(ldy):
        model = MapperWithLocalYCorrection(
            inner=model,
            train_x=np.asarray(lx, dtype=np.float64),
            train_dy=np.asarray(ldy, dtype=np.float64),
        )
    return model


def mapper_from_dict(data: dict[str, Any]) -> Optional[RidgeCalibrationMapper]:
    """Deserialize a ridge mapper; returns None if version/type unsupported."""
    version = int(data.get("file_version", 0))
    if version != CALIBRATION_V2_FILE_VERSION:
        print(f"[calib2] calibration_v2.json version {version} unsupported (need {CALIBRATION_V2_FILE_VERSION})")
        return None

    n = int(data.get("train_n", 0))
    if n < 5:
        return None
    u_l = _list_to_arr(data["train_u_l"])
    u_r = _list_to_arr(data["train_u_r"])
    v_l = _list_to_arr(data["train_v_l"])
    v_r = _list_to_arr(data["train_v_r"])
    y_flat = _list_to_arr(data["train_Y"])
    y = y_flat.reshape(n, 2)
    clip_bounds = _bounds_from_json(data.get("clip_bounds"))
    alpha = float(data.get("alpha", 10.0))
    mtype = str(data.get("mapper_type", ""))

    model: Optional[RidgeCalibrationMapper] = None
    if mtype == "pca4_baseline":
        model = Pca4BaselineMapper(
            w_x=_list_to_arr(data["w_x"]),
            b_x=float(data["b_x"]),
            mu_x=_list_to_arr(data["mu_x"]),
            sigma_x=_list_to_arr(data["sigma_x"]),
            w_y=_list_to_arr(data["w_y"]),
            b_y=float(data["b_y"]),
            mu_y=_list_to_arr(data["mu_y"]),
            sigma_y=_list_to_arr(data["sigma_y"]),
            alpha=alpha,
            train_u_l=u_l,
            train_u_r=u_r,
            train_v_l=v_l,
            train_v_r=v_r,
            train_Y=y,
            clip_bounds=clip_bounds,
        )
    elif mtype == "pca4_decoupled_split":
        model = Pca4DecoupledSplitMapper(
            w_x=_list_to_arr(data["w_x"]),
            b_x=float(data["b_x"]),
            mu_x=_list_to_arr(data["mu_x"]),
            sigma_x=_list_to_arr(data["sigma_x"]),
            w_y=_list_to_arr(data["w_y"]),
            b_y=float(data["b_y"]),
            mu_y=_list_to_arr(data["mu_y"]),
            sigma_y=_list_to_arr(data["sigma_y"]),
            beta_v_l=_list_to_arr(data["beta_v_l"]),
            beta_v_r=_list_to_arr(data["beta_v_r"]),
            alpha=alpha,
            train_u_l=u_l,
            train_u_r=u_r,
            train_v_l=v_l,
            train_v_r=v_r,
            train_Y=y,
            clip_bounds=clip_bounds,
        )
    elif mtype == "poly12_ridge":
        w_shape = tuple(int(x) for x in data.get("w_shape", [12, 2]))
        model = Poly12RidgeMapper(
            w=_list_to_arr(data["w"]).reshape(w_shape),
            intercept=_list_to_arr(data["intercept"]),
            mu=_list_to_arr(data["mu"]),
            sigma=_list_to_arr(data["sigma"]),
            alpha=alpha,
            train_u_l=u_l,
            train_u_r=u_r,
            train_v_l=v_l,
            train_v_r=v_r,
            train_Y=y,
            clip_bounds=clip_bounds,
        )
    elif mtype in ("poly12_ridge_split", "poly12_ridge_split_decoupled_y"):
        beta_l = data.get("beta_v_l")
        beta_r = data.get("beta_v_r")
        model = Poly12RidgeSplitMapper(
            w_x=_list_to_arr(data["w_x"]),
            b_x=float(data["b_x"]),
            mu_x=_list_to_arr(data["mu_x"]),
            sigma_x=_list_to_arr(data["sigma_x"]),
            w_y=_list_to_arr(data["w_y"]),
            b_y=float(data["b_y"]),
            mu_y=_list_to_arr(data["mu_y"]),
            sigma_y=_list_to_arr(data["sigma_y"]),
            y_feature_mode=str(data.get("y_feature_mode", "poly12")),
            beta_v_l=_list_to_arr(beta_l) if beta_l is not None else None,
            beta_v_r=_list_to_arr(beta_r) if beta_r is not None else None,
            alpha=alpha,
            train_u_l=u_l,
            train_u_r=u_r,
            train_v_l=v_l,
            train_v_r=v_r,
            train_Y=y,
            clip_bounds=clip_bounds,
        )

    if model is None:
        print(f"[calib2] unknown mapper_type in calibration_v2.json: {mtype}")
        return None
    return _apply_wrappers_from_dict(model, data)


class MapperStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or DEFAULT_CALIBRATION_V2_PATH

    def exists(self) -> bool:
        return self.path.is_file()

    def save(
        self,
        model: RidgeCalibrationMapper,
        *,
        calibration_mode: str,
        mapper_mode: str,
    ) -> bool:
        try:
            payload = mapper_to_dict(
                model,
                calibration_mode=calibration_mode,
                mapper_mode=mapper_mode,
            )
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            print(f"[calib2] saved v2 mapper to {self.path}")
            return True
        except (OSError, TypeError, ValueError) as e:
            print(f"[calib2] failed to save v2 mapper: {e}")
            return False

    def load(self) -> Optional[Tuple[RidgeCalibrationMapper, str, str]]:
        """Return (model, calibration_mode, mapper_mode) or None."""
        if not self.exists():
            return None
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"[calib2] failed to load v2 mapper: {e}")
            return None
        model = mapper_from_dict(data)
        if model is None:
            return None
        mode = str(data.get("calibration_mode", "keyboard9"))
        mapper_mode = str(data.get("mapper_mode", mode))
        return model, mode, mapper_mode
