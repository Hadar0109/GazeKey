"""Stage-by-stage mapper diagnostics for keyboard accuracy replay."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

from gazekey.calibration2.targets import CalibrationTarget
from gazekey.debug.keyboard_accuracy import (
    DEFAULT_FEATURE_SMOOTHER_ALPHA,
    RecordedKeyFrames,
    display_key_name,
    mean_frame_features,
    predict_key_at,
)
from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.mapping.local_y_correction import (
    MapperWithLocalYCorrection,
    interpolate_y_residual,
)
from gazekey.mapping.ridge import Pca4BaselineMapper, _clip_xy, _predict_ridge_1d, _raw_uv
from gazekey.mapping.row_bias import MapperWithRowBias

ROW_NAMES = ("top", "mid", "bottom")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_mapper_stages_csv_path() -> Path:
    return _repo_root() / "key_accuracy_mapper_stages.csv"


def default_anchor_distance_csv_path() -> Path:
    return _repo_root() / "key_accuracy_anchor_distance.csv"


@dataclass(frozen=True)
class MapperStack:
    core: object
    row_bias: Optional[MapperWithRowBias]
    local_y: Optional[MapperWithLocalYCorrection]


def unwrap_mapper_stack(model: object) -> MapperStack:
    """Split runtime mapper into core ridge + optional correction wrappers."""
    row_bias: Optional[MapperWithRowBias] = None
    local_y: Optional[MapperWithLocalYCorrection] = None
    m = model
    if isinstance(m, MapperWithLocalYCorrection):
        local_y = m
        m = m.inner
    if isinstance(m, MapperWithRowBias):
        row_bias = m
        m = m.inner
    return MapperStack(core=m, row_bias=row_bias, local_y=local_y)


def _nearest_row_index(py: float, row_y_centers: Tuple[float, float, float]) -> int:
    ys = np.asarray(row_y_centers, dtype=np.float64)
    return int(np.argmin(np.abs(ys - float(py))))


def _predict_pca4_core_xy(
    core: Pca4BaselineMapper,
    features: FrameFeatures,
) -> Optional[Tuple[float, float, float, float]]:
    """Return (x_raw, y_raw, x_clipped, y_clipped) from core ridge before wrappers."""
    raw = _raw_uv(features)
    if raw is None:
        return None
    u_l, v_l, u_r, v_r = raw
    px_raw = _predict_ridge_1d(
        np.array([u_l, u_r], dtype=np.float64),
        w=core.w_x,
        intercept=core.b_x,
        mu=core.mu_x,
        sigma=core.sigma_x,
    )
    py_raw = _predict_ridge_1d(
        np.array([v_l, v_r], dtype=np.float64),
        w=core.w_y,
        intercept=core.b_y,
        mu=core.mu_y,
        sigma=core.sigma_y,
    )
    px, py = _clip_xy(px_raw, py_raw, core.clip_bounds)
    return float(px_raw), float(py_raw), float(px), float(py)


def _clip_flags(
    x_before: float,
    y_before: float,
    x_after: float,
    y_after: float,
    bounds: Optional[Tuple[float, float, float, float]],
) -> Tuple[int, int, int, int]:
    if bounds is None:
        return 0, 0, 0, 0
    x0, y0, x1, y1 = bounds
    clip_x_min = int(abs(x_before - x0) > 1e-3 and abs(x_after - x0) < 1e-3)
    clip_x_max = int(abs(x_before - x1) > 1e-3 and abs(x_after - x1) < 1e-3)
    clip_y_min = int(abs(y_before - y0) > 1e-3 and abs(y_after - y0) < 1e-3)
    clip_y_max = int(abs(y_before - y1) > 1e-3 and abs(y_after - y1) < 1e-3)
    return clip_x_min, clip_x_max, clip_y_min, clip_y_max


@dataclass(frozen=True)
class FrameStageTrace:
    raw: FrameFeatures
    smooth: FrameFeatures
    core_x: float
    core_y_raw: float
    core_y: float
    row_idx: int
    row_bias: float
    x_after_row: float
    y_after_row: float
    local_dy: float
    x_after_local: float
    y_after_local: float
    x_after_bias: float
    y_after_bias: float
    x_final: float
    y_final: float
    clip_x_min: int
    clip_x_max: int
    clip_y_min: int
    clip_y_max: int


def trace_mapper_frame(
    raw: FrameFeatures,
    *,
    stack: MapperStack,
    feature_smoother: PcaFeatureSmoother,
    gaze_bias_x: float = 0.0,
    gaze_bias_y: float = 0.0,
    clamp_xy: Optional[Callable[[float, float], Tuple[float, float]]] = None,
) -> Optional[FrameStageTrace]:
    """Trace one frame through smoother -> core -> row bias -> local Y -> bias -> clamp."""
    smooth = feature_smoother.smooth(raw)
    core = stack.core
    clip_bounds = getattr(core, "clip_bounds", None)

    if isinstance(core, Pca4BaselineMapper):
        core_xy = _predict_pca4_core_xy(core, smooth)
        if core_xy is None:
            return None
        _px_raw, core_y_raw, core_x, core_y = core_xy
    else:
        pred = core.predict(smooth)
        if pred is None:
            return None
        core_x = float(pred.x)
        core_y = float(pred.y)
        core_y_raw = core_y

    x_after_row = core_x
    y_after_row = core_y
    row_idx = -1
    row_bias = 0.0
    if stack.row_bias is not None:
        row_idx = _nearest_row_index(core_y, stack.row_bias.row_y_centers)
        row_bias = float(stack.row_bias.row_y_bias[row_idx])
        y_after_row = core_y - row_bias

    local_dy = 0.0
    x_after_local = x_after_row
    y_after_local = y_after_row
    if stack.local_y is not None:
        local_dy = interpolate_y_residual(
            x_after_row,
            stack.local_y.train_x,
            stack.local_y.train_dy,
        )
        y_after_local = y_after_row - local_dy

    x_after_bias = x_after_local + float(gaze_bias_x)
    y_after_bias = y_after_local + float(gaze_bias_y)

    x_final = x_after_bias
    y_final = y_after_bias
    if clamp_xy is not None:
        x_final, y_final = clamp_xy(x_after_bias, y_after_bias)
    elif clip_bounds is not None:
        x_final, y_final = _clip_xy(x_after_bias, y_after_bias, clip_bounds)

    clip_x_min, clip_x_max, clip_y_min, clip_y_max = _clip_flags(
        x_after_bias,
        y_after_bias,
        x_final,
        y_final,
        clip_bounds,
    )

    return FrameStageTrace(
        raw=raw,
        smooth=smooth,
        core_x=core_x,
        core_y_raw=core_y_raw,
        core_y=core_y,
        row_idx=row_idx,
        row_bias=row_bias,
        x_after_row=x_after_row,
        y_after_row=y_after_row,
        local_dy=local_dy,
        x_after_local=x_after_local,
        y_after_local=y_after_local,
        x_after_bias=x_after_bias,
        y_after_bias=y_after_bias,
        x_final=x_final,
        y_final=y_final,
        clip_x_min=clip_x_min,
        clip_x_max=clip_x_max,
        clip_y_min=clip_y_min,
        clip_y_max=clip_y_max,
    )


def _mean_features(frames: Sequence[FrameFeatures]) -> Optional[FrameFeatures]:
    return mean_frame_features(frames)


def _mean_trace_coords(traces: Sequence[FrameStageTrace]) -> dict[str, float]:
    def mean_attr(name: str) -> float:
        vals = [float(getattr(t, name)) for t in traces]
        return float(np.mean(np.asarray(vals, dtype=np.float64)))

    row_idx_vals = [int(t.row_idx) for t in traces if t.row_idx >= 0]
    row_idx = int(round(float(np.mean(row_idx_vals)))) if row_idx_vals else -1

    return {
        "core_x": mean_attr("core_x"),
        "core_y_raw": mean_attr("core_y_raw"),
        "core_y": mean_attr("core_y"),
        "row_idx": float(row_idx),
        "row_bias": mean_attr("row_bias"),
        "x_after_row": mean_attr("x_after_row"),
        "y_after_row": mean_attr("y_after_row"),
        "local_dy": mean_attr("local_dy"),
        "x_after_local": mean_attr("x_after_local"),
        "y_after_local": mean_attr("y_after_local"),
        "x_after_bias": mean_attr("x_after_bias"),
        "y_after_bias": mean_attr("y_after_bias"),
        "x_final": mean_attr("x_final"),
        "y_final": mean_attr("y_final"),
        "clip_x_min": float(max(int(t.clip_x_min) for t in traces)),
        "clip_x_max": float(max(int(t.clip_x_max) for t in traces)),
        "clip_y_min": float(max(int(t.clip_y_min) for t in traces)),
        "clip_y_max": float(max(int(t.clip_y_max) for t in traces)),
    }


def _feature_snapshot(feat: Optional[FrameFeatures], prefix: str) -> dict[str, str]:
    fields = (
        "avg_h",
        "avg_v",
        "pca_uL",
        "pca_vL",
        "pca_uR",
        "pca_vR",
        "face_x",
        "face_y",
    )
    out: dict[str, str] = {}
    for name in fields:
        val = None if feat is None else getattr(feat, name)
        out[f"{prefix}_{name}"] = "" if val is None else f"{float(val):.6f}"
    return out


def _pca4_feature_vector(feat: FrameFeatures) -> Optional[np.ndarray]:
    if (
        feat.pca_uL is None
        or feat.pca_vL is None
        or feat.pca_uR is None
        or feat.pca_vR is None
    ):
        return None
    return np.array(
        [float(feat.pca_uL), float(feat.pca_vL), float(feat.pca_uR), float(feat.pca_vR)],
        dtype=np.float64,
    )


def rank_calibration_anchors(
    feat: FrameFeatures,
    *,
    calib_samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    calib_targets: Sequence[CalibrationTarget],
) -> List[Tuple[int, str, str, float, float, float]]:
    """
    Return anchors sorted by PCA4 feature distance:
    (index, target_id, label, distance, anchor_screen_y, anchor_avg_v).
    """
    q = _pca4_feature_vector(feat)
    if q is None:
        return []
    ranked: List[Tuple[int, str, str, float, float, float]] = []
    for i, (anchor_feat, (_tx, ty)) in enumerate(calib_samples):
        a = _pca4_feature_vector(anchor_feat)
        if a is None:
            continue
        dist = float(np.linalg.norm(q - a))
        label = calib_targets[i].label if i < len(calib_targets) else f"anchor_{i}"
        tid = calib_targets[i].target_id if i < len(calib_targets) else f"T{i+1:02d}"
        avg_v = float(anchor_feat.avg_v) if anchor_feat.avg_v is not None else float("nan")
        ranked.append((i, tid, label, dist, float(ty), avg_v))
    ranked.sort(key=lambda t: t[3])
    return ranked


@dataclass(frozen=True)
class KeyMapperStageRow:
    target_key: str
    target_center_x: float
    target_center_y: float
    is_correct: int
    predicted_key: str
    error_px: float
    raw_features: dict[str, str]
    smooth_features: dict[str, str]
    core_x: float
    core_y_raw: float
    core_y: float
    row_idx: int
    row_name: str
    row_bias: float
    y_after_row: float
    local_dy: float
    y_after_local: float
    y_after_bias: float
    x_final: float
    y_final: float
    clip_y_min: int
    clip_y_max: int
    dy_core: float
    dy_row: float
    dy_local: float
    dy_final: float
    delta_y_row: float
    delta_y_local: float
    delta_y_clamp: float


@dataclass(frozen=True)
class KeyAnchorDistanceRow:
    target_key: str
    test_avg_v: float
    nearest_id: str
    nearest_label: str
    nearest_distance: float
    nearest_anchor_y: float
    nearest_anchor_avg_v: float
    second_id: str
    second_label: str
    second_distance: float
    third_id: str
    third_label: str
    third_distance: float


STAGE_CSV_FIELDS = [
    "target_key",
    "target_center_x",
    "target_center_y",
    "is_correct",
    "predicted_key",
    "error_px",
    "raw_avg_h",
    "raw_avg_v",
    "raw_pca_uL",
    "raw_pca_vL",
    "raw_pca_uR",
    "raw_pca_vR",
    "raw_face_x",
    "raw_face_y",
    "smooth_avg_h",
    "smooth_avg_v",
    "smooth_pca_uL",
    "smooth_pca_vL",
    "smooth_pca_uR",
    "smooth_pca_vR",
    "smooth_face_x",
    "smooth_face_y",
    "core_x",
    "core_y_raw",
    "core_y",
    "row_idx",
    "row_name",
    "row_bias_applied",
    "y_after_row",
    "local_dy",
    "y_after_local",
    "y_after_bias",
    "x_final",
    "y_final",
    "clip_y_min",
    "clip_y_max",
    "dy_core",
    "dy_row",
    "dy_local",
    "dy_final",
    "delta_y_row",
    "delta_y_local",
    "delta_y_clamp",
]

ANCHOR_CSV_FIELDS = [
    "target_key",
    "test_avg_v",
    "nearest_id",
    "nearest_label",
    "nearest_distance",
    "nearest_anchor_y",
    "nearest_anchor_avg_v",
    "second_id",
    "second_label",
    "second_distance",
    "third_id",
    "third_label",
    "third_distance",
]


def diagnose_recorded_keys(
    *,
    recorded: Sequence[RecordedKeyFrames],
    keys: Sequence[KeyGeometryRow],
    model: object,
    calib_samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    calib_targets: Sequence[CalibrationTarget],
    gaze_bias_x: float = 0.0,
    gaze_bias_y: float = 0.0,
    clamp_xy: Optional[Callable[[float, float], Tuple[float, float]]] = None,
    feature_smoother_alpha: float = DEFAULT_FEATURE_SMOOTHER_ALPHA,
) -> Tuple[List[KeyMapperStageRow], List[KeyAnchorDistanceRow]]:
    """Replay recorded per-key frames through staged mapper diagnostics."""
    stack = unwrap_mapper_stack(model)
    stage_rows: List[KeyMapperStageRow] = []
    anchor_rows: List[KeyAnchorDistanceRow] = []

    for item in recorded:
        smoother = PcaFeatureSmoother(alpha=float(feature_smoother_alpha))
        traces: List[FrameStageTrace] = []
        smooth_frames: List[FrameFeatures] = []
        for raw in item.frames:
            trace = trace_mapper_frame(
                raw,
                stack=stack,
                feature_smoother=smoother,
                gaze_bias_x=gaze_bias_x,
                gaze_bias_y=gaze_bias_y,
                clamp_xy=clamp_xy,
            )
            if trace is not None:
                traces.append(trace)
                smooth_frames.append(trace.smooth)

        tcx, tcy = item.target.center
        if not traces:
            continue

        coords = _mean_trace_coords(traces)
        raw_mean = _mean_features(item.frames)
        smooth_mean = _mean_features(smooth_frames)

        x_final = coords["x_final"]
        y_final = coords["y_final"]
        predicted = predict_key_at(x_final, y_final, keys)
        pred_name = display_key_name(predicted)
        is_correct = int(
            pred_name.upper() == str(item.target_label).upper()
            or (str(item.target_label).lower() == "space" and pred_name == "Space")
        )
        err = float(math.hypot(x_final - tcx, y_final - tcy))

        row_idx = int(coords["row_idx"])
        row_name = ROW_NAMES[row_idx] if 0 <= row_idx < len(ROW_NAMES) else ""

        dy_core = coords["core_y"] - tcy
        dy_row = coords["y_after_row"] - tcy
        dy_local = coords["y_after_local"] - tcy
        dy_final = y_final - tcy

        stage_rows.append(
            KeyMapperStageRow(
                target_key=item.target_label,
                target_center_x=float(tcx),
                target_center_y=float(tcy),
                is_correct=is_correct,
                predicted_key=pred_name,
                error_px=err,
                raw_features=_feature_snapshot(raw_mean, "raw"),
                smooth_features=_feature_snapshot(smooth_mean, "smooth"),
                core_x=coords["core_x"],
                core_y_raw=coords["core_y_raw"],
                core_y=coords["core_y"],
                row_idx=row_idx,
                row_name=row_name,
                row_bias=coords["row_bias"],
                y_after_row=coords["y_after_row"],
                local_dy=coords["local_dy"],
                y_after_local=coords["y_after_local"],
                y_after_bias=coords["y_after_bias"],
                x_final=x_final,
                y_final=y_final,
                clip_y_min=int(coords["clip_y_min"]),
                clip_y_max=int(coords["clip_y_max"]),
                dy_core=dy_core,
                dy_row=dy_row,
                dy_local=dy_local,
                dy_final=dy_final,
                delta_y_row=coords["y_after_row"] - coords["core_y"],
                delta_y_local=coords["y_after_local"] - coords["y_after_row"],
                delta_y_clamp=y_final - coords["y_after_bias"],
            )
        )

        if raw_mean is not None:
            ranked = rank_calibration_anchors(
                raw_mean,
                calib_samples=calib_samples,
                calib_targets=calib_targets,
            )
            test_avg_v = float(raw_mean.avg_v) if raw_mean.avg_v is not None else float("nan")
            if ranked:
                n1 = ranked[0]
                n2 = ranked[1] if len(ranked) > 1 else (0, "", "", float("nan"), float("nan"), float("nan"))
                n3 = ranked[2] if len(ranked) > 2 else (0, "", "", float("nan"), float("nan"), float("nan"))
                anchor_rows.append(
                    KeyAnchorDistanceRow(
                        target_key=item.target_label,
                        test_avg_v=test_avg_v,
                        nearest_id=n1[1],
                        nearest_label=n1[2],
                        nearest_distance=n1[3],
                        nearest_anchor_y=n1[4],
                        nearest_anchor_avg_v=n1[5],
                        second_id=n2[1],
                        second_label=n2[2],
                        second_distance=n2[3],
                        third_id=n3[1],
                        third_label=n3[2],
                        third_distance=n3[3],
                    )
                )

    return stage_rows, anchor_rows


def write_mapper_stage_csv(
    rows: Sequence[KeyMapperStageRow],
    *,
    path: Optional[Path] = None,
) -> Path:
    dest = path or default_mapper_stages_csv_path()
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=STAGE_CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            row = {
                "target_key": r.target_key,
                "target_center_x": f"{r.target_center_x:.2f}",
                "target_center_y": f"{r.target_center_y:.2f}",
                "is_correct": str(r.is_correct),
                "predicted_key": r.predicted_key,
                "error_px": f"{r.error_px:.2f}",
                **r.raw_features,
                **r.smooth_features,
                "core_x": f"{r.core_x:.2f}",
                "core_y_raw": f"{r.core_y_raw:.2f}",
                "core_y": f"{r.core_y:.2f}",
                "row_idx": str(r.row_idx),
                "row_name": r.row_name,
                "row_bias_applied": f"{r.row_bias:+.2f}",
                "y_after_row": f"{r.y_after_row:.2f}",
                "local_dy": f"{r.local_dy:+.2f}",
                "y_after_local": f"{r.y_after_local:.2f}",
                "y_after_bias": f"{r.y_after_bias:.2f}",
                "x_final": f"{r.x_final:.2f}",
                "y_final": f"{r.y_final:.2f}",
                "clip_y_min": str(r.clip_y_min),
                "clip_y_max": str(r.clip_y_max),
                "dy_core": f"{r.dy_core:+.2f}",
                "dy_row": f"{r.dy_row:+.2f}",
                "dy_local": f"{r.dy_local:+.2f}",
                "dy_final": f"{r.dy_final:+.2f}",
                "delta_y_row": f"{r.delta_y_row:+.2f}",
                "delta_y_local": f"{r.delta_y_local:+.2f}",
                "delta_y_clamp": f"{r.delta_y_clamp:+.2f}",
            }
            writer.writerow(row)
    return dest


def write_anchor_distance_csv(
    rows: Sequence[KeyAnchorDistanceRow],
    *,
    path: Optional[Path] = None,
) -> Path:
    dest = path or default_anchor_distance_csv_path()
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ANCHOR_CSV_FIELDS)
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "target_key": r.target_key,
                    "test_avg_v": f"{r.test_avg_v:.6f}",
                    "nearest_id": r.nearest_id,
                    "nearest_label": r.nearest_label,
                    "nearest_distance": f"{r.nearest_distance:.6f}",
                    "nearest_anchor_y": f"{r.nearest_anchor_y:.2f}",
                    "nearest_anchor_avg_v": f"{r.nearest_anchor_avg_v:.6f}",
                    "second_id": r.second_id,
                    "second_label": r.second_label,
                    "second_distance": f"{r.second_distance:.6f}",
                    "third_id": r.third_id,
                    "third_label": r.third_label,
                    "third_distance": f"{r.third_distance:.6f}",
                }
            )
    return dest


def print_mapper_stage_summary(rows: Sequence[KeyMapperStageRow]) -> None:
    if not rows:
        print("[key_accuracy_mapper] no stage rows")
        return

    print("[key_accuracy_mapper] --- stage breakdown (mean collect window) ---")
    print(
        "[key_accuracy_mapper] "
        f"{'key':<6} {'ok':>2} {'pred':<5} "
        f"{'dy_core':>8} {'dy_row':>8} {'dy_local':>8} {'dy_final':>8} "
        f"{'d_row':>7} {'d_local':>7} {'d_clamp':>7} "
        f"{'row':<3} {'clip':>4}"
    )
    for r in rows:
        clip = ""
        if r.clip_y_min:
            clip = "Ymin"
        elif r.clip_y_max:
            clip = "Ymax"
        print(
            f"[key_accuracy_mapper] "
            f"{r.target_key:<6} {r.is_correct:>2} {r.predicted_key:<5} "
            f"{r.dy_core:+8.1f} {r.dy_row:+8.1f} {r.dy_local:+8.1f} {r.dy_final:+8.1f} "
            f"{r.delta_y_row:+7.1f} {r.delta_y_local:+7.1f} {r.delta_y_clamp:+7.1f} "
            f"{r.row_name:<3} {clip:>4}"
        )

    fails = [r for r in rows if not r.is_correct]
    if fails:
        print("[key_accuracy_mapper] --- where Y error is introduced (failing keys) ---")
        for r in fails:
            stages = [
                ("core", abs(r.dy_core)),
                ("row_bias", abs(r.dy_row)),
                ("local_y", abs(r.dy_local)),
                ("final", abs(r.dy_final)),
            ]
            worst = max(stages, key=lambda t: t[1])
            improved = abs(r.dy_core) - abs(r.dy_final)
            print(
                f"[key_accuracy_mapper]   {r.target_key}: "
                f"core_y={r.core_y:.1f} final_y={r.y_final:.1f} target_y={r.target_center_y:.1f} "
                f"largest |dy| at {worst[0]} ({worst[1]:.1f}px); "
                f"net correction {improved:+.1f}px vs core"
            )


def print_anchor_distance_summary(rows: Sequence[KeyAnchorDistanceRow]) -> None:
    if not rows:
        print("[key_accuracy_mapper] no anchor distance rows")
        return
    print("[key_accuracy_mapper] --- nearest calibration anchors (PCA4 feature distance) ---")
    for r in rows:
        print(
            f"[key_accuracy_mapper]   {r.target_key}: test_avg_v={r.test_avg_v:.4f} "
            f"nearest={r.nearest_label} ({r.nearest_distance:.4f}) anchor_y={r.nearest_anchor_y:.0f} "
            f"anchor_avg_v={r.nearest_anchor_avg_v:.4f}; "
            f"2nd={r.second_label} ({r.second_distance:.4f}); "
            f"3rd={r.third_label} ({r.third_distance:.4f})"
        )


def run_keyboard_accuracy_mapper_diagnostics(
    *,
    recorded: Sequence[RecordedKeyFrames],
    keys: Sequence[KeyGeometryRow],
    model: object,
    calib_samples: Sequence[Tuple[FrameFeatures, Tuple[float, float]]],
    calib_targets: Sequence[CalibrationTarget],
    gaze_bias_x: float = 0.0,
    gaze_bias_y: float = 0.0,
    clamp_xy: Optional[Callable[[float, float], Tuple[float, float]]] = None,
    feature_smoother_alpha: float = DEFAULT_FEATURE_SMOOTHER_ALPHA,
    stages_csv: Optional[Path] = None,
    anchor_csv: Optional[Path] = None,
    verbose: bool = True,
) -> Tuple[List[KeyMapperStageRow], List[KeyAnchorDistanceRow]]:
    """Run diagnostics, write CSVs, and print summaries."""
    if not recorded:
        if verbose:
            print("[key_accuracy_mapper] skipped: no recorded gaze frames")
        return [], []
    if not calib_samples or not calib_targets:
        if verbose:
            print("[key_accuracy_mapper] skipped: no calibration samples/targets")
        return [], []

    stage_rows, anchor_rows = diagnose_recorded_keys(
        recorded=recorded,
        keys=keys,
        model=model,
        calib_samples=calib_samples,
        calib_targets=calib_targets,
        gaze_bias_x=gaze_bias_x,
        gaze_bias_y=gaze_bias_y,
        clamp_xy=clamp_xy,
        feature_smoother_alpha=feature_smoother_alpha,
    )
    stages_path = write_mapper_stage_csv(stage_rows, path=stages_csv)
    anchor_path = write_anchor_distance_csv(anchor_rows, path=anchor_csv)
    if verbose:
        print(f"[key_accuracy_mapper] wrote stage CSV -> {stages_path}")
        print(f"[key_accuracy_mapper] wrote anchor distance CSV -> {anchor_path}")
        print_mapper_stage_summary(stage_rows)
        print_anchor_distance_summary(anchor_rows)
    return stage_rows, anchor_rows
