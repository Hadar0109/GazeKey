"""Peer outlier checks for per-target calibration means (same row / column)."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures


def _row_column_peers(targets: Sequence[CalibrationTarget], idx: int) -> Tuple[List[int], List[int]]:
    """Return (row_peer_indices, col_peer_indices) excluding idx."""
    if idx < 0 or idx >= len(targets):
        return [], []
    t = targets[idx]
    lab = str(t.label).lower()
    row_peers: List[int] = []
    col_peers: List[int] = []
    for j, other in enumerate(targets):
        if j == idx:
            continue
        olab = str(other.label).lower()
        same_row = (
            ("top" in lab and "top" in olab)
            or ("bottom" in lab and "bottom" in olab)
            or (lab in {"left", "center", "right"} and olab in {"left", "center", "right"})
            or ("middle" in lab and "middle" in olab)
        )
        same_col = (
            ("left" in lab and "left" in olab)
            or ("right" in lab and "right" in olab)
            or (lab in {"top", "center", "bottom"} and olab in {"top", "center", "bottom"})
        )
        if same_row:
            row_peers.append(j)
        if same_col:
            col_peers.append(j)
    return row_peers, col_peers


def _pca_v_mean(f: FrameFeatures) -> Optional[float]:
    if f.pca_vL is None or f.pca_vR is None:
        return None
    return 0.5 * (float(f.pca_vL) + float(f.pca_vR))


def _pca_u_mean(f: FrameFeatures) -> Optional[float]:
    if f.pca_uL is None or f.pca_uR is None:
        return None
    return 0.5 * (float(f.pca_uL) + float(f.pca_uR))


def check_target_mean_outlier(
    *,
    idx: int,
    feature: FrameFeatures,
    targets: Sequence[CalibrationTarget],
    peer_features: Sequence[Optional[FrameFeatures]],
    min_row_peers: int = 2,
    row_residual_threshold: float = 0.10,
    col_u_residual_threshold: float = 0.12,
) -> Optional[str]:
    """
    Flag targets whose mean features are inconsistent with row/column peers.

    Same-row targets often have different v at the same screen_y (horizontal coupling).
    We fit v ~ u within the row and flag only large *residuals* (bad collection), not coupling.
    """
    row_peers, col_peers = _row_column_peers(targets, idx)
    v_self = _pca_v_mean(feature)
    u_self = _pca_u_mean(feature)

    if v_self is not None and u_self is not None and len(row_peers) >= min_row_peers:
        us: List[float] = [u_self]
        vs: List[float] = [v_self]
        for j in row_peers:
            pf = peer_features[j] if j < len(peer_features) else None
            if pf is None:
                continue
            u = _pca_u_mean(pf)
            v = _pca_v_mean(pf)
            if u is not None and v is not None:
                us.append(u)
                vs.append(v)
        if len(us) >= min_row_peers + 1:
            u_arr = np.array(us, dtype=np.float64)
            v_arr = np.array(vs, dtype=np.float64)
            if float(np.std(u_arr)) > 1e-5:
                b, a = np.polyfit(u_arr, v_arr, 1)
                pred_v = float(a + b * u_self)
                resid = abs(v_self - pred_v)
                pred_all = a + b * u_arr
                resids = np.abs(v_arr - pred_all)
                scale = float(np.median(resids)) if resids.size else 0.0
                if resid > max(row_residual_threshold, 2.5 * scale + 0.02):
                    label = targets[idx].label if idx < len(targets) else f"T{idx+1:02d}"
                    return (
                        f"{label}: row v~u residual {resid:.4f} "
                        f"(expected v≈{pred_v:.4f} at u={u_self:.4f})"
                    )

    if u_self is not None and len(col_peers) >= min_row_peers:
        us_col: List[float] = [u_self]
        for j in col_peers:
            pf = peer_features[j] if j < len(peer_features) else None
            if pf is None:
                continue
            u = _pca_u_mean(pf)
            if u is not None:
                us_col.append(u)
        if len(us_col) >= min_row_peers + 1:
            u_arr = np.array(us_col, dtype=np.float64)
            med_u = float(np.median(u_arr))
            resid_u = abs(u_self - med_u)
            if resid_u > col_u_residual_threshold:
                label = targets[idx].label if idx < len(targets) else f"T{idx+1:02d}"
                return f"{label}: pca_u={u_self:.4f} deviates {resid_u:.4f} from column median {med_u:.4f}"

    return None
