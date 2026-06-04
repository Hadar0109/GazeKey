"""One-off analysis of calibration CSV artifacts."""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def fval(r: dict, k: str) -> float | None:
    v = r.get(k, "")
    if v == "" or v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def main() -> None:
    rows: list[dict] = []
    with open(ROOT / "calibration_samples.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    acc = [r for r in rows if r.get("accepted", "").strip().lower() == "true"]
    print(f"Total rows: {len(rows)}, accepted: {len(acc)}")

    by_label: dict[str, list[dict]] = defaultdict(list)
    for r in acc:
        by_label[r["target_label"]].append(r)

    grid9 = [
        "row0_left",
        "row0_center",
        "row0_right",
        "row1_left",
        "row1_center",
        "row1_right",
        "row2_left",
        "row2_center",
        "row2_right",
    ]
    extra = ["gap_0_1", "gap_1_2", "row0_x28", "row0_x72", "row2_x28", "row2_x72"]
    gate_ratio = 0.040
    gate_pca = 0.035

    print("\n=== Per-target ACCEPTED sample stability ===")
    print(
        f"{'label':<14} {'n':>3} {'std_u':>8} {'std_v':>8} "
        f"{'std_avg_h':>9} {'std_avg_v':>9} {'noisy':>5}"
    )
    per_target = []
    for lab in grid9 + extra:
        pts = by_label.get(lab, [])
        if not pts:
            continue
        u_means, v_means, ah, av = [], [], [], []
        for r in pts:
            uL, uR = fval(r, "pca_uL"), fval(r, "pca_uR")
            vL, vR = fval(r, "pca_vL"), fval(r, "pca_vR")
            if uL is not None and uR is not None:
                u_means.append(0.5 * (uL + uR))
            if vL is not None and vR is not None:
                v_means.append(0.5 * (vL + vR))
            h, v = fval(r, "avg_h"), fval(r, "avg_v")
            if h is not None:
                ah.append(h)
            if v is not None:
                av.append(v)
        su = float(np.std(u_means)) if u_means else float("nan")
        sv = float(np.std(v_means)) if v_means else float("nan")
        sah = float(np.std(ah)) if ah else float("nan")
        sav = float(np.std(av)) if av else float("nan")
        noisy = su > gate_pca or sv > gate_pca or sah > gate_ratio or sav > gate_ratio
        per_target.append((lab, len(pts), su, sv, sah, sav, noisy))
        print(
            f"{lab:<14} {len(pts):>3} {su:8.4f} {sv:8.4f} "
            f"{sah:9.4f} {sav:9.4f} {'YES' if noisy else 'no':>5}"
        )

    def agg(name: str, labs: set[str]) -> None:
        sus = [r[2] for r in per_target if r[0] in labs]
        svs = [r[3] for r in per_target if r[0] in labs]
        print(
            f"{name}: mean std_u={np.nanmean(sus):.4f} std_v={np.nanmean(svs):.4f} "
            f"(gate pca={gate_pca})"
        )

    corners = {"row0_left", "row0_right", "row2_left", "row2_right"}
    centers = {"row0_center", "row1_center", "row2_center"}
    agg("CORNERS (4 graded)", corners)
    agg("CENTERS (3 graded)", centers)
    agg("MID row L/R", {"row1_left", "row1_right"})

    dbg: list[dict] = []
    with open(ROOT / "calibration_debug.csv", newline="", encoding="utf-8") as f:
        dbg = list(csv.DictReader(f))

    print("\n=== Train error: |dx| vs |dy| (mapper bias direction) ===")
    print(f"{'label':<14} {'train':>6} {'|dx|':>7} {'|dy|':>7} {'dx%':>6}")
    for r in dbg:
        if r["label"] not in grid9:
            continue
        tx, ty = float(r["target_x"]), float(r["target_y"])
        px, py = float(r["predicted_x"]), float(r["predicted_y"])
        te = float(r["train_error_px"])
        dx, dy = abs(px - tx), abs(py - ty)
        dx_pct = 100.0 * dx / te if te > 1e-6 else 0.0
        print(f"{r['label']:<14} {te:6.1f} {dx:7.1f} {dy:7.1f} {dx_pct:5.0f}%")

    print("\n=== LOOCV vs train ratio (generalization gap) ===")
    for r in dbg:
        if r["label"] not in grid9:
            continue
        te, le = float(r["train_error_px"]), float(r["loocv_error_px"])
        ratio = le / te if te > 1e-6 else float("inf")
        print(f"  {r['label']:<14} train={te:5.1f} loocv={le:5.1f} ratio={ratio:4.1f}x")

    print("\n=== Bootstrap half-window mean shift (recollection sensitivity) ===")
    for lab in ["row0_center", "row0_left", "row0_right", "row2_left", "row2_right"]:
        pts = by_label.get(lab, [])
        feats = []
        for r in pts:
            uL, uR = fval(r, "pca_uL"), fval(r, "pca_uR")
            vL, vR = fval(r, "pca_vL"), fval(r, "pca_vR")
            if None not in (uL, uR, vL, vR):
                feats.append([0.5 * (uL + uR), 0.5 * (vL + vR)])
        if len(feats) < 10:
            continue
        a = np.array(feats)
        n = len(a)
        h1, h2 = a[: n // 2], a[n // 2 :]
        shift = float(np.linalg.norm(np.mean(h1, axis=0) - np.mean(h2, axis=0)))
        # Rough px sensitivity: use poly scale ~ 1000px per 0.1 u from train span
        u_span = 0.62 - 0.44  # approx from json
        px_per_u = 887 / u_span if u_span > 0 else 5000
        equiv_px = shift * px_per_u
        print(
            f"  {lab}: half-half uv shift={shift:.4f} (~{equiv_px:.0f}px equiv along u if linear)"
        )

    print("\n=== LOOCV error axis (from saved mapper + train features) ===")
    try:
        import json

        from gazekey.calibration2.mapper_store import mapper_from_dict
        from gazekey.features.feature_types import FrameFeatures

        with open(ROOT / "calibration_v2.json", encoding="utf-8") as f:
            data = json.load(f)
        model = mapper_from_dict(data)
        if model is None:
            print("  (could not load model)")
        else:
            n = int(data["train_n"])
            labels_by_idx = [dbg[i]["label"] for i in range(len(dbg))]

            def feat_i(i: int) -> FrameFeatures:
                u_l, u_r = float(data["train_u_l"][i]), float(data["train_u_r"][i])
                v_l, v_r = float(data["train_v_l"][i]), float(data["train_v_r"][i])
                return FrameFeatures(
                    timestamp_ms=0,
                    face_detected=True,
                    blink=False,
                    confidence=1.0,
                    Lh=0.5 + u_l,
                    Lv=0.5 + v_l,
                    Rh=0.5 + u_r,
                    Rv=0.5 + v_r,
                    avg_h=0.5 + 0.5 * (u_l + u_r),
                    avg_v=0.5 + 0.5 * (v_l + v_r),
                    eye_box_w=None,
                    eye_box_h=None,
                    face_x=None,
                    face_y=None,
                    pca_uL=u_l,
                    pca_vL=v_l,
                    pca_uR=u_r,
                    pca_vR=v_r,
                )

            detail = model.leave_one_out_detail_px()
            print(f"{'label':<14} {'loocv':>6} {'|dx|':>7} {'|dy|':>7} {'train':>6}")
            for d in detail:
                i = int(d["i"])
                lab = labels_by_idx[i] if i < len(labels_by_idx) else "?"
                tx, ty = float(dbg[i]["target_x"]), float(dbg[i]["target_y"])
                te = float(dbg[i]["train_error_px"])
                dx, dy = abs(float(d["pred_x"]) - tx), abs(float(d["pred_y"]) - ty)
                print(
                    f"{lab:<14} {float(d['err']):6.1f} {dx:7.1f} {dy:7.1f} {te:6.1f}"
                )
    except Exception as e:
        print(f"  (LOOCV recompute skipped: {e})")


if __name__ == "__main__":
    main()
