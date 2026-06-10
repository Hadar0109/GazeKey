"""Timed benchmark session: settle + collect per key, score via benchmark_runner."""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple

from gazekey.evaluation.benchmark_runner import (
    COLLECT_MS,
    KeyAccuracyResultRow,
    SETTLE_MS,
    evaluate_key_accuracy_from_frames,
    resolve_sample_keys,
)
from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow


class BenchmarkEvalSession:
    """Timed settle + collect session over a fixed key sample list."""

    def __init__(
        self,
        samples: Sequence[Tuple[str, KeyGeometryRow]],
        *,
        keys_for_hit_test: Sequence[KeyGeometryRow],
        predict_screen_xy: Callable[[FrameFeatures], Optional[Tuple[float, float]]],
        on_collect_begin: Optional[Callable[[], None]] = None,
        settle_ms: int = SETTLE_MS,
        collect_ms: int = COLLECT_MS,
    ) -> None:
        self._samples = list(samples)
        self._keys = list(keys_for_hit_test)
        self._predict_screen_xy = predict_screen_xy
        self._on_collect_begin = on_collect_begin
        self._settle_ms = int(settle_ms)
        self._collect_ms = int(collect_ms)
        self._index = 0
        self._phase = "settle"
        self._phase_start_ms = 0
        self._collect_features: List[FrameFeatures] = []
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
        self._collect_features = []
        self._results = []

    def tick(
        self,
        now_ms: int,
        features: Optional[FrameFeatures] = None,
    ) -> Optional[KeyAccuracyResultRow]:
        if self.finished:
            return None
        elapsed = int(now_ms) - int(self._phase_start_ms)
        if self._phase == "settle":
            if elapsed < self._settle_ms:
                return None
            self._phase = "collect"
            self._phase_start_ms = int(now_ms)
            self._collect_features = []
            if self._on_collect_begin is not None:
                self._on_collect_begin()
            return None

        if self._phase == "collect":
            if features is not None:
                self._collect_features.append(features)
            if elapsed < self._collect_ms:
                return None
            return self._finish_current_key(int(now_ms))
        return None

    def _finish_current_key(self, now_ms: int) -> KeyAccuracyResultRow:
        label, target = self._samples[self._index]
        frames = tuple(self._collect_features)
        row = evaluate_key_accuracy_from_frames(
            target_label=label,
            target=target,
            frames=frames,
            keys=self._keys,
            predict_screen_xy=self._predict_screen_xy,
        )
        self._results.append(row)
        self._index += 1
        self._collect_features = []
        if not self.finished:
            self._phase = "settle"
            self._phase_start_ms = int(now_ms)
        return row


__all__ = ["BenchmarkEvalSession", "resolve_sample_keys"]
