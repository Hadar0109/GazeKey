"""Complete per-benchmark diagnostics record (reporting only).

Purpose (Phase 8, post-Iteration-3): the lightweight benchmark summary in
``run_summary.py`` persists only *failed* keys (``per_key_misses``). That makes
residual analysis miss-biased and prevents data-driven experiment selection
(see ``runs/iteration_03_row_y_bias.txt`` Verification §3).

This module persists **all** benchmark target results (hits + misses) plus the
metadata needed to compare experiment outcomes: selected ridge alpha, mapper
config / correction-layer flags, calibration target geometry, runtime smoothing,
per-target predicted/target points, row assignments, and residual/error
statistics (overall, by row, hits-vs-misses).

It is strictly **read-only** with respect to mapping: it only serializes values
passed in by the caller. It never predicts, fits, tunes, or mutates a mapper.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Optional, Sequence

from tools.evaluation.benchmark_runner import KeyAccuracyResultRow

SCHEMA_VERSION = 1


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_float_tuple(value: Any) -> Optional[List[float]]:
    if value is None:
        return None
    try:
        return [float(v) for v in value]
    except (TypeError, ValueError):
        return None


def _stats_for(values: Sequence[float]) -> dict[str, Any]:
    """Min/max/mean/median/std for a 1-D sample (null fields when empty)."""
    vals = [float(v) for v in values]
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None, "std": None}
    ordered = sorted(vals)
    mid = n // 2
    median = ordered[mid] if n % 2 == 1 else (ordered[mid - 1] + ordered[mid]) / 2.0
    mean = sum(vals) / n
    var = sum((v - mean) ** 2 for v in vals) / n
    return {
        "n": n,
        "mean": mean,
        "median": median,
        "min": min(vals),
        "max": max(vals),
        "std": var ** 0.5,
    }


def _residual_block(rows: Sequence[KeyAccuracyResultRow]) -> dict[str, Any]:
    """dx / dy / |dx| / |dy| / err statistics for a group of result rows."""
    return {
        "dx": _stats_for([r.dx for r in rows]),
        "dy": _stats_for([r.dy for r in rows]),
        "abs_dx": _stats_for([abs(r.dx) for r in rows]),
        "abs_dy": _stats_for([abs(r.dy) for r in rows]),
        "error_px": _stats_for([r.error_px for r in rows]),
    }


def compute_residual_stats(rows: Sequence[KeyAccuracyResultRow]) -> dict[str, Any]:
    """Residual statistics across ALL targets, by target row, and hits vs misses."""
    rows = list(rows)
    by_row: dict[str, Any] = {}
    row_indices = sorted({int(r.target_row_index) for r in rows})
    for ri in row_indices:
        group = [r for r in rows if int(r.target_row_index) == ri]
        block = _residual_block(group)
        block["keys"] = [r.target_key for r in group]
        block["keys_correct"] = sum(1 for r in group if r.is_correct)
        block["rows_correct"] = sum(1 for r in group if r.row_correct)
        by_row[str(ri)] = block
    hits = [r for r in rows if r.is_correct]
    misses = [r for r in rows if not r.is_correct]
    return {
        "overall": _residual_block(rows),
        "by_target_row": by_row,
        "hits": {**_residual_block(hits), "keys": [r.target_key for r in hits]},
        "misses": {**_residual_block(misses), "keys": [r.target_key for r in misses]},
    }


def _result_row_to_dict(r: KeyAccuracyResultRow) -> dict[str, Any]:
    return {
        "target_key": r.target_key,
        "target_x": float(r.target_center_x),
        "target_y": float(r.target_center_y),
        "pred_x": float(r.predicted_x),
        "pred_y": float(r.predicted_y),
        "predicted_key": r.predicted_key,
        "dx": float(r.dx),
        "dy": float(r.dy),
        "error_px": float(r.error_px),
        "target_row_index": int(r.target_row_index),
        "predicted_row_index": int(r.predicted_row_index),
        "is_correct": bool(r.is_correct),
        "row_correct": bool(r.row_correct),
    }


def _calibration_target_to_dict(t: Any) -> dict[str, Any]:
    if is_dataclass(t):
        d = asdict(t)
        return {
            "target_id": d.get("target_id"),
            "label": d.get("label"),
            "key_id": d.get("key_id"),
            "screen_x": _to_float(d.get("screen_x")),
            "screen_y": _to_float(d.get("screen_y")),
            "grid_row": d.get("grid_row"),
            "grid_col": d.get("grid_col"),
        }
    return {
        "target_id": getattr(t, "target_id", None),
        "label": getattr(t, "label", None),
        "key_id": getattr(t, "key_id", None),
        "screen_x": _to_float(getattr(t, "screen_x", None)),
        "screen_y": _to_float(getattr(t, "screen_y", None)),
        "grid_row": getattr(t, "grid_row", None),
        "grid_col": getattr(t, "grid_col", None),
    }


def _mapper_metadata(model: Any) -> dict[str, Any]:
    """Read-only snapshot of the active mapper's reportable attributes."""
    meta: dict[str, Any] = {
        "mapper_type": getattr(model, "mapper_type", None),
        "ridge_alpha": _to_float(getattr(model, "alpha", None)),
        "row_y_centers": _to_float_tuple(getattr(model, "row_y_centers", None)),
        "row_y_bias": _to_float_tuple(getattr(model, "row_y_bias", None)),
        "has_row_y_bias_layer": hasattr(model, "row_y_bias"),
    }
    clip = getattr(model, "clip_bounds", None)
    meta["clip_bounds"] = _to_float_tuple(clip) if clip is not None else None
    loocv = getattr(model, "leave_one_out_rms_px", None)
    if callable(loocv):
        try:
            meta["loocv_rms_px"] = _to_float(loocv())
        except Exception:
            meta["loocv_rms_px"] = None
    else:
        meta["loocv_rms_px"] = None
    return meta


def _config_metadata() -> dict[str, Any]:
    """GazeFollower evaluation metadata (PCA4 mapper config deleted in Stage G)."""
    return {
        "typing_candidate_id": None,
        "active_mapper": "gazefollower",
        "calibration_mode": "official",
        "alpha_grid": None,
        "min_alpha": None,
        "apply_row_y_bias": False,
        "apply_local_y_correction": False,
        "feature_smoother_alpha_default": None,
        "gaze_smoother_alpha_default": None,
    }


def build_benchmark_diagnostics(
    *,
    session_id: str,
    rows: Sequence[KeyAccuracyResultRow],
    metrics: Any,
    status: str,
    failure_reason: Optional[str] = None,
    likely_cause: str = "unknown",
    model: Any = None,
    calibration_targets: Optional[Iterable[Any]] = None,
    calibration_loocv_rms_px: Optional[float] = None,
    feature_smoother_alpha: Optional[float] = None,
    gaze_smoother_alpha: Optional[float] = None,
    gaze_bias_x: Optional[float] = None,
    gaze_bias_y: Optional[float] = None,
    thresholds: Any = None,
    active_calibration_mode: Optional[str] = None,
) -> dict[str, Any]:
    """Assemble the full diagnostics record (does not write anything)."""
    from tools.evaluation.run_summary import benchmark_thresholds, display_key_hit_pct

    rows = list(rows)
    t = thresholds or benchmark_thresholds()

    metrics_block = {
        "keys_correct": int(getattr(metrics, "keys_correct", 0)),
        "keys_total": int(getattr(metrics, "keys_total", len(rows))),
        "key_hit_pct": display_key_hit_pct(
            int(getattr(metrics, "keys_correct", 0)),
            int(getattr(metrics, "keys_total", len(rows))),
        ),
        "rows_correct": int(getattr(metrics, "rows_correct", 0)),
        "row_accuracy_pct": 100.0 * float(getattr(metrics, "row_accuracy", 0.0)),
        "median_error_px": _to_float(getattr(metrics, "median_pixel_error", None)),
    }

    mapper_block = _mapper_metadata(model) if model is not None else {}
    if calibration_loocv_rms_px is not None:
        mapper_block["calibration_loocv_rms_px"] = _to_float(calibration_loocv_rms_px)

    runtime_block = {
        "feature_smoother_alpha": _to_float(feature_smoother_alpha),
        "gaze_smoother_alpha": _to_float(gaze_smoother_alpha),
        "gaze_bias_x": _to_float(gaze_bias_x),
        "gaze_bias_y": _to_float(gaze_bias_y),
    }

    cal_targets = (
        [_calibration_target_to_dict(t_) for t_ in calibration_targets]
        if calibration_targets is not None
        else None
    )

    config_block = _config_metadata()
    if active_calibration_mode is not None:
        # Record the layout actually used this run (e.g. T032 candidate via env override),
        # which may differ from the static configured CALIBRATION_MODE.
        config_block["calibration_mode"] = str(active_calibration_mode)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_type": "benchmark",
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": status,
        "failure_reason": failure_reason,
        "likely_cause": likely_cause,
        "thresholds": {
            "benchmark_key_count": int(getattr(t, "benchmark_key_count", 15)),
            "min_keys_correct": int(getattr(t, "min_keys_correct", 10)),
            "max_median_error_px": _to_float(getattr(t, "max_median_error_px", None)),
            "min_row_accuracy": _to_float(getattr(t, "min_row_accuracy", None)),
            "max_session_spread_fraction": _to_float(
                getattr(t, "max_session_spread_fraction", None)
            ),
        },
        "metrics": metrics_block,
        "mapper": mapper_block,
        "config": config_block,
        "runtime": runtime_block,
        "calibration_targets": cal_targets,
        "targets": [_result_row_to_dict(r) for r in rows],
        "residual_stats": compute_residual_stats(rows),
    }


def diagnostics_path(session_id: str, runs_dir: Optional[Path] = None) -> Path:
    from tools.evaluation.session_paths import benchmark_diag_path, runs_root

    return benchmark_diag_path(session_id, runs_dir=runs_dir or runs_root())


def write_benchmark_diagnostics(
    diagnostics: dict[str, Any],
    *,
    session_id: str,
    runs_dir: Optional[Path] = None,
) -> Path:
    """Persist diagnostics JSON under ``runs/<session_id>/benchmark_diag.json``."""
    from tools.evaluation.session_paths import benchmark_diag_path, ensure_session_dir, runs_root

    root = runs_dir or runs_root()
    ensure_session_dir(session_id, runs_dir=root)
    path = benchmark_diag_path(session_id, runs_dir=root)
    path.write_text(json.dumps(diagnostics, indent=2, sort_keys=False), encoding="utf-8")
    return path
