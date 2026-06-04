"""Remove horizontal–vertical coupling in per-eye gaze features.

Eye-local ``v`` is computed from a corner-aligned basis; when the iris moves
horizontally, projection onto the eyelid-normal axis changes even if vertical
gaze is fixed. We residualize each eye's ``v`` on ``[1, uL, uR]`` using
calibration statistics, then map screen Y from decoupled vertical features only.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np


def _augment_u(u_l: np.ndarray, u_r: np.ndarray) -> np.ndarray:
    """Design matrix [1, uL, uR] for n samples."""
    n = int(u_l.shape[0])
    return np.column_stack([np.ones(n, dtype=np.float64), u_l, u_r])


def fit_v_residualizers(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fit vL ~ [1,uL,uR] and vR ~ [1,uL,uR].

    Returns (beta_l, beta_r) each shape (3,).
    """
    u_l = np.asarray(u_l, dtype=np.float64).reshape(-1)
    u_r = np.asarray(u_r, dtype=np.float64).reshape(-1)
    v_l = np.asarray(v_l, dtype=np.float64).reshape(-1)
    v_r = np.asarray(v_r, dtype=np.float64).reshape(-1)
    u = _augment_u(u_l, u_r)
    beta_l, _, _, _ = np.linalg.lstsq(u, v_l, rcond=None)
    beta_r, _, _, _ = np.linalg.lstsq(u, v_r, rcond=None)
    return np.asarray(beta_l, dtype=np.float64), np.asarray(beta_r, dtype=np.float64)


def apply_v_residualizers(
    u_l: float,
    u_r: float,
    v_l: float,
    v_r: float,
    *,
    beta_l: np.ndarray,
    beta_r: np.ndarray,
) -> Tuple[float, float]:
    """Return (vL_res, vR_res) for one frame."""
    x = np.array([1.0, float(u_l), float(u_r)], dtype=np.float64)
    vl_res = float(v_l) - float(x @ beta_l)
    vr_res = float(v_r) - float(x @ beta_r)
    return vl_res, vr_res


def apply_v_residualizers_batch(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    *,
    beta_l: np.ndarray,
    beta_r: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    u = _augment_u(u_l, u_r)
    vl_res = v_l - (u @ beta_l)
    vr_res = v_r - (u @ beta_r)
    return np.asarray(vl_res, dtype=np.float64), np.asarray(vr_res, dtype=np.float64)


def coupling_report(
    u_l: np.ndarray,
    u_r: np.ndarray,
    v_l: np.ndarray,
    v_r: np.ndarray,
    *,
    beta_l: Optional[np.ndarray] = None,
    beta_r: Optional[np.ndarray] = None,
) -> None:
    """Log correlations showing u–v coupling before/after residualization."""
    u_l = np.asarray(u_l, dtype=np.float64).reshape(-1)
    u_r = np.asarray(u_r, dtype=np.float64).reshape(-1)
    v_l = np.asarray(v_l, dtype=np.float64).reshape(-1)
    v_r = np.asarray(v_r, dtype=np.float64).reshape(-1)
    u_mean = 0.5 * (u_l + u_r)

    def corr(a: np.ndarray, b: np.ndarray) -> float:
        if a.size < 2 or float(np.std(a)) < 1e-9 or float(np.std(b)) < 1e-9:
            return float("nan")
        return float(np.corrcoef(a, b)[0, 1])

    print("[calib2] --- u–v coupling (horizontal vs vertical features) ---")
    print(
        f"[calib2] raw corr(vL,uL)={corr(v_l, u_l):.3f} corr(vL,uR)={corr(v_l, u_r):.3f} "
        f"corr(vR,uR)={corr(v_r, u_r):.3f} corr(vR,uL)={corr(v_r, u_l):.3f}"
    )
    print(
        f"[calib2] raw corr(v_mean,u_mean)={corr(0.5 * (v_l + v_r), u_mean):.3f} "
        f"(high |r| => vertical conflated with horizontal)"
    )
    if beta_l is not None and beta_r is not None:
        vl_r, vr_r = apply_v_residualizers_batch(u_l, u_r, v_l, v_r, beta_l=beta_l, beta_r=beta_r)
        print(
            f"[calib2] decoupled corr(vL_res,u_mean)={corr(vl_r, u_mean):.3f} "
            f"corr(vR_res,u_mean)={corr(vr_r, u_mean):.3f}"
        )
