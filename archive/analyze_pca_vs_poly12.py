"""PCA vs poly12 keyboard benchmark analysis (read-only)."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gazekey.calibration.region_quality import raw_v_mean_u_corr
from gazekey.features.feature_types import FrameFeatures
from gazekey.features.poly_features import poly12_from_uv
from gazekey.mapping.ridge import (
    _fit_pca4_baseline,
    _fit_pca4_decoupled,
    _fit_poly12_joint,
    _fit_poly12_split,
    _loocv_pca4_baseline,
    _loocv_pca4_decoupled,
    _loocv_poly12_joint,
    _loocv_poly12_split,
    _loocv_rms_from_detail,
)


def main() -> None:
    data = json.loads((ROOT / "calibration_v2.json").read_text(encoding="utf-8"))
    n = int(data["train_n"])
    u_l = np.asarray(data["train_u_l"], dtype=np.float64)
    u_r = np.asarray(data["train_u_r"], dtype=np.float64)
    v_l = np.asarray(data["train_v_l"], dtype=np.float64)
    v_r = np.asarray(data["train_v_r"], dtype=np.float64)
    ty = np.asarray(data["train_Y"], dtype=np.float64).reshape(n, 2)
    Y = ty
    clip = tuple(data["clip_bounds"])
    alpha = float(data["alpha"])

    samples = []
    for i in range(n):
        samples.append(
            (
                FrameFeatures(
                    timestamp_ms=0,
                    face_detected=True,
                    blink=False,
                    confidence=1.0,
                    Lh=None,
                    Lv=None,
                    Rh=None,
                    Rv=None,
                    avg_h=None,
                    avg_v=None,
                    eye_box_w=None,
                    eye_box_h=None,
                    face_x=None,
                    face_y=None,
                    pca_uL=float(u_l[i]),
                    pca_vL=float(v_l[i]),
                    pca_uR=float(u_r[i]),
                    pca_vR=float(v_r[i]),
                ),
                (float(Y[i, 0]), float(Y[i, 1])),
            )
        )
    vu = raw_v_mean_u_corr(samples)
    print(f"v-u coupling r = {vu:.3f} (COUPLING_POLY12_THRESH=0.55)")

    cands = [
        ("pca4_baseline", _loocv_pca4_baseline, lambda: _fit_pca4_baseline(u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip)),
        (
            "pca4_decoupled_split",
            _loocv_pca4_decoupled,
            lambda: _fit_pca4_decoupled(
                u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip, log_coupling=False
            ),
        ),
        ("poly12_ridge", _loocv_poly12_joint, lambda: _fit_poly12_joint(u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip)),
        (
            "poly12_ridge_split_decoupled_y",
            lambda *a, **k: _loocv_poly12_split(*a, **k, y_mode="decoupled_v"),
            lambda: _fit_poly12_split(
                u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip, y_mode="decoupled_v"
            ),
        ),
    ]
    print("\nmapper                         train_rms  loocv_rms  worst_loocv  max_train")
    for name, loocv_fn, fit_fn in cands:
        detail = loocv_fn(u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip)
        loocv_rms = _loocv_rms_from_detail(detail)
        worst = max(float(x["err"]) for x in detail)
        m = fit_fn()
        train_errs = []
        for i, (f, _) in enumerate(samples):
            p = m.predict(f)
            train_errs.append(float(np.hypot(p.x - Y[i, 0], p.y - Y[i, 1])))
        train_rms = float(np.sqrt(np.mean(np.array(train_errs) ** 2)))
        print(
            f"{name:30} {train_rms:8.1f}   {loocv_rms:8.1f}   {worst:9.1f}   {max(train_errs):9.1f}"
        )

    m_pca = _fit_pca4_baseline(u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip)
    m_poly = _fit_poly12_split(
        u_l, u_r, v_l, v_r, Y, alpha=alpha, clip_bounds=clip, y_mode="decoupled_v"
    )
    print(f"\nPCA sum|w_x|={float(np.sum(np.abs(m_pca.w_x))):.1f}  poly12 sum|w_x|={float(np.sum(np.abs(m_poly.w_x))):.1f}")
    print(f"PCA b_x={m_pca.b_x:.1f}  poly12 b_x={m_poly.b_x:.1f}")

    P = poly12_from_uv(u_l, v_l, u_r, v_r)
    print(f"poly12 per-feature std: min={P.std(axis=0).min():.4f} max={P.std(axis=0).max():.4f}")
    print(f"raw u_l std={u_l.std():.4f}  u_r std={u_r.std():.4f}")

    # Cal target screen positions
    cal_xy = Y
    print("\nCal targets (screen):")
    labels = [
        "row0_left",
        "row0_center",
        "row0_right",
        "row1_left",
        "row1_center",
        "row1_right",
        "row2_left",
        "row2_center",
        "row2_right",
        "gap_0_1",
        "gap_1_2",
        "row0_x28",
        "row0_x72",
        "row2_x28",
        "row2_x72",
    ]
    for i, lab in enumerate(labels):
        print(f"  {lab:12} ({cal_xy[i,0]:6.0f}, {cal_xy[i,1]:3.0f})")

    rows = list(csv.DictReader((ROOT / "key_accuracy_compare.csv").open(encoding="utf-8")))
    keys = [r["target_key"] for r in rows if r["mapper_type"] == "pca4_baseline"]
    print("\nPer-key keyboard benchmark (pca4_baseline vs poly12_split_decoupled_y):")
    print(f"{'key':6} {'tcx':>5} {'pca_dx':>8} {'poly_dx':>8} {'pca_dy':>8} {'poly_dy':>8} pca poly")
    for k in keys:
        pca = next(r for r in rows if r["mapper_type"] == "pca4_baseline" and r["target_key"] == k)
        poly = next(
            r
            for r in rows
            if r["mapper_type"] == "poly12_ridge_split_decoupled_y" and r["target_key"] == k
        )
        print(
            f"{k:6} {float(pca['target_center_x']):5.0f} "
            f"{float(pca['dx']):+8.1f} {float(poly['dx']):+8.1f} "
            f"{float(pca['dy']):+8.1f} {float(poly['dy']):+8.1f} "
            f"{pca['is_correct']:>3} {poly['is_correct']:>4}"
        )

    # Keys where poly12 wrong and pca right
    print("\nKeys PCA correct, poly12 wrong:")
    for k in keys:
        pca = next(r for r in rows if r["mapper_type"] == "pca4_baseline" and r["target_key"] == k)
        poly = next(
            r
            for r in rows
            if r["mapper_type"] == "poly12_ridge_split_decoupled_y" and r["target_key"] == k
        )
        if pca["is_correct"] == "1" and poly["is_correct"] == "0":
            print(
                f"  {k}: pca err={float(pca['error_px']):.0f}px "
                f"poly err={float(poly['error_px']):.0f}px "
                f"dx poly={float(poly['dx']):+.0f}"
            )

    print("\nKeys both wrong:")
    for k in keys:
        pca = next(r for r in rows if r["mapper_type"] == "pca4_baseline" and r["target_key"] == k)
        poly = next(
            r
            for r in rows
            if r["mapper_type"] == "poly12_ridge_split_decoupled_y" and r["target_key"] == k
        )
        if pca["is_correct"] == "0" and poly["is_correct"] == "0":
            print(f"  {k}: pca={pca['predicted_key']} poly={poly['predicted_key']}")


if __name__ == "__main__":
    main()
