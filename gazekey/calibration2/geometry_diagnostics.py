"""Per-target geometric diagnostics after calibration fit."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration2.region_quality import (
    nearest_target_index,
    parse_target_region,
)
from gazekey.calibration2.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow


def _nearest_key(
    px: float,
    py: float,
    keys: Sequence[KeyGeometryRow],
) -> Optional[KeyGeometryRow]:
    if not keys:
        return None
    best: Optional[KeyGeometryRow] = None
    best_d = float("inf")
    for k in keys:
        cx, cy = k.center
        d = float(np.hypot(px - cx, py - cy))
        if d < best_d:
            best_d = d
            best = k
    return best


def _region_str(t: CalibrationTarget) -> str:
    if t.grid_row >= 0 and t.grid_col >= 0:
        return f"r{t.grid_row}/c{t.grid_col}"
    reg = parse_target_region(t.label)
    return f"{reg.row}/{reg.col}"


def print_geometric_diagnostics(
    *,
    model,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
    loocv_detail: Optional[Sequence[dict]],
    keys: Optional[Sequence[KeyGeometryRow]] = None,
) -> None:
    """Log train + LOOCV row/col, nearest key, and dx/dy per calibration target."""
    loocv_by_i = {}
    if loocv_detail:
        for d in loocv_detail:
            loocv_by_i[int(d["i"])] = d

    print("[calib2] --- geometric diagnostics (train) ---")
    for i, (feat, (tx, ty)) in enumerate(samples):
        if i >= len(targets):
            break
        t = targets[i]
        pred = model.predict(feat)
        exp_reg = _region_str(t)
        if pred is None:
            print(f"[calib2] train {t.target_id} {t.label}: predict=None expect={exp_reg}")
            continue
        px, py = float(pred.x), float(pred.y)
        dx, dy = px - float(tx), py - float(ty)
        pred_i = nearest_target_index(px, py, targets)
        pred_t = targets[pred_i]
        pred_reg = _region_str(pred_t)
        nk = _nearest_key(px, py, keys) if keys else None
        key_s = f"{nk.key_label}@{nk.row_index}" if nk is not None else "?"
        status = "OK" if exp_reg == pred_reg else "WRONG"
        print(
            f"[calib2] train {t.target_id} {t.label}: "
            f"expect={exp_reg} pred={pred_reg} {status} "
            f"nearest_key={key_s} "
            f"dx={dx:+.1f} dy={dy:+.1f} err={float(np.hypot(dx, dy)):.1f}px"
        )

    if not loocv_detail:
        return

    print("[calib2] --- geometric diagnostics (LOOCV) ---")
    for d in loocv_detail:
        i = int(d["i"])
        if i >= len(targets) or i >= len(samples):
            continue
        t = targets[i]
        tx, ty = samples[i][1]
        px, py = float(d["pred_x"]), float(d["pred_y"])
        dx, dy = px - float(tx), py - float(ty)
        pred_i = nearest_target_index(px, py, targets)
        pred_t = targets[pred_i]
        exp_reg = _region_str(t)
        pred_reg = _region_str(pred_t)
        nk = _nearest_key(px, py, keys) if keys else None
        key_s = f"{nk.key_label}@{nk.row_index}" if nk is not None else "?"
        status = "OK" if exp_reg == pred_reg else "WRONG"
        print(
            f"[calib2] loocv {t.target_id} {t.label}: "
            f"expect={exp_reg} pred={pred_reg} {status} "
            f"nearest_key={key_s} "
            f"dx={dx:+.1f} dy={dy:+.1f} err={float(d['err']):.1f}px"
        )
