"""One-off analysis: correction layer contribution from saved session CSVs.

Developer tooling (moved from ``scripts/``). Expects artifact CSVs next to the
repo root working directory (historical layout). Run::

    python tools/debug/analyze_correction_layers.py
"""
from __future__ import annotations

import csv
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class KeySnap:
    label: str
    action: str
    cx: float
    cy: float
    x0: int
    y0: int
    x1: int
    y1: int


def load_keys() -> list[KeySnap]:
    """Load full keyboard layout for hit-test (letters, space, and special keys)."""
    keys: list[KeySnap] = []
    with (ROOT / "keyboard_layout.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            act = r["key_action"]
            keys.append(
                KeySnap(
                    label=r["key_label"],
                    action=act,
                    cx=float(r["center_x"]),
                    cy=float(r["center_y"]),
                    x0=int(r["rect_x"]),
                    y0=int(r["rect_y"]),
                    x1=int(r["rect_x"]) + int(r["rect_w"]),
                    y1=int(r["rect_y"]) + int(r["rect_h"]),
                )
            )
    return keys


def predict_label(keys: list[KeySnap], px: float, py: float) -> str:
    containing = [k for k in keys if k.x0 <= px < k.x1 and k.y0 <= py < k.y1]
    if containing:
        containing.sort(key=lambda k: (k.x1 - k.x0) * (k.y1 - k.y0))
        k = containing[0]
    else:
        k = min(keys, key=lambda kk: math.hypot(px - kk.cx, py - kk.cy))
    if k.action == " ":
        return "Space"
    if len(k.action) == 1:
        return k.action.upper()
    return k.label


def is_correct(target: str, predicted: str) -> bool:
    if target.lower() == "space":
        return predicted == "Space"
    return predicted.upper() == target.upper()


def metrics(
    keys: list[KeySnap],
    targets: list[tuple[str, float, float]],
    px_list: list[float],
    py_list: list[float],
    *,
    clip_x: float,
    clip_y: float,
) -> dict:
    n = len(targets)
    ok = errs = dxs = dys = 0
    clip_x_n = clip_y_n = 0
    per_key = []
    for (tgt, tcx, tcy), px, py in zip(targets, px_list, py_list):
        pred = predict_label(keys, px, py)
        good = is_correct(tgt, pred)
        ok += int(good)
        e = math.hypot(px - tcx, py - tcy)
        errs += e
        dxs += abs(px - tcx)
        dys += abs(py - tcy)
        if abs(py - clip_y) < 0.05:
            clip_y_n += 1
        if abs(px - clip_x) < 0.05:
            clip_x_n += 1
        per_key.append((tgt, pred, good, e, px, py))
    return {
        "acc": 100.0 * ok / n,
        "ok": ok,
        "n": n,
        "mean_err": errs / n,
        "max_err": max(math.hypot(px - tcx, py - tcy) for (_, tcx, tcy), px, py in zip(targets, px_list, py_list)),
        "mean_dx": dxs / n,
        "mean_dy": dys / n,
        "clip_x": clip_x_n,
        "clip_y": clip_y_n,
        "per_key": per_key,
    }


def main() -> None:
    keys = load_keys()
    data = json.loads((ROOT / "calibration_v2.json").read_text(encoding="utf-8"))
    centers = data["row_y_centers"]
    biases = data["row_y_bias"]
    tx = np.asarray(data["local_y_train_x"], dtype=np.float64)
    tdy = np.asarray(data["local_y_train_dy"], dtype=np.float64)
    clip_y = float(data["clip_bounds"][1])
    clip_x = float(data["clip_bounds"][2])

    def undo_row(py_after_row: float) -> float:
        py_core = float(py_after_row)
        for _ in range(12):
            ri = int(np.argmin(np.abs(np.asarray(centers, dtype=np.float64) - py_core)))
            py_next = float(py_after_row) + float(biases[ri])
            if abs(py_next - py_core) < 1e-4:
                return py_next
            py_core = py_next
        return py_core

    def undo_all(px: float, py_final: float) -> tuple[float, float]:
        py_after_row = float(py_final) + float(np.interp(float(px), tx, tdy))
        return undo_row(py_after_row), py_after_row

    debug = list(csv.DictReader((ROOT / "key_accuracy_debug.csv").open(encoding="utf-8")))
    compare = [
        r
        for r in csv.DictReader((ROOT / "key_accuracy_compare.csv").open(encoding="utf-8"))
        if r["mapper_type"] == "poly12_ridge_split_decoupled_y"
    ]
    order = [r["target_key"] for r in debug]
    cmp_by = {r["target_key"]: r for r in compare}
    dbg_by = {r["target_key"]: r for r in debug}

    targets = [
        (k, float(dbg_by[k]["target_center_x"]), float(dbg_by[k]["target_center_y"])) for k in order
    ]
    s3_px = [float(cmp_by[k]["predicted_x"]) for k in order]
    s3_py = [float(cmp_by[k]["predicted_y"]) for k in order]
    s4_px = [float(dbg_by[k]["predicted_x"]) for k in order]
    s4_py = [float(dbg_by[k]["predicted_y"]) for k in order]

    py_core, py_row = [], []
    for px, py in zip(s3_px, s3_py):
        pc, pr = undo_all(px, py)
        py_core.append(pc)
        py_row.append(pr)

    stages = [
        ("1 Raw poly12 (core; inverse from compare replay)", s3_px, py_core),
        ("2 Poly12 + row bias", s3_px, py_row),
        ("3 Poly12 + row + local Y (compare replay, no feature smoother)", s3_px, s3_py),
        ("4 Runtime pipeline (live: feature smoother + mean of preds)", s4_px, s4_py),
    ]

    print("=== Correction layer breakdown (poly12_ridge_split_decoupled_y) ===")
    print("Same calibration + 15-key session (key_accuracy_debug/compare CSVs)")
    print("Stages 1-3: inverse/forward Y chain from compare replay (same gaze features)")
    print("Stage 4: live runtime path")
    print(f"Clip counts: Y={clip_y:.0f}, X={clip_x:.0f}")
    print()

    prev_m = None
    stage_metrics = []
    for name, px_list, py_list in stages:
        m = metrics(keys, targets, px_list, py_list, clip_x=clip_x, clip_y=clip_y)
        stage_metrics.append((name, m))
        print(name)
        print(
            f"  accuracy={m['acc']:.1f}% ({m['ok']}/{m['n']})  "
            f"mean_err={m['mean_err']:.1f}px  max_err={m['max_err']:.1f}px  "
            f"mean|dx|={m['mean_dx']:.1f}  mean|dy|={m['mean_dy']:.1f}  "
            f"clip_y={m['clip_y']}  clip_x={m['clip_x']}"
        )
        if prev_m is not None:
            print(
                f"  delta vs prev: acc {m['acc'] - prev_m['acc']:+.1f}pp  "
                f"mean_err {m['mean_err'] - prev_m['mean_err']:+.1f}px  "
                f"mean|dx| {m['mean_dx'] - prev_m['mean_dx']:+.1f}  "
                f"mean|dy| {m['mean_dy'] - prev_m['mean_dy']:+.1f}  "
                f"clip_y {m['clip_y'] - prev_m['clip_y']:+d}"
            )
        prev_m = m
        print()

    print("=== CSV is_correct (runtime hit-test at session time) ===")
    cmp_ok = sum(1 for r in compare if r["is_correct"] == "1")
    dbg_ok = sum(1 for r in debug if r["is_correct"] == "1")
    print(f"  stage 3 compare CSV: {100*cmp_ok/len(compare):.1f}% ({cmp_ok}/{len(compare)})")
    print(f"  stage 4 debug CSV:   {100*dbg_ok/len(debug):.1f}% ({dbg_ok}/{len(debug)})")
    print()

    m2, m3 = stage_metrics[1][1], stage_metrics[2][1]
    print("=== Keys whose correctness changes: stage 2 -> stage 3 ===")
    for (t2, p2, g2, _, _, _), (t3, p3, g3, _, _, _) in zip(m2["per_key"], m3["per_key"]):
        if g2 != g3:
            print(f"  {t2}: {p2} ({'OK' if g2 else 'miss'}) -> {p3} ({'OK' if g3 else 'miss'})")

    print()
    print("=== Keys whose correctness changes: stage 3 -> stage 4 ===")
    m4 = stage_metrics[3][1]
    for (t3, p3, g3, _, px3, py3), (t4, p4, g4, _, px4, py4) in zip(m3["per_key"], m4["per_key"]):
        if g3 != g4:
            print(
                f"  {t3}: {p3} ({'OK' if g3 else 'miss'}) -> {p4} ({'OK' if g4 else 'miss'}) "
                f"py {py3:.1f}->{py4:.1f}"
            )

    cal = list(csv.DictReader((ROOT / "calibration_debug.csv").open(encoding="utf-8")))
    if cal:
        errs = [float(r["loocv_error_px"]) for r in cal if r.get("loocv_error_px")]
        print()
        print("=== Calibration LOOCV (calibration_debug.csv, full wrapped model) ===")
        print(f"  mean_loocv_err={float(np.mean(errs)):.1f}px on {len(errs)} cal targets")
    summ = list(csv.DictReader((ROOT / "calibration_summary.csv").open(encoding="utf-8")))
    overall = [r for r in summ if r.get("record_type") == "overall"]
    if overall:
        print(f"  calibration_summary overall LOOCV: {float(overall[0]['estimated_error_px']):.1f}px")


if __name__ == "__main__":
    main()
