"""GazeFollower evaluation scoring: GazeSample screen points + live QRects.

Does not import or call FeatureExtractor, Ridge, PCA4, or MapperRuntime predict.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from gazekey.backend.gaze_sample import GazeSample
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.typing.key_hit_tester import hit_test_layout_keys
from tools.evaluation.benchmark_runner import (
    COLLECT_MS,
    SETTLE_MS,
    KeyAccuracyResultRow,
    build_result_row,
    point_in_tight_rect,
    predict_key_at,
    slice_flags_for_label,
)
from tools.evaluation.benchmark_session import resolve_sample_keys

_FORBIDDEN_SCORING_TOKENS = (
    "FeatureExtractor",
    "Pca4BaselineMapper",
    "MapperRuntime",
    "key_accuracy_predict_screen_xy",
    "pca_vL",
    "pca_vR",
    "Ridge",
)


def _median_xy(preds: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    xs = sorted(p[0] for p in preds)
    ys = sorted(p[1] for p in preds)
    mid = len(xs) // 2
    if len(xs) % 2:
        return float(xs[mid]), float(ys[mid])
    return (float(xs[mid - 1] + xs[mid]) / 2.0, float(ys[mid - 1] + ys[mid]) / 2.0)


def screen_points_from_samples(samples: Sequence[GazeSample]) -> List[Tuple[float, float]]:
    return [(float(s.x), float(s.y)) for s in samples if bool(s.valid)]


def evaluate_key_accuracy_from_screen_points(
    *,
    target_label: str,
    target: KeyGeometryRow,
    points: Sequence[Tuple[float, float]],
    keys: Sequence[KeyGeometryRow],
    calibration_labels: Optional[Sequence[str]] = None,
    held_out_letters: Optional[Sequence[str]] = None,
) -> KeyAccuracyResultRow:
    """Score already-mapped GazeSample screen points against live layout QRects."""
    clamped: List[Tuple[float, float]] = []
    intended_hits = 0
    for px, py in points:
        x, y = float(px), float(py)
        clamped.append((x, y))
        hit_id = hit_test_layout_keys(keys, x, y)
        if hit_id is not None:
            hit = keys[int(hit_id)]
            if hit.key_id and target.key_id and hit.key_id == target.key_id:
                intended_hits += 1
            elif str(hit.key_action) == str(target.key_action):
                intended_hits += 1

    if not clamped:
        px = float(target.center[0])
        py = float(target.center[1])
    else:
        px, py = _median_xy(clamped)

    inside = point_in_tight_rect(target, px, py)
    hit_id = hit_test_layout_keys(keys, px, py)
    if hit_id is not None:
        predicted = keys[int(hit_id)]
    else:
        predicted = predict_key_at(px, py, keys)

    was_cal, in_held, in_edit = slice_flags_for_label(
        target_label,
        calibration_labels=calibration_labels,
        held_out_letters=held_out_letters,
    )
    stability = float(intended_hits) / float(len(clamped)) if clamped else 0.0
    return build_result_row(
        target_label=target_label,
        target=target,
        predicted_x=px,
        predicted_y=py,
        predicted=predicted,
        inside_tight=inside,
        focus_stability=stability,
        was_calibration_location=was_cal,
        in_held_out_letter_slice=in_held,
        in_editing_control_slice=in_edit,
        collect_frames=int(len(clamped)),
    )


class GazeSampleEvalSession:
    """Settle + collect GazeSample screen points; no FeatureExtractor predict."""

    def __init__(
        self,
        samples: Sequence[Tuple[str, KeyGeometryRow]],
        *,
        keys_for_hit_test: Sequence[KeyGeometryRow],
        on_key_begin=None,
        settle_ms: int = SETTLE_MS,
        collect_ms: int = COLLECT_MS,
        calibration_labels: Optional[Sequence[str]] = None,
        held_out_letters: Optional[Sequence[str]] = None,
    ) -> None:
        self._samples = list(samples)
        self._keys = list(keys_for_hit_test)
        self._on_key_begin = on_key_begin
        self._settle_ms = int(settle_ms)
        self._collect_ms = int(collect_ms)
        self._calibration_labels = list(calibration_labels) if calibration_labels is not None else None
        self._held_out_letters = list(held_out_letters) if held_out_letters is not None else None
        self._index = 0
        self._phase = "settle"
        self._phase_start_ms = 0
        self._collect_points: List[Tuple[float, float]] = []
        self._results: List[KeyAccuracyResultRow] = []

    @property
    def finished(self) -> bool:
        return self._index >= len(self._samples)

    @property
    def results(self) -> List[KeyAccuracyResultRow]:
        return list(self._results)

    def current_sample(self) -> Optional[Tuple[str, KeyGeometryRow]]:
        if self.finished:
            return None
        return self._samples[self._index]

    def instruction_text(self) -> str:
        cur = self.current_sample()
        if cur is None:
            return "Benchmark complete"
        label, _row = cur
        if self._phase == "settle":
            return f"Look at key: {label}  (settling…)"
        return f"Look at key: {label}  (collecting…)"

    def begin(self, now_ms: int) -> None:
        self._index = 0
        self._phase = "settle"
        self._phase_start_ms = int(now_ms)
        self._collect_points = []
        self._results = []
        if self._on_key_begin is not None:
            self._on_key_begin()

    def tick_sample(self, now_ms: int, sample: GazeSample) -> Optional[KeyAccuracyResultRow]:
        if self.finished:
            return None
        elapsed = int(now_ms) - int(self._phase_start_ms)
        if self._phase == "settle":
            if elapsed < self._settle_ms:
                return None
            self._phase = "collect"
            self._phase_start_ms = int(now_ms)
            self._collect_points = []
            return None
        if self._phase == "collect":
            if sample.valid:
                self._collect_points.append((float(sample.x), float(sample.y)))
            if elapsed < self._collect_ms:
                return None
            return self._finish_current_key(int(now_ms))
        return None

    def _finish_current_key(self, now_ms: int) -> KeyAccuracyResultRow:
        label, target = self._samples[self._index]
        row = evaluate_key_accuracy_from_screen_points(
            target_label=label,
            target=target,
            points=tuple(self._collect_points),
            keys=self._keys,
            calibration_labels=self._calibration_labels,
            held_out_letters=self._held_out_letters,
        )
        self._results.append(row)
        self._index += 1
        self._collect_points = []
        if not self.finished:
            self._phase = "settle"
            self._phase_start_ms = int(now_ms)
            if self._on_key_begin is not None:
                self._on_key_begin()
        return row


def write_gaze_replay(
    samples: Sequence[GazeSample],
    *,
    path: Path,
    provenance: Optional[dict] = None,
) -> Path:
    """Optional JSONL GazeSample capture. No webcam frames. Caller gitignores path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if provenance:
            handle.write(json.dumps({"type": "provenance", **provenance}) + "\n")
        for sample in samples:
            handle.write(
                json.dumps(
                    {
                        "type": "gaze_sample",
                        "timestamp_ns": sample.timestamp_ns,
                        "valid": sample.valid,
                        "x": sample.x,
                        "y": sample.y,
                        "tracking_state": sample.tracking_state,
                        "left_openness": sample.left_openness,
                        "right_openness": sample.right_openness,
                    }
                )
                + "\n"
            )
    return path


__all__ = [
    "GazeSampleEvalSession",
    "evaluate_key_accuracy_from_screen_points",
    "resolve_sample_keys",
    "screen_points_from_samples",
    "write_gaze_replay",
    "_FORBIDDEN_SCORING_TOKENS",
]
