"""Polynomial gaze features for ridge mappers (handles u–v coupling)."""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures


def poly12_from_uv(
    u_l: np.ndarray,
    v_l: np.ndarray,
    u_r: np.ndarray,
    v_r: np.ndarray,
) -> np.ndarray:
    """
    Build 12D features per sample:
    [uL, vL, uR, vR, uL^2, vL^2, uR^2, vR^2, uL*vL, uR*vR, uL*uR, vL*vR]
    """
    u_l = np.asarray(u_l, dtype=np.float64).reshape(-1)
    v_l = np.asarray(v_l, dtype=np.float64).reshape(-1)
    u_r = np.asarray(u_r, dtype=np.float64).reshape(-1)
    v_r = np.asarray(v_r, dtype=np.float64).reshape(-1)
    n = u_l.shape[0]
    return np.column_stack(
        [
            u_l,
            v_l,
            u_r,
            v_r,
            u_l * u_l,
            v_l * v_l,
            u_r * u_r,
            v_r * v_r,
            u_l * v_l,
            u_r * v_r,
            u_l * u_r,
            v_l * v_r,
        ]
    )


def poly12_from_frame(features: FrameFeatures) -> Optional[np.ndarray]:
    u_l, v_l, u_r, v_r = features.pca_uL, features.pca_vL, features.pca_uR, features.pca_vR
    if u_l is None or v_l is None or u_r is None or v_r is None:
        return None
    return poly12_from_uv(
        np.array([float(u_l)]),
        np.array([float(v_l)]),
        np.array([float(u_r)]),
        np.array([float(v_r)]),
    ).reshape(-1)


def poly12_feature_names() -> Tuple[str, ...]:
    return (
        "uL",
        "vL",
        "uR",
        "vR",
        "uL^2",
        "vL^2",
        "uR^2",
        "vR^2",
        "uL*vL",
        "uR*vR",
        "uL*uR",
        "vL*vR",
    )


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
