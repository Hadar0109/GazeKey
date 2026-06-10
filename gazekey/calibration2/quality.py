"""Calibration v2 quality diagnostics and acceptance gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration2.region_quality import assess_region_gates
from gazekey.calibration2.targets import CalibrationTarget, calibration_row_groups
from gazekey.features.feature_types import FrameFeatures
from gazekey.features.vertical_decouple import apply_v_residualizers_batch, fit_v_residualizers
from gazekey.mapping.ridge import RidgeCalibrationMapper
from gazekey.mvp_log import mvp_log, mvp_verbose


@dataclass(frozen=True)
class VerticalRowStats:
    name: str
    target_labels: Tuple[str, ...]
    mean_avg_v: Optional[float]
    mean_pca_v: Optional[float]
    mean_pca_vL: Optional[float]
    mean_pca_vR: Optional[float]
    mean_vL_res: Optional[float] = None
    mean_vR_res: Optional[float] = None
    mean_face_y: Optional[float] = None
    mean_eye_box_h: Optional[float] = None


@dataclass
class MonotonicityReport:
    feature_name: str
    top_mean: Optional[float]
    mid_mean: Optional[float]
    bottom_mean: Optional[float]
    valid: bool
    message: str


@dataclass
class CalibrationQualityResult:
    """Calibration usability vs supplementary mapping-quality signals.

    ``usable`` / ``accepted``: True when collection + basic sanity passed and the
    PCA4 mapper can predict (preview/benchmark may proceed). LOOCV, region, and
    train pixel gates are recorded as ``warnings`` on keyboard mode — benchmark
    decides mapping acceptance (FR-009, calibration-session contract).
    """

    usable: bool
    accepted: bool
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    monotonicity: List[MonotonicityReport] = field(default_factory=list)
    row_stats: List[VerticalRowStats] = field(default_factory=list)
    head_drift_warnings: List[str] = field(default_factory=list)
    max_train_error_px: Optional[float] = None
    max_loocv_error_px: Optional[float] = None
    loocv_rms_px: Optional[float] = None
    validation_center_error_px: Optional[float] = None
    screen_y_avg_v_corr: Optional[float] = None
    any_prediction_off_screen: bool = False


def _mean_feat(samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]], idx: int, attr: str) -> Optional[float]:
    if idx < 0 or idx >= len(samples):
        return None
    f = samples[idx][0]
    v = getattr(f, attr, None)
    return float(v) if v is not None and np.isfinite(float(v)) else None


def analyze_vertical_features(
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
) -> List[VerticalRowStats]:
    """Per-target vertical feature table + row aggregates."""
    top_i, mid_i, bot_i = calibration_row_groups(targets)

    mvp_log("[calib2] --- per-target vertical features (training means) ---")
    mvp_log(
        "[calib2] "
        f"{'id':<4} {'label':<14} {'screen_y':>8} "
        f"{'avg_v':>8} {'pca_vL':>8} {'pca_vR':>8} {'pca_v':>8} "
        f"{'face_y':>8} {'eye_h':>8}"
    )
    # Decoupled vertical residuals (fit on all training targets for diagnostics only).
    decoupled_by_i: Dict[int, Tuple[Optional[float], Optional[float]]] = {}
    u_l_all: List[float] = []
    u_r_all: List[float] = []
    v_l_all: List[float] = []
    v_r_all: List[float] = []
    for i, (feat, _) in enumerate(samples):
        if feat.pca_uL is not None and feat.pca_vL is not None and feat.pca_uR is not None and feat.pca_vR is not None:
            u_l_all.append(float(feat.pca_uL))
            u_r_all.append(float(feat.pca_uR))
            v_l_all.append(float(feat.pca_vL))
            v_r_all.append(float(feat.pca_vR))
    if len(u_l_all) >= 5:
        bl, br = fit_v_residualizers(
            np.array(u_l_all), np.array(u_r_all), np.array(v_l_all), np.array(v_r_all)
        )
        vl_r, vr_r = apply_v_residualizers_batch(
            np.array(u_l_all), np.array(u_r_all), np.array(v_l_all), np.array(v_r_all), beta_l=bl, beta_r=br
        )
        j = 0
        for i, (feat, _) in enumerate(samples):
            if feat.pca_uL is None or feat.pca_vL is None or feat.pca_uR is None or feat.pca_vR is None:
                decoupled_by_i[i] = (None, None)
            else:
                decoupled_by_i[i] = (float(vl_r[j]), float(vr_r[j]))
                j += 1

    per_target: List[dict] = []
    for i, (feat, (_tx, ty)) in enumerate(samples):
        label = targets[i].label if i < len(targets) else "?"
        pca_vL = feat.pca_vL
        pca_vR = feat.pca_vR
        pca_v = None
        if pca_vL is not None and pca_vR is not None:
            pca_v = 0.5 * (float(pca_vL) + float(pca_vR))
        vl_res, vr_res = decoupled_by_i.get(i, (None, None))
        v_res = None
        if vl_res is not None and vr_res is not None:
            v_res = 0.5 * (vl_res + vr_res)
        row = {
            "i": i,
            "label": label,
            "screen_y": float(ty),
            "avg_v": feat.avg_v,
            "pca_vL": pca_vL,
            "pca_vR": pca_vR,
            "pca_v": pca_v,
            "vL_res": vl_res,
            "vR_res": vr_res,
            "v_res": v_res,
            "face_y": feat.face_y,
            "eye_box_h": feat.eye_box_h,
        }
        per_target.append(row)
        mvp_log(
            "[calib2] "
            f"T{i+1:02d} {label:<14} {ty:8.0f} "
            f"{_fmt(feat.avg_v):>8} {_fmt(pca_vL):>8} {_fmt(pca_vR):>8} {_fmt(pca_v):>8} "
            f"{_fmt(feat.face_y):>8} {_fmt(feat.eye_box_h):>8}"
        )

    def row_stats(name: str, indices: List[int]) -> VerticalRowStats:
        labels = tuple(targets[j].label for j in indices if j < len(targets))

        def col(key: str) -> Optional[float]:
            vals = [per_target[j][key] for j in indices if per_target[j][key] is not None]
            if not vals:
                return None
            return float(np.mean(np.array(vals, dtype=np.float64)))

        return VerticalRowStats(
            name=name,
            target_labels=labels,
            mean_avg_v=col("avg_v"),
            mean_pca_v=col("pca_v"),
            mean_pca_vL=col("pca_vL"),
            mean_pca_vR=col("pca_vR"),
            mean_vL_res=col("vL_res"),
            mean_vR_res=col("vR_res"),
            mean_face_y=col("face_y"),
            mean_eye_box_h=col("eye_box_h"),
        )

    stats = [
        row_stats("top", top_i),
        row_stats("mid", mid_i),
        row_stats("bottom", bot_i),
    ]
    mvp_log("[calib2] --- row means (vertical features) ---")
    for rs in stats:
        mvp_log(
            "[calib2] "
            f"row {rs.name}: avg_v={_fmt(rs.mean_avg_v)} pca_v={_fmt(rs.mean_pca_v)} "
            f"pca_vL={_fmt(rs.mean_pca_vL)} pca_vR={_fmt(rs.mean_pca_vR)} "
            f"face_y={_fmt(rs.mean_face_y)} eye_box_h={_fmt(rs.mean_eye_box_h)} "
            f"n={len(rs.target_labels)}"
        )

    def row_span(key: str, row_name: str, indices: List[int]) -> None:
        vals = [per_target[j][key] for j in indices if per_target[j].get(key) is not None]
        if len(vals) >= 2:
            span = float(max(vals) - min(vals))
            mvp_log(f"[calib2] within-row {key} span ({row_name}): {span:.4f}")

    mvp_log("[calib2] --- within-row vertical feature spread ---")
    for row_name, indices in (("top", top_i), ("mid", mid_i), ("bottom", bot_i)):
        row_span("avg_v", row_name, indices)
        row_span("pca_v", row_name, indices)
        if decoupled_by_i:
            row_span("v_res", row_name, indices)

    return stats


def _fmt(v: Optional[float]) -> str:
    if v is None:
        return "   n/a"
    return f"{float(v):8.4f}"


def _keyboard_blocking_reason(reason: str) -> bool:
    """Hard blockers for keyboard usability (collection sanity + mapper usable)."""
    lower = reason.lower()
    if "predict returned none" in lower:
        return True
    if "catastrophic" in lower:
        return True
    if "head drift:" in lower and ("face_x" in lower or "face_y" in lower):
        return True
    return False


def check_vertical_monotonicity(
    row_stats: Sequence[VerticalRowStats],
    *,
    feature_attr: str,
    min_separation: float = 0.008,
) -> MonotonicityReport:
    """Expect top < mid < bottom for the given row-stat attribute."""
    by_name = {rs.name: rs for rs in row_stats}
    field_map = {
        "avg_v": "mean_avg_v",
        "pca_v": "mean_pca_v",
        "pca_vL": "mean_pca_vL",
        "pca_vR": "mean_pca_vR",
        "face_y": "mean_face_y",
        "eye_box_h": "mean_eye_box_h",
    }
    fld = field_map.get(feature_attr, f"mean_{feature_attr}")

    def get_row(name: str) -> Optional[float]:
        rs = by_name.get(name)
        if rs is None:
            return None
        v = getattr(rs, fld, None)
        return float(v) if v is not None else None

    t = get_row("top")
    m = get_row("mid")
    b = get_row("bottom")
    if t is None or m is None or b is None:
        return MonotonicityReport(
            feature_name=feature_attr,
            top_mean=t,
            mid_mean=m,
            bottom_mean=b,
            valid=False,
            message="missing row means",
        )

    sep_tm = m - t
    sep_mb = b - m
    valid = bool(sep_tm >= min_separation and sep_mb >= min_separation and t < m < b)
    if valid:
        msg = f"OK top={t:.4f} < mid={m:.4f} < bottom={b:.4f}"
    else:
        msg = (
            f"FAIL top={t:.4f} mid={m:.4f} bottom={b:.4f} "
            f"(sep top-mid={sep_tm:.4f} mid-bot={sep_mb:.4f}, need >={min_separation:.4f})"
        )
    return MonotonicityReport(feature_name=feature_attr, top_mean=t, mid_mean=m, bottom_mean=b, valid=valid, message=msg)


def print_monotonicity_reports(reports: Sequence[MonotonicityReport]) -> None:
    mvp_log("[calib2] --- vertical monotonicity (top < mid < bottom) ---")
    for r in reports:
        status = "VALID" if r.valid else "INVALID"
        mvp_log(f"[calib2] {r.feature_name}: {status} — {r.message}")


def analyze_head_pose_drift(
    *,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
    warn_face_x: float = 0.012,
    warn_face_y: float = 0.012,
    warn_eye_w: float = 0.006,
    warn_eye_h: float = 0.004,
) -> List[str]:
    """Warn if face geometry shifts too much between calibration targets."""
    warnings: List[str] = []
    attrs = ("face_x", "face_y", "eye_box_w", "eye_box_h")
    mvp_log("[calib2] --- head pose / face geometry per target ---")
    mvp_log(f"[calib2] {'id':<4} {'label':<14} {'face_x':>8} {'face_y':>8} {'eye_w':>8} {'eye_h':>8}")
    vals: Dict[str, List[float]] = {a: [] for a in attrs}
    for i, (feat, _) in enumerate(samples):
        label = targets[i].label if i < len(targets) else "?"
        row = {a: getattr(feat, a, None) for a in attrs}
        mvp_log(
            "[calib2] "
            f"T{i+1:02d} {label:<14} "
            f"{_fmt(row['face_x']):>8} {_fmt(row['face_y']):>8} "
            f"{_fmt(row['eye_box_w']):>8} {_fmt(row['eye_box_h']):>8}"
        )
        for a in attrs:
            v = row[a]
            if v is not None:
                vals[a].append(float(v))

    spans = {a: (max(vals[a]) - min(vals[a])) if vals[a] else 0.0 for a in attrs}
    thresholds = {
        "face_x": warn_face_x,
        "face_y": warn_face_y,
        "eye_box_w": warn_eye_w,
        "eye_box_h": warn_eye_h,
    }
    mvp_log(
        "[calib2] head geometry span: "
        + " ".join(f"{a}={spans[a]:.4f}" for a in attrs)
    )
    for a, thr in thresholds.items():
        if spans[a] > thr:
            msg = f"head drift: {a} span {spans[a]:.4f} > {thr:.4f} across targets"
            warnings.append(msg)
            mvp_log(f"[calib2] WARNING: {msg}")
    if not warnings:
        mvp_log("[calib2] head pose drift: within thresholds")
    return warnings


def _screen_bounds(screen_rect: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    """(x0, y0, x1, y1) inclusive bounds."""
    x, y, w, h = screen_rect
    return float(x), float(y), float(x + w), float(y + h)


def _in_screen(px: float, py: float, bounds: Tuple[float, float, float, float], *, margin: float = 0.0) -> bool:
    x0, y0, x1, y1 = bounds
    return bool(x0 - margin <= px <= x1 + margin and y0 - margin <= py <= y1 + margin)


def check_within_row_vertical_spread(
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
    *,
    min_pca_v_span: float = 0.02,
    min_avg_v_span: float = 0.02,
) -> List[str]:
    """Fail if targets in the same screen row have nearly identical vertical features."""
    top_i, mid_i, bot_i = calibration_row_groups(targets)
    issues: List[str] = []

    def row_span(indices: List[int], row_name: str) -> None:
        if len(indices) < 2:
            return
        pca_vs: List[float] = []
        avg_vs: List[float] = []
        labels: List[str] = []
        for j in indices:
            if j >= len(samples):
                continue
            f = samples[j][0]
            labels.append(targets[j].label if j < len(targets) else f"T{j+1:02d}")
            if f.pca_vL is not None and f.pca_vR is not None:
                pca_vs.append(0.5 * (float(f.pca_vL) + float(f.pca_vR)))
            if f.avg_v is not None:
                avg_vs.append(float(f.avg_v))
        if len(pca_vs) >= 2:
            span = float(max(pca_vs) - min(pca_vs))
            mvp_log(f"[calib2] within-row pca_v span ({row_name}): {span:.4f} ({', '.join(labels)})")
            if span < min_pca_v_span:
                issues.append(f"{row_name} row pca_v span {span:.4f} < {min_pca_v_span:.4f}")
        if len(avg_vs) >= 2:
            span_a = float(max(avg_vs) - min(avg_vs))
            mvp_log(f"[calib2] within-row avg_v span ({row_name}): {span_a:.4f} ({', '.join(labels)})")
            if span_a < min_avg_v_span:
                issues.append(f"{row_name} row avg_v span {span_a:.4f} < {min_avg_v_span:.4f}")

    row_span(top_i, "top")
    row_span(mid_i, "mid")
    row_span(bot_i, "bottom")
    return issues


def evaluate_calibration_quality(
    *,
    model: RidgeCalibrationMapper,
    samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    targets: Sequence[CalibrationTarget],
    screen_rect: Tuple[float, float, float, float],
    calibration_mode: str = "keyboard9",
    loocv_detail: Optional[Sequence[dict]] = None,
    max_validation_error_px: float = 150.0,
    max_train_error_px: float = 100.0,
    max_loocv_rms_px: float = 150.0,
    max_target_loocv_px: float = 175.0,
    max_off_screen_loocv: int = 1,
    min_vertical_separation: float = 0.008,
    min_within_row_pca_v_span: float = 0.015,
    min_screen_y_avg_v_corr: float = 0.55,
    min_catastrophic_screen_y_avg_v_corr: float = 0.15,
    max_single_target_train_px: float = 55.0,
    require_avg_v_monotonic: bool = False,
    require_any_vertical_monotonic: bool = True,
    half_key_height_px: float = 34.0,
    max_head_drift_eye_h: Optional[float] = None,
    min_avg_v_row_separation: Optional[float] = None,
) -> CalibrationQualityResult:
    """
    Run diagnostics and return whether calibration should be accepted.
    """
    reasons: List[str] = []
    warnings: List[str] = []
    row_stats = analyze_vertical_features(samples=samples, targets=targets)
    head_warnings = analyze_head_pose_drift(samples=samples, targets=targets)
    for msg in head_warnings:
        if "face_x" in msg or "face_y" in msg:
            reasons.append(msg)
            mvp_log(f"[calib2]   quality (reject): {msg}")
        elif max_head_drift_eye_h is not None and "eye_box" in msg:
            reasons.append(msg)
        elif max_head_drift_eye_h is not None:
            warnings.append(msg)
            mvp_log(f"[calib2]   quality (warning): {msg}")

    mono_reports = [
        check_vertical_monotonicity(row_stats, feature_attr="avg_v", min_separation=min_vertical_separation),
        check_vertical_monotonicity(row_stats, feature_attr="pca_v", min_separation=min_vertical_separation),
        check_vertical_monotonicity(row_stats, feature_attr="pca_vL", min_separation=min_vertical_separation),
        check_vertical_monotonicity(row_stats, feature_attr="pca_vR", min_separation=min_vertical_separation),
        check_vertical_monotonicity(row_stats, feature_attr="face_y", min_separation=min_vertical_separation),
    ]
    print_monotonicity_reports(mono_reports)

    if require_avg_v_monotonic and not mono_reports[0].valid:
        reasons.append(f"avg_v row order invalid: {mono_reports[0].message}")
    if require_any_vertical_monotonic:
        pca_ok = any(r.valid for r in mono_reports[1:4])
        if not pca_ok:
            reasons.append("no pca_v / pca_vL / pca_vR row monotonicity (vertical gaze signal weak)")

    if min_avg_v_row_separation is not None:
        rs = {r.name: r for r in row_stats}
        top_v = rs.get("top").mean_avg_v if rs.get("top") else None
        bot_v = rs.get("bottom").mean_avg_v if rs.get("bottom") else None
        if top_v is not None and bot_v is not None:
            sep = float(bot_v) - float(top_v)
            mvp_log(f"[calib2] avg_v row separation (bottom-top): {sep:.4f}")
            if sep < float(min_avg_v_row_separation):
                reasons.append(
                    f"avg_v row separation too weak ({sep:.4f} < {min_avg_v_row_separation:.4f})"
                )

    for issue in check_within_row_vertical_spread(
        samples,
        targets,
        min_pca_v_span=min_within_row_pca_v_span,
        min_avg_v_span=min_within_row_pca_v_span,
    ):
        reasons.append(issue)

    bounds = _screen_bounds(screen_rect)
    train_errs: List[float] = []
    off_screen = False
    mvp_log("[calib2] --- training predictions (Y-axis check) ---")
    for i, (feat, (tx, ty)) in enumerate(samples):
        pred = model.predict(feat)
        if pred is None:
            reasons.append(f"T{i+1:02d}: mapper predict returned None")
            continue
        err = float(np.hypot(float(pred.x) - float(tx), float(pred.y) - float(ty)))
        train_errs.append(err)
        in_bounds = _in_screen(float(pred.x), float(pred.y), bounds)
        if not in_bounds:
            off_screen = True
            reasons.append(
                f"T{i+1:02d} train prediction off-screen: ({pred.x:.1f},{pred.y:.1f}) "
                f"bounds=({bounds[0]:.0f},{bounds[1]:.0f})-({bounds[2]:.0f},{bounds[3]:.0f})"
            )
        dy = float(pred.y) - float(ty)
        mvp_log(
            "[calib2] "
            f"T{i+1:02d} target_y={ty:.0f} pred_y={pred.y:.1f} dy={dy:+.0f}px err={err:.1f}px in_screen={in_bounds}"
        )

    max_train = max(train_errs) if train_errs else None
    worst_train_i = int(np.argmax(train_errs)) if train_errs else -1
    worst_train_label = (
        targets[worst_train_i].label if 0 <= worst_train_i < len(targets) else ""
    )
    if worst_train_label:
        mvp_log(f"[calib2] worst train target: {worst_train_label} err={max_train:.1f}px")

    is_keyboard = str(calibration_mode).lower().startswith("keyboard")
    pixel_reasons: List[str] = []
    if max_train is not None and max_train > max_train_error_px:
        pixel_reasons.append(f"max train error {max_train:.1f}px > {max_train_error_px:.1f}px")
    for i, err in enumerate(train_errs):
        if err > max_single_target_train_px:
            label = targets[i].label if i < len(targets) else f"T{i+1:02d}"
            pixel_reasons.append(
                f"{label} train error {err:.1f}px > {max_single_target_train_px:.1f}px"
            )
    if is_keyboard:
        for pr in pixel_reasons:
            warnings.append(pr)
            mvp_log(f"[calib2]   pixel (warning): {pr}")
    else:
        reasons.extend(pixel_reasons)

    # LOOCV (softened: allow at most max_off_screen_loocv corner extrapolations)
    loocv_errs: List[float] = []
    off_screen_loocv: List[str] = []
    if loocv_detail:
        for d in loocv_detail:
            i = int(d["i"])
            e = float(d["err"])
            loocv_errs.append(e)
            px = float(d["pred_x"])
            py = float(d["pred_y"])
            if not _in_screen(px, py, bounds):
                off_screen = True
                off_screen_loocv.append(f"T{i+1:02d}=({px:.1f},{py:.1f})")

    if off_screen_loocv:
        mvp_log(
            f"[calib2] LOOCV off-screen ({len(off_screen_loocv)}): "
            + ", ".join(off_screen_loocv)
        )
        if len(off_screen_loocv) > int(max_off_screen_loocv):
            reasons.append(
                f"too many LOOCV off-screen ({len(off_screen_loocv)} > {max_off_screen_loocv}): "
                + "; ".join(off_screen_loocv[:3])
            )

    loocv_rms = float(np.sqrt(np.mean(np.array(loocv_errs, dtype=np.float64) ** 2))) if loocv_errs else None
    max_loocv = max(loocv_errs) if loocv_errs else None
    worst_loocv_label = ""
    if loocv_detail and loocv_errs:
        wi = int(max(range(len(loocv_errs)), key=lambda j: loocv_errs[j]))
        worst_loocv_label = targets[wi].label if wi < len(targets) else f"T{wi+1:02d}"
        if worst_loocv_label:
            mvp_log(f"[calib2] worst LOOCV target: {worst_loocv_label} err={max_loocv:.1f}px")

    loocv_pixel: List[str] = []
    if loocv_rms is not None and loocv_rms > max_loocv_rms_px:
        loocv_pixel.append(f"LOOCV RMS {loocv_rms:.1f}px > {max_loocv_rms_px:.1f}px")
    if max_loocv is not None and max_loocv > max_target_loocv_px:
        loocv_pixel.append(f"worst LOOCV {max_loocv:.1f}px > {max_target_loocv_px:.1f}px")
    if is_keyboard:
        for pr in loocv_pixel:
            warnings.append(pr)
            mvp_log(f"[calib2]   pixel (warning): {pr}")
    else:
        reasons.extend(loocv_pixel)

    if is_keyboard:
        region = assess_region_gates(
            model=model,
            samples=samples,
            targets=targets,
            loocv_detail=loocv_detail,
            keyboard_mode=True,
            half_key_height_px=half_key_height_px,
            verbose=False,
        )
        for rr in region.hard_fail_reasons:
            warnings.append(rr)
        if not region.passed:
            mvp_log(
                "[calib2] keyboard region quality warning: wrong calibration region "
                "(row/col) — supplementary; benchmark decides mapping acceptance"
            )
        elif pixel_reasons or loocv_pixel:
            mvp_log(
                "[calib2] keyboard region OK — pixel thresholds exceeded "
                "(supplementary warnings only)"
            )

    # Center-target proxy for post-fit validation (offline).
    center_err = None
    center_idx = next((i for i, t in enumerate(targets) if str(t.label).lower() == "center"), None)
    if center_idx is not None and center_idx < len(samples):
        feat, (cx, cy) = samples[center_idx]
        pred = model.predict(feat)
        if pred is not None:
            center_err = float(np.hypot(float(pred.x) - float(cx), float(pred.y) - float(cy)))
            if center_err > max_validation_error_px:
                reasons.append(
                    f"center hold-out error {center_err:.1f}px > {max_validation_error_px:.1f}px"
                )
            if not _in_screen(float(pred.x), float(pred.y), bounds):
                off_screen = True
                reasons.append(f"center prediction off-screen: ({pred.x:.1f},{pred.y:.1f})")

    # Feature span sanity (vertical signal usable for ridge).
    is_fullscreen = str(calibration_mode).lower().startswith("fullscreen")
    v_vals = [float(s[0].avg_v) for s in samples if s[0].avg_v is not None]
    if v_vals:
        span_v = float(max(v_vals) - min(v_vals))
        mvp_log(f"[calib2] avg_v span across targets: {span_v:.4f}")
        if is_fullscreen and span_v < 0.04:
            reasons.append(f"avg_v span too small ({span_v:.4f} < 0.04) for fullscreen mapping")

    pca_vs = []
    for s in samples:
        f = s[0]
        if f.pca_vL is not None and f.pca_vR is not None:
            pca_vs.append(0.5 * (float(f.pca_vL) + float(f.pca_vR)))
    if pca_vs:
        span_pca = float(max(pca_vs) - min(pca_vs))
        mvp_log(f"[calib2] pca_v span across targets: {span_pca:.4f}")
        if is_fullscreen and span_pca < 0.04:
            reasons.append(f"pca_v span too small ({span_pca:.4f} < 0.04) for fullscreen mapping")

    # Y-axis orientation: screen_y should correlate positively with avg_v.
    screen_y_avg_v_corr: Optional[float] = None
    ys = np.array([float(t.screen_y) for t in targets[: len(samples)]], dtype=np.float64)
    vs = np.array([float(s[0].avg_v) for s in samples if s[0].avg_v is not None], dtype=np.float64)
    if ys.size == vs.size and ys.size >= 3:
        corr = float(np.corrcoef(ys, vs)[0, 1]) if np.std(vs) > 1e-9 else 0.0
        screen_y_avg_v_corr = float(corr)
        mvp_log(f"[calib2] corr(screen_y, avg_v)={corr:.3f} (expect positive)")
        catastrophic = float(min_catastrophic_screen_y_avg_v_corr)
        preferred = float(min_screen_y_avg_v_corr)
        if is_fullscreen:
            if corr < catastrophic:
                reasons.append(
                    f"avg_v poorly correlated with screen Y (r={corr:.3f}, need >={catastrophic:.2f})"
                )
        elif is_keyboard:
            if corr < catastrophic:
                reasons.append(
                    f"avg_v poorly correlated with screen Y (r={corr:.3f}, "
                    f"catastrophic threshold >={catastrophic:.2f})"
                )
            elif corr < preferred:
                msg = (
                    f"avg_v correlation below preferred {preferred:.2f} "
                    f"(r={corr:.3f}) — typing enabled; region gates are primary"
                )
                warnings.append(msg)
                mvp_log(f"[calib2]   quality (warning): {msg}")
        else:
            if corr < preferred:
                reasons.append(
                    f"avg_v poorly correlated with screen Y (r={corr:.3f}, need >={preferred:.2f})"
                )

    if is_keyboard:
        kept: List[str] = []
        for r in reasons:
            if _keyboard_blocking_reason(r):
                kept.append(r)
            else:
                warnings.append(r)
        reasons = kept

    usable = len(reasons) == 0
    if usable:
        if warnings:
            mvp_log(
                f"[calib2] calibration usable for preview/benchmark "
                f"({len(warnings)} quality warning(s); benchmark decides mapping acceptance)",
                always=True,
            )
            for w in warnings:
                mvp_log(f"[calib2]   quality warning: {w}")
        else:
            mvp_log("[calib2] calibration usable for preview/benchmark", always=True)
    else:
        mvp_log("[calib2] calibration NOT usable (basic sanity / mapper failed)", always=True)
        for r in reasons:
            mvp_log(f"[calib2]   - {r}", always=True)

    return CalibrationQualityResult(
        usable=usable,
        accepted=usable,
        reasons=reasons,
        warnings=warnings,
        monotonicity=list(mono_reports),
        row_stats=list(row_stats),
        head_drift_warnings=head_warnings,
        max_train_error_px=max_train,
        max_loocv_error_px=max_loocv,
        loocv_rms_px=loocv_rms,
        validation_center_error_px=center_err,
        screen_y_avg_v_corr=screen_y_avg_v_corr,
        any_prediction_off_screen=off_screen,
    )


def assess_fullscreen_feasibility(
    *,
    row_stats: Sequence[VerticalRowStats],
    monotonicity: Sequence[MonotonicityReport],
    loocv_rms_px: Optional[float],
) -> None:
    """Print a short conclusion on whether fullscreen 9-point mapping is realistic."""
    if not mvp_verbose():
        return
    avg_v_mono = next((r for r in monotonicity if r.feature_name == "avg_v"), None)
    pca_mono = [r for r in monotonicity if r.feature_name.startswith("pca")]
    pca_any = any(r.valid for r in pca_mono)

    rs = {r.name: r for r in row_stats}
    sep_avg = None
    if rs.get("top") and rs.get("bottom") and rs["top"].mean_avg_v is not None and rs["bottom"].mean_avg_v is not None:
        sep_avg = float(rs["bottom"].mean_avg_v) - float(rs["top"].mean_avg_v)

    mvp_log("[calib2] --- fullscreen mapping feasibility ---")
    if sep_avg is not None:
        mvp_log(f"[calib2] avg_v row separation (bottom-top): {sep_avg:.4f}")
    if avg_v_mono and avg_v_mono.valid:
        mvp_log("[calib2] avg_v: row monotonicity OK (coarse vertical signal present)")
    else:
        mvp_log("[calib2] avg_v: row monotonicity weak or absent — vertical mapping unreliable")
    if pca_any:
        mvp_log("[calib2] pca_v*: better row separation than avg_v alone — prefer ridge PCA features")
    else:
        mvp_log("[calib2] pca_v*: no clear row separation — webcam vertical signal likely insufficient for fullscreen")
    if loocv_rms_px is not None:
        if loocv_rms_px <= 120.0:
            mvp_log(f"[calib2] LOOCV {loocv_rms_px:.1f}px: fullscreen mapping may be viable")
        elif loocv_rms_px <= 180.0:
            mvp_log(f"[calib2] LOOCV {loocv_rms_px:.1f}px: marginal — keyboard-region calibration likely more stable")
        else:
            mvp_log(f"[calib2] LOOCV {loocv_rms_px:.1f}px: poor — fullscreen mapping not realistic with current features")
