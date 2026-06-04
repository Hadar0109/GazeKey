"""Calibration target region checks (keyboard 9-point grid)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration2.targets import CalibrationTarget, calibration_row_groups
from gazekey.features.feature_types import FrameFeatures


@dataclass(frozen=True)
class TargetRegion:
    row: str  # top | mid | bottom
    col: str  # left | center | right
    label: str


@dataclass
class RegionCheckRow:
    target_id: str
    label: str
    expected: TargetRegion
    predicted: TargetRegion
    px: float
    py: float
    tx: float
    ty: float
    err_px: float
    region_ok: bool
    pixel_ok: bool


@dataclass
class RegionGateResult:
    train_checks: List[RegionCheckRow] = field(default_factory=list)
    loocv_checks: List[RegionCheckRow] = field(default_factory=list)
    train_region_wrong: int = 0
    loocv_region_wrong: int = 0
    train_pixel_fail: int = 0
    loocv_pixel_fail: int = 0
    worst_train_label: str = ""
    worst_train_err_px: float = 0.0
    worst_loocv_label: str = ""
    worst_loocv_err_px: float = 0.0
    hard_fail_reasons: List[str] = field(default_factory=list)
    pixel_warnings: List[str] = field(default_factory=list)
    passed: bool = True


def parse_target_region(label: str, *, grid_row: int = -1, grid_col: int = -1) -> TargetRegion:
    if grid_row >= 0 and grid_col >= 0:
        row_names = ("top", "mid", "bottom")
        col_names = ("left", "center", "right")
        row = row_names[min(grid_row, 2)]
        col = col_names[min(grid_col, 2)]
        return TargetRegion(row=row, col=col, label=str(label))

    lab = str(label).lower().strip()
    if "top" in lab or lab.startswith("row0"):
        row = "top"
    elif "bottom" in lab or lab.startswith("row2"):
        row = "bottom"
    else:
        row = "mid"
    if "left" in lab or lab.endswith("_left"):
        col = "left"
    elif "right" in lab or lab.endswith("_right"):
        col = "right"
    else:
        col = "center"
    return TargetRegion(row=row, col=col, label=str(label))


def _region_match(expected: TargetRegion, predicted: TargetRegion) -> bool:
    return expected.row == predicted.row and expected.col == predicted.col


def region_gate_limits(
    targets: Sequence[CalibrationTarget],
    *,
    calibration_mode: str = "keyboard9",
) -> Tuple[int, int, int]:
    """
    Return (n_graded, max_train_region_wrong, max_loocv_region_wrong).

    Graded targets have grid_row/grid_col (excludes row-gap anchors).
    Limits scale with point count for dense keyboard15 layouts.
    """
    keyboard = str(calibration_mode).lower().startswith("keyboard")
    n_graded = sum(
        1 for t in targets if int(getattr(t, "grid_row", -1)) >= 0 and int(getattr(t, "grid_col", -1)) >= 0
    )
    if not keyboard or n_graded < 5:
        return n_graded, 0, 1
    # ~1 allowed LOOCV region miss per 5 graded keys; at least 2 for 13+ point layouts.
    max_loocv = max(2, int(n_graded) // 5)
    # Train fit can miss slightly on dense grids; still require majority correct.
    max_train = max(1, int(n_graded) // 8)
    return n_graded, max_train, max_loocv


def _is_graded_target(t: CalibrationTarget) -> bool:
    return int(getattr(t, "grid_row", -1)) >= 0 and int(getattr(t, "grid_col", -1)) >= 0


def nearest_target_index(px: float, py: float, targets: Sequence[CalibrationTarget]) -> int:
    best_i = 0
    best_d = float("inf")
    for i, t in enumerate(targets):
        d = float(np.hypot(px - float(t.screen_x), py - float(t.screen_y)))
        if d < best_d:
            best_d = d
            best_i = i
    return best_i


def _check_one(
    *,
    i: int,
    px: float,
    py: float,
    tx: float,
    ty: float,
    targets: Sequence[CalibrationTarget],
    half_key_height_px: float,
) -> RegionCheckRow:
    label = targets[i].label if i < len(targets) else f"T{i+1:02d}"
    tid = targets[i].target_id if i < len(targets) else f"T{i+1:02d}"
    t_i = targets[i] if i < len(targets) else None
    expected = parse_target_region(
        label,
        grid_row=int(t_i.grid_row) if t_i is not None else -1,
        grid_col=int(t_i.grid_col) if t_i is not None else -1,
    )
    pred_i = nearest_target_index(px, py, targets)
    t_pred = targets[pred_i]
    predicted = parse_target_region(
        t_pred.label,
        grid_row=int(t_pred.grid_row),
        grid_col=int(t_pred.grid_col),
    )
    err = float(np.hypot(px - tx, py - ty))
    region_ok = _region_match(expected, predicted)
    pixel_ok = err <= float(half_key_height_px)
    return RegionCheckRow(
        target_id=tid,
        label=label,
        expected=expected,
        predicted=predicted,
        px=px,
        py=py,
        tx=tx,
        ty=ty,
        err_px=err,
        region_ok=region_ok,
        pixel_ok=pixel_ok,
    )


def assess_region_gates(
    *,
    model,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
    loocv_detail: Optional[Sequence[dict]],
    keyboard_mode: bool,
    half_key_height_px: float = 34.0,
    max_loocv_region_wrong: Optional[int] = None,
    max_train_region_wrong: Optional[int] = None,
    calibration_mode: str = "keyboard9",
    verbose: bool = True,
) -> RegionGateResult:
    """Train + LOOCV region accuracy; keyboard mode uses region as primary gate."""
    out = RegionGateResult()
    if not keyboard_mode:
        out.passed = True
        return out

    _n_graded, default_max_train, default_max_loocv = region_gate_limits(
        targets, calibration_mode=calibration_mode
    )
    if max_loocv_region_wrong is None:
        max_loocv_region_wrong = default_max_loocv
    if max_train_region_wrong is None:
        max_train_region_wrong = default_max_train

    if verbose:
        print(
            f"[calib2] region gate limits: graded={_n_graded} "
            f"max_train_wrong={max_train_region_wrong} max_loocv_wrong={max_loocv_region_wrong}"
        )
        print("[calib2] --- calibration target region check (train) ---")
    for i, (feat, (tx, ty)) in enumerate(samples):
        if i >= len(targets) or not _is_graded_target(targets[i]):
            continue
        pred = model.predict(feat)
        if pred is None:
            out.hard_fail_reasons.append(f"{targets[i].label}: predict None")
            continue
        row = _check_one(
            i=i,
            px=float(pred.x),
            py=float(pred.y),
            tx=float(tx),
            ty=float(ty),
            targets=targets,
            half_key_height_px=half_key_height_px,
        )
        out.train_checks.append(row)
        if not row.region_ok:
            out.train_region_wrong += 1
        if not row.pixel_ok:
            out.train_pixel_fail += 1
        if row.err_px >= out.worst_train_err_px:
            out.worst_train_err_px = row.err_px
            out.worst_train_label = row.label
        status = "OK" if row.region_ok else "WRONG_REGION"
        if verbose:
            print(
                f"[calib2] train {row.target_id} {row.label}: "
                f"expect={row.expected.row}/{row.expected.col} "
                f"pred={row.predicted.row}/{row.predicted.col} "
                f"err={row.err_px:.1f}px {status}"
            )

    if loocv_detail:
        if verbose:
            print("[calib2] --- calibration target region check (LOOCV) ---")
        for d in loocv_detail:
            i = int(d["i"])
            if i >= len(targets) or i >= len(samples) or not _is_graded_target(targets[i]):
                continue
            tx, ty = samples[i][1]
            row = _check_one(
                i=i,
                px=float(d["pred_x"]),
                py=float(d["pred_y"]),
                tx=float(tx),
                ty=float(ty),
                targets=targets,
                half_key_height_px=half_key_height_px,
            )
            out.loocv_checks.append(row)
            if not row.region_ok:
                out.loocv_region_wrong += 1
            if not row.pixel_ok:
                out.loocv_pixel_fail += 1
            if row.err_px >= out.worst_loocv_err_px:
                out.worst_loocv_err_px = row.err_px
                out.worst_loocv_label = row.label
            status = "OK" if row.region_ok else "WRONG_REGION"
            if verbose:
                print(
                    f"[calib2] loocv {row.target_id} {row.label}: "
                    f"expect={row.expected.row}/{row.expected.col} "
                    f"pred={row.predicted.row}/{row.predicted.col} "
                    f"err={row.err_px:.1f}px {status}"
                )

    if verbose:
        if out.worst_train_label:
            print(
                f"[calib2] worst train: {out.worst_train_label} err={out.worst_train_err_px:.1f}px"
            )
        if out.worst_loocv_label:
            print(
                f"[calib2] worst LOOCV: {out.worst_loocv_label} err={out.worst_loocv_err_px:.1f}px"
            )

    if out.train_region_wrong > int(max_train_region_wrong):
        out.hard_fail_reasons.append(
            f"train region wrong on {out.train_region_wrong} target(s) "
            f"(allowed {max_train_region_wrong})"
        )
    if out.loocv_region_wrong > int(max_loocv_region_wrong):
        out.hard_fail_reasons.append(
            f"LOOCV region wrong on {out.loocv_region_wrong} target(s) "
            f"(allowed {max_loocv_region_wrong})"
        )

    out.passed = len(out.hard_fail_reasons) == 0
    return out


def compute_row_y_residuals(
    *,
    model,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Mean (pred_y - target_y) per calibration row and row Y centers for assignment.

    Returns (row_y_centers top/mid/bottom, row_y_bias top/mid/bottom).
    Bias is subtracted at predict time to correct systematic row error.
    """
    top_i, mid_i, bot_i = calibration_row_groups(targets)
    groups = [("top", top_i), ("mid", mid_i), ("bottom", bot_i)]
    centers: List[float] = []
    biases: List[float] = []
    print("[calib2] --- row-level Y residuals (train, before bias correction) ---")
    for row_name, indices in groups:
        ys: List[float] = []
        res: List[float] = []
        for i in indices:
            if i >= len(targets) or i >= len(samples):
                continue
            feat, (_tx, ty) = samples[i]
            pred = model.predict(feat)
            if pred is None:
                continue
            ys.append(float(ty))
            res.append(float(pred.y) - float(ty))
        cy = float(np.mean(ys)) if ys else 0.0
        bias = float(np.mean(res)) if res else 0.0
        centers.append(cy)
        biases.append(bias)
        print(
            f"[calib2] row {row_name}: n={len(res)} mean_target_y={cy:.1f} "
            f"mean_residual_dy={bias:+.1f}px"
        )
    return (float(centers[0]), float(centers[1]), float(centers[2])), (
        float(biases[0]),
        float(biases[1]),
        float(biases[2]),
    )


def raw_v_mean_u_corr(samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]]) -> float:
    u_m: List[float] = []
    v_m: List[float] = []
    for f, _ in samples:
        if f.pca_uL is None or f.pca_vL is None or f.pca_uR is None or f.pca_vR is None:
            continue
        u_m.append(0.5 * (float(f.pca_uL) + float(f.pca_uR)))
        v_m.append(0.5 * (float(f.pca_vL) + float(f.pca_vR)))
    if len(u_m) < 3:
        return 0.0
    u = np.array(u_m, dtype=np.float64)
    v = np.array(v_m, dtype=np.float64)
    if float(np.std(u)) < 1e-9 or float(np.std(v)) < 1e-9:
        return 0.0
    return float(np.corrcoef(u, v)[0, 1])
