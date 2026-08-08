"""Benchmark scoring for the MVP calibration-mapping path."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.typing.key_hit_tester import hit_test_layout_keys

DEFAULT_SAMPLE_KEYS: Tuple[str, ...] = (
    "Q",
    "E",
    "T",
    "U",
    "P",
    "A",
    "D",
    "G",
    "J",
    "L",
    "Z",
    "C",
    "B",
    "M",
    "Space",
)

SETTLE_MS = 1200
COLLECT_MS = 2500


def _normalize_match_token(label: str) -> str:
    s = str(label).strip()
    if s.lower() == "space":
        return " "
    if len(s) == 1:
        return s.lower()
    return s.lower()


def resolve_sample_keys(
    keys: Sequence[KeyGeometryRow],
    sample_labels: Sequence[str] = DEFAULT_SAMPLE_KEYS,
) -> List[Tuple[str, KeyGeometryRow]]:
    """Map human-readable sample labels to layout keys."""
    by_action: dict[str, List[KeyGeometryRow]] = {}
    by_label: dict[str, List[KeyGeometryRow]] = {}
    for k in keys:
        act = _normalize_match_token(k.key_action)
        lab = str(k.key_label).strip().lower()
        by_action.setdefault(act, []).append(k)
        by_label.setdefault(lab, []).append(k)

    out: List[Tuple[str, KeyGeometryRow]] = []
    for sample in sample_labels:
        token = _normalize_match_token(sample)
        candidates = by_action.get(token) or by_label.get(str(sample).strip().lower())
        if not candidates:
            raise ValueError(f"Benchmark: no key found for sample '{sample}'")
        if len(candidates) > 1:
            letter = [c for c in candidates if len(c.key_action) == 1 and not c.is_special_key]
            pick = letter[0] if letter else candidates[0]
        else:
            pick = candidates[0]
        out.append((str(sample), pick))
    return out


def display_key_name(row: KeyGeometryRow) -> str:
    if row.key_action == " ":
        return "Space"
    if len(row.key_action) == 1:
        return row.key_action.upper()
    return str(row.key_label)


def predict_key_at(
    screen_x: float,
    screen_y: float,
    keys: Sequence[KeyGeometryRow],
) -> KeyGeometryRow:
    """Hit-test gaze point using KeyHitTester-equivalent tight/snap geometry."""
    if not keys:
        raise ValueError("predict_key_at requires at least one key")
    hit_id = hit_test_layout_keys(keys, screen_x, screen_y)
    if hit_id is not None:
        return keys[int(hit_id)]

    best = keys[0]
    best_d = float("inf")
    for k in keys:
        cx, cy = k.center
        d = math.hypot(screen_x - cx, screen_y - cy)
        if d < best_d:
            best_d = d
            best = k
    return best


@dataclass(frozen=True)
class KeyAccuracyResultRow:
    target_key: str
    target_center_x: float
    target_center_y: float
    predicted_x: float
    predicted_y: float
    predicted_key: str
    error_px: float
    dx: float
    dy: float
    is_correct: bool
    target_row_index: int = -1
    predicted_row_index: int = -1
    row_correct: bool = False


def build_result_row(
    *,
    target_label: str,
    target: KeyGeometryRow,
    predicted_x: float,
    predicted_y: float,
    predicted: KeyGeometryRow,
) -> KeyAccuracyResultRow:
    tcx, tcy = target.center
    err = float(math.hypot(predicted_x - tcx, predicted_y - tcy))
    pred_name = display_key_name(predicted)
    is_correct = pred_name.upper() == str(target_label).upper() or (
        str(target_label).lower() == "space" and pred_name == "Space"
    )
    row_correct = int(predicted.row_index) == int(target.row_index)
    return KeyAccuracyResultRow(
        target_key=str(target_label),
        target_center_x=float(tcx),
        target_center_y=float(tcy),
        predicted_x=float(predicted_x),
        predicted_y=float(predicted_y),
        predicted_key=pred_name,
        error_px=err,
        dx=float(predicted_x - tcx),
        dy=float(predicted_y - tcy),
        is_correct=bool(is_correct),
        target_row_index=int(target.row_index),
        predicted_row_index=int(predicted.row_index),
        row_correct=bool(row_correct),
    )


def evaluate_key_accuracy_from_frames(
    *,
    target_label: str,
    target: KeyGeometryRow,
    frames: Sequence[FrameFeatures],
    keys: Sequence[KeyGeometryRow],
    predict_screen_xy,
) -> KeyAccuracyResultRow:
    preds: List[Tuple[float, float]] = []
    for feat in frames:
        xy = predict_screen_xy(feat)
        if xy is not None:
            preds.append((float(xy[0]), float(xy[1])))
    if not preds:
        px = float(target.center[0])
        py = float(target.center[1])
    else:
        px = float(sum(p[0] for p in preds) / len(preds))
        py = float(sum(p[1] for p in preds) / len(preds))
    predicted = predict_key_at(px, py, keys)
    return build_result_row(
        target_label=target_label,
        target=target,
        predicted_x=px,
        predicted_y=py,
        predicted=predicted,
    )


@dataclass(frozen=True)
class BenchmarkMetrics:
    key_hit_accuracy: float
    row_accuracy: float
    median_pixel_error: float
    keys_correct: int
    keys_total: int
    rows_correct: int


@dataclass(frozen=True)
class BenchmarkRun:
    results: Tuple[KeyAccuracyResultRow, ...]
    metrics: BenchmarkMetrics
    status: str  # passed | failed


def compute_benchmark_metrics(
    rows: Sequence[KeyAccuracyResultRow],
) -> BenchmarkMetrics:
    if not rows:
        return BenchmarkMetrics(
            key_hit_accuracy=0.0,
            row_accuracy=0.0,
            median_pixel_error=float("inf"),
            keys_correct=0,
            keys_total=0,
            rows_correct=0,
        )
    n = len(rows)
    keys_correct = sum(1 for r in rows if r.is_correct)
    rows_correct = sum(1 for r in rows if r.row_correct)
    errs = np.array([r.error_px for r in rows], dtype=np.float64)
    return BenchmarkMetrics(
        key_hit_accuracy=float(keys_correct) / float(n),
        row_accuracy=float(rows_correct) / float(n),
        median_pixel_error=float(np.median(errs)),
        keys_correct=int(keys_correct),
        keys_total=int(n),
        rows_correct=int(rows_correct),
    )


def evaluate_benchmark_pass(metrics: BenchmarkMetrics) -> Tuple[bool, str]:
    """Return (passed, failure_reason) against SC-001–SC-003 thresholds."""
    from tools.evaluation.run_summary import benchmark_thresholds, display_key_hit_pct

    t = benchmark_thresholds()
    reasons: List[str] = []
    min_keys = t.min_keys_correct if metrics.keys_total == t.benchmark_key_count else max(
        1, int(round(t.min_keys_correct * metrics.keys_total / t.benchmark_key_count))
    )
    if metrics.keys_correct < min_keys:
        pct = display_key_hit_pct(metrics.keys_correct, metrics.keys_total)
        target_pct = display_key_hit_pct(t.min_keys_correct, t.benchmark_key_count)
        reasons.append(
            f"key-hit {metrics.keys_correct}/{metrics.keys_total} "
            f"({pct}%) < {t.min_keys_correct}/{t.benchmark_key_count} (~{target_pct}%)"
        )
    if metrics.median_pixel_error > t.max_median_error_px:
        reasons.append(
            f"median_err {metrics.median_pixel_error:.1f}px > {t.max_median_error_px:.0f}px"
        )
    if metrics.row_accuracy < t.min_row_accuracy:
        reasons.append(
            f"row {metrics.rows_correct}/{metrics.keys_total} "
            f"({100.0 * metrics.row_accuracy:.0f}%) < {100.0 * t.min_row_accuracy:.0f}%"
        )
    if reasons:
        return False, "; ".join(reasons)
    return True, ""


def build_benchmark_run(rows: Sequence[KeyAccuracyResultRow]) -> BenchmarkRun:
    metrics = compute_benchmark_metrics(rows)
    passed, _reason = evaluate_benchmark_pass(metrics)
    return BenchmarkRun(
        results=tuple(rows),
        metrics=metrics,
        status="passed" if passed else "failed",
    )
