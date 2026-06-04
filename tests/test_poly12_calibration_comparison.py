"""Compare poly12_ridge vs poly12_ridge_split_decoupled_y on the same calibration data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pytest

from gazekey.calibration2.region_quality import (
    assess_region_gates,
    nearest_target_index,
    parse_target_region,
)
from gazekey.calibration2.targets import CalibrationTarget
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.ridge import (
    _fit_poly12_joint,
    _fit_poly12_split,
    _keyboard_assessment_model,
    _loocv_from_detail,
    _train_rms_px,
)

ROOT = Path(__file__).resolve().parents[1]
CALIB_JSON = ROOT / "calibration_v2.json"
COMPARE_ALPHA = 10.0

# keyboard15 target order (matches calibration_debug.csv / mapper_store train_Y layout).
KEYBOARD15_META: Tuple[Tuple[str, int, int], ...] = (
    ("row0_left", 0, 0),
    ("row0_center", 0, 1),
    ("row0_right", 0, 2),
    ("row1_left", 1, 0),
    ("row1_center", 1, 1),
    ("row1_right", 1, 2),
    ("row2_left", 2, 0),
    ("row2_center", 2, 1),
    ("row2_right", 2, 2),
    ("gap_0_1", -1, 1),
    ("gap_1_2", -1, 1),
    ("row0_x28", 0, 1),
    ("row0_x72", 0, 1),
    ("row2_x28", 2, 1),
    ("row2_x72", 2, 1),
)

CORNER_LABELS = frozenset({"row0_left", "row0_right", "row2_left", "row2_right"})
CENTER_LABELS = frozenset({"row0_center", "row1_center", "row2_center"})


@dataclass(frozen=True)
class TargetMetrics:
    label: str
    train_px: float
    loocv_px: float
    region_ok: bool
    pred_x: float
    pred_y: float
    target_x: float
    target_y: float
    nearest_label: str


@dataclass
class ModelComparison:
    name: str
    core_train_rms: float
    core_loocv_rms: float
    core_worst_loocv: float
    wrap_train_rms: float
    wrap_loocv_rms: float
    region_train_wrong: int
    region_loocv_wrong: int
    per_target: List[TargetMetrics]
    corner_loocv_mean: float
    corner_loocv_max: float
    center_loocv_mean: float


def _load_calibration_bundle(path: Path = CALIB_JSON) -> dict:
    if not path.is_file():
        pytest.skip(f"Missing calibration artifact: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _targets_from_train_y(Y: np.ndarray) -> List[CalibrationTarget]:
    n = Y.shape[0]
    if n != len(KEYBOARD15_META):
        raise ValueError(f"expected {len(KEYBOARD15_META)} targets, got {n}")
    out: List[CalibrationTarget] = []
    for i, (label, grid_row, grid_col) in enumerate(KEYBOARD15_META):
        out.append(
            CalibrationTarget(
                target_id=f"T{i + 1:02d}",
                label=label,
                key_id="",
                screen_x=float(Y[i, 0]),
                screen_y=float(Y[i, 1]),
                grid_row=int(grid_row),
                grid_col=int(grid_col),
            )
        )
    return out


def _samples_from_bundle(data: dict) -> Tuple[List[Tuple[FrameFeatures, Tuple[float, float]]], np.ndarray]:
    n = int(data["train_n"])
    Y = np.array(data["train_Y"], dtype=np.float64).reshape(n, 2)
    u_l = np.array(data["train_u_l"], dtype=np.float64)
    u_r = np.array(data["train_u_r"], dtype=np.float64)
    v_l = np.array(data["train_v_l"], dtype=np.float64)
    v_r = np.array(data["train_v_r"], dtype=np.float64)
    samples: List[Tuple[FrameFeatures, Tuple[float, float]]] = []
    for i in range(n):
        feat = FrameFeatures(
            timestamp_ms=0,
            face_detected=True,
            blink=False,
            confidence=1.0,
            Lh=0.5 + float(u_l[i]),
            Lv=0.5 + float(v_l[i]),
            Rh=0.5 + float(u_r[i]),
            Rv=0.5 + float(v_r[i]),
            avg_h=0.5 + 0.5 * (float(u_l[i]) + float(u_r[i])),
            avg_v=0.5 + 0.5 * (float(v_l[i]) + float(v_r[i])),
            eye_box_w=None,
            eye_box_h=None,
            face_x=None,
            face_y=None,
            pca_uL=float(u_l[i]),
            pca_vL=float(v_l[i]),
            pca_uR=float(u_r[i]),
            pca_vR=float(v_r[i]),
        )
        samples.append((feat, (float(Y[i, 0]), float(Y[i, 1]))))
    return samples, Y


def _region_ok(i: int, px: float, py: float, targets: Sequence[CalibrationTarget]) -> bool:
    t = targets[i]
    if t.grid_row < 0 or t.grid_col < 0:
        return True
    expected = parse_target_region(t.label, grid_row=t.grid_row, grid_col=t.grid_col)
    pred_i = nearest_target_index(px, py, targets)
    pred_t = targets[pred_i]
    predicted = parse_target_region(
        pred_t.label,
        grid_row=int(pred_t.grid_row),
        grid_col=int(pred_t.grid_col),
    )
    return expected.row == predicted.row and expected.col == predicted.col


def assess_model(
    name: str,
    core,
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
    clip_bounds: Tuple[float, float, float, float],
) -> ModelComparison:
    wrapped = _keyboard_assessment_model(
        core, samples=samples, targets=targets, verbose=False
    )
    loocv_core = core.leave_one_out_detail_px()
    loocv_wrap = wrapped.leave_one_out_detail_px()
    core_loocv_rms, core_worst = _loocv_from_detail(loocv_core)
    wrap_loocv_rms, _ = _loocv_from_detail(loocv_wrap)
    region = assess_region_gates(
        model=wrapped,
        samples=samples,
        targets=targets,
        loocv_detail=loocv_wrap,
        keyboard_mode=True,
        calibration_mode="keyboard15",
        verbose=False,
    )

    per_target: List[TargetMetrics] = []
    corner_loocv: List[float] = []
    center_loocv: List[float] = []

    for i, (feat, (tx, ty)) in enumerate(samples):
        label = targets[i].label
        tr = core.predict(feat)
        train_px = float(np.hypot(tr.x - tx, tr.y - ty)) if tr else float("inf")
        ld = loocv_wrap[i]
        loocv_px = float(ld["err"])
        px, py = float(ld["pred_x"]), float(ld["pred_y"])
        pred_i = nearest_target_index(px, py, targets)
        per_target.append(
            TargetMetrics(
                label=label,
                train_px=train_px,
                loocv_px=loocv_px,
                region_ok=_region_ok(i, px, py, targets),
                pred_x=px,
                pred_y=py,
                target_x=float(tx),
                target_y=float(ty),
                nearest_label=targets[pred_i].label,
            )
        )
        if label in CORNER_LABELS:
            corner_loocv.append(loocv_px)
        if label in CENTER_LABELS:
            center_loocv.append(loocv_px)

    return ModelComparison(
        name=name,
        core_train_rms=float(_train_rms_px(core, samples) or 0.0),
        core_loocv_rms=float(core_loocv_rms or 0.0),
        core_worst_loocv=float(core_worst or 0.0),
        wrap_train_rms=float(_train_rms_px(wrapped, samples) or 0.0),
        wrap_loocv_rms=float(wrap_loocv_rms or 0.0),
        region_train_wrong=int(region.train_region_wrong),
        region_loocv_wrong=int(region.loocv_region_wrong),
        per_target=per_target,
        corner_loocv_mean=float(np.mean(corner_loocv)) if corner_loocv else 0.0,
        corner_loocv_max=float(max(corner_loocv)) if corner_loocv else 0.0,
        center_loocv_mean=float(np.mean(center_loocv)) if center_loocv else 0.0,
    )


def fit_poly12_pair(
    data: dict,
    *,
    alpha: float = COMPARE_ALPHA,
) -> Tuple[ModelComparison, ModelComparison]:
    samples, Y = _samples_from_bundle(data)
    targets = _targets_from_train_y(Y)
    bounds = tuple(float(x) for x in data["clip_bounds"])
    u_l = np.array(data["train_u_l"], dtype=np.float64)
    u_r = np.array(data["train_u_r"], dtype=np.float64)
    v_l = np.array(data["train_v_l"], dtype=np.float64)
    v_r = np.array(data["train_v_r"], dtype=np.float64)

    joint = _fit_poly12_joint(u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=bounds)
    split = _fit_poly12_split(
        u_l, u_r, v_l, v_r, Y, alpha=alpha, y_mode="decoupled_v", clip_bounds=bounds
    )
    return (
        assess_model("poly12_ridge", joint, samples=samples, targets=targets, clip_bounds=bounds),
        assess_model(
            "poly12_ridge_split_decoupled_y",
            split,
            samples=samples,
            targets=targets,
            clip_bounds=bounds,
        ),
    )


def _print_comparison(joint: ModelComparison, split: ModelComparison) -> None:
    print("\n=== poly12 @ alpha={:.1f} - summary (same calibration_v2.json) ===".format(COMPARE_ALPHA))
    print(
        f"{'metric':<32} {'poly12_ridge':>14} {'split_decoupled_y':>18} {'better':>10}"
    )
    rows = [
        ("core train RMS px", joint.core_train_rms, split.core_train_rms, True),
        ("core LOOCV RMS px", joint.core_loocv_rms, split.core_loocv_rms, True),
        ("core worst LOOCV px", joint.core_worst_loocv, split.core_worst_loocv, True),
        ("runtime wrap train RMS", joint.wrap_train_rms, split.wrap_train_rms, True),
        ("runtime wrap LOOCV RMS", joint.wrap_loocv_rms, split.wrap_loocv_rms, True),
        ("region train wrong", float(joint.region_train_wrong), float(split.region_train_wrong), False),
        ("region LOOCV wrong", float(joint.region_loocv_wrong), float(split.region_loocv_wrong), False),
        ("corner LOOCV mean", joint.corner_loocv_mean, split.corner_loocv_mean, True),
        ("corner LOOCV max", joint.corner_loocv_max, split.corner_loocv_max, True),
        ("center LOOCV mean", joint.center_loocv_mean, split.center_loocv_mean, True),
    ]
    for name, a, b, lower_is_better in rows:
        if abs(a - b) < 0.05:
            better = "tie"
        elif lower_is_better:
            better = "joint" if a < b else "split"
        else:
            better = "joint" if a < b else "split"
        print(f"{name:<32} {a:14.1f} {b:18.1f} {better:>10}")

    print("\n=== per-target (runtime wrapped LOOCV + predict) ===")
    print(
        f"{'label':<14} {'joint_tr':>7} {'split_tr':>7} {'joint_lo':>8} {'split_lo':>8} "
        f"{'j_reg':>5} {'s_reg':>5} {'joint_xy':>16} {'split_xy':>16}"
    )
    for jm, sm in zip(joint.per_target, split.per_target):
        assert jm.label == sm.label
        jxy = f"({jm.pred_x:.0f},{jm.pred_y:.0f})"
        sxy = f"({sm.pred_x:.0f},{sm.pred_y:.0f})"
        print(
            f"{jm.label:<14} {jm.train_px:7.1f} {sm.train_px:7.1f} "
            f"{jm.loocv_px:8.1f} {sm.loocv_px:8.1f} "
            f"{'OK' if jm.region_ok else 'BAD':>5} {'OK' if sm.region_ok else 'BAD':>5} "
            f"{jxy:>16} {sxy:>16}"
        )


def test_poly12_joint_vs_split_decoupled_same_calibration(capsys: pytest.CaptureFixture[str]) -> None:
    """Fit both poly12 variants at alpha=10 on calibration_v2.json and compare metrics."""
    data = _load_calibration_bundle()
    joint, split = fit_poly12_pair(data, alpha=COMPARE_ALPHA)
    _print_comparison(joint, split)

    # Sanity: finite errors on all targets.
    for model in (joint, split):
        for row in model.per_target:
            assert np.isfinite(row.train_px) and np.isfinite(row.loocv_px)
            assert np.isfinite(row.pred_x) and np.isfinite(row.pred_y)

    # Document selection-relevant core LOOCV ordering for this fixture.
    assert joint.core_loocv_rms > 0.0 and split.core_loocv_rms > 0.0

    # Runtime predictions must differ somewhere (different mappers).
    diffs = [
        np.hypot(j.pred_x - s.pred_x, j.pred_y - s.pred_y)
        for j, s in zip(joint.per_target, split.per_target)
    ]
    assert max(diffs) > 1.0

    out = capsys.readouterr().out
    assert "poly12 @ alpha=10.0" in out
    assert "row2_right" in out


def test_poly12_comparison_corner_and_center_breakouts() -> None:
    """Structured corner/center aggregates for programmatic checks."""
    data = _load_calibration_bundle()
    joint, split = fit_poly12_pair(data, alpha=COMPARE_ALPHA)

    by_label_j = {r.label: r for r in joint.per_target}
    by_label_s = {r.label: r for r in split.per_target}

    for lab in CORNER_LABELS:
        assert lab in by_label_j and lab in by_label_s
        # LOOCV corner errors are logged in metrics objects.
        assert by_label_j[lab].loocv_px >= 0.0
        assert by_label_s[lab].loocv_px >= 0.0

    # Region wrong counts match manual recount on graded LOOCV rows.
    graded_loocv_region_wrong = lambda m: sum(
        1
        for r in m.per_target
        if r.label in {t[0] for t in KEYBOARD15_META if t[1] >= 0}
        and not r.region_ok
    )
    assert joint.region_loocv_wrong == graded_loocv_region_wrong(joint)
    assert split.region_loocv_wrong == graded_loocv_region_wrong(split)
