"""Keyboard-level gaze mapping accuracy evaluation (post-calibration diagnostic)."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from PySide6.QtCore import QPoint, QRect

from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.features.feature_types import FrameFeatures
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.mapping.typing_candidate import FEATURE_SMOOTHER_ALPHA

DEFAULT_FEATURE_SMOOTHER_ALPHA = FEATURE_SMOOTHER_ALPHA


def mean_frame_features(frames: Sequence[FrameFeatures]) -> Optional[FrameFeatures]:
    """Average numeric fields across collected frames."""
    if not frames:
        return None

    def mean_opt(name: str) -> Optional[float]:
        vals = [
            float(getattr(f, name))
            for f in frames
            if getattr(f, name) is not None and np.isfinite(float(getattr(f, name)))
        ]
        if not vals:
            return None
        return float(np.mean(np.asarray(vals, dtype=np.float64)))

    base = frames[-1]
    return FrameFeatures(
        timestamp_ms=int(base.timestamp_ms),
        face_detected=True,
        blink=False,
        confidence=1.0,
        Lh=mean_opt("Lh"),
        Lv=mean_opt("Lv"),
        Rh=mean_opt("Rh"),
        Rv=mean_opt("Rv"),
        avg_h=mean_opt("avg_h"),
        avg_v=mean_opt("avg_v"),
        eye_box_w=mean_opt("eye_box_w"),
        eye_box_h=mean_opt("eye_box_h"),
        face_x=mean_opt("face_x"),
        face_y=mean_opt("face_y"),
        pca_uL=mean_opt("pca_uL"),
        pca_vL=mean_opt("pca_vL"),
        pca_uR=mean_opt("pca_uR"),
        pca_vR=mean_opt("pca_vR"),
    )

# Default sample: left/center/right, top/mid/bottom, edges, space.
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

CSV_FIELDNAMES = (
    "target_key",
    "target_center_x",
    "target_center_y",
    "predicted_x",
    "predicted_y",
    "predicted_key",
    "error_px",
    "dx",
    "dy",
    "is_correct",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_key_accuracy_debug_path() -> Path:
    return _repo_root() / "key_accuracy_debug.csv"


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
    """
    Map human-readable sample labels (e.g. 'Q', 'Space') to layout keys.

    Raises ValueError if any sample cannot be resolved uniquely.
    """
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
            raise ValueError(f"Keyboard accuracy: no key found for sample '{sample}'")
        if len(candidates) > 1:
            # Prefer letter keys over duplicates (e.g. symbols layout hidden).
            letter = [c for c in candidates if len(c.key_action) == 1 and not c.is_special_key]
            pick = letter[0] if letter else candidates[0]
        else:
            pick = candidates[0]
        out.append((str(sample), pick))
    return out


def predict_key_at(
    screen_x: float,
    screen_y: float,
    keys: Sequence[KeyGeometryRow],
) -> KeyGeometryRow:
    """
    Hit-test gaze point against key rects; if none contain the point, pick nearest center.
    """
    if not keys:
        raise ValueError("predict_key_at requires at least one key")
    point = QPoint(int(screen_x), int(screen_y))
    containing = [k for k in keys if k.rect.contains(point)]
    if containing:
        containing.sort(key=lambda k: k.rect.width() * k.rect.height())
        return containing[0]

    best = keys[0]
    best_d = float("inf")
    for k in keys:
        cx, cy = k.center
        d = math.hypot(screen_x - cx, screen_y - cy)
        if d < best_d:
            best_d = d
            best = k
    return best


def display_key_name(row: KeyGeometryRow) -> str:
    if row.key_action == " ":
        return "Space"
    if len(row.key_action) == 1:
        return row.key_action.upper()
    return str(row.key_label)


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


def predict_key_accuracy_screen_xy(
    raw: FrameFeatures,
    *,
    model: object,
    feature_smoother: PcaFeatureSmoother,
    gaze_bias_x: float = 0.0,
    gaze_bias_y: float = 0.0,
    clamp_xy: Optional[Callable[[float, float], Tuple[float, float]]] = None,
    min_quality: Optional[float] = None,
) -> Optional[Tuple[float, float]]:
    """Shared live/replay path: smooth PCA features, predict, bias, clip, quality gate."""
    smooth = feature_smoother.smooth(raw)
    pred = model.predict(smooth)
    if pred is None:
        return None
    if min_quality is not None and pred.quality is not None and float(pred.quality) < float(min_quality):
        return None
    px = float(pred.x) + float(gaze_bias_x)
    py = float(pred.y) + float(gaze_bias_y)
    if clamp_xy is not None:
        px, py = clamp_xy(px, py)
    return px, py


def evaluate_key_accuracy_from_frames(
    *,
    target_label: str,
    target: KeyGeometryRow,
    frames: Sequence[FrameFeatures],
    keys: Sequence[KeyGeometryRow],
    predict_screen_xy: Callable[[FrameFeatures], Optional[Tuple[float, float]]],
) -> KeyAccuracyResultRow:
    """
    Mean of per-frame screen predictions over the collect window, then full-key hit-test.

    Uses the same aggregation recipe for live keyboard accuracy and compare replay.
    """
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


def build_result_row(
    *,
    target_label: str,
    target: KeyGeometryRow,
    predicted_x: float,
    predicted_y: float,
    predicted: KeyGeometryRow,
) -> KeyAccuracyResultRow:
    tcx, tcy = target.center
    pcx, pcy = predicted.center
    err = float(math.hypot(predicted_x - tcx, predicted_y - tcy))
    pred_name = display_key_name(predicted)
    is_correct = pred_name.upper() == str(target_label).upper() or (
        str(target_label).lower() == "space" and pred_name == "Space"
    )
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
    )


@dataclass(frozen=True)
class RecordedKeyFrames:
    """Per-key raw gaze frames captured during the collect window (for compare replay)."""

    target_label: str
    target: KeyGeometryRow
    frames: Tuple[FrameFeatures, ...]


class KeyboardAccuracyEvalSession:
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
        self._recorded_gaze: List[RecordedKeyFrames] = []

    @property
    def finished(self) -> bool:
        return self._index >= len(self._samples)

    @property
    def results(self) -> List[KeyAccuracyResultRow]:
        return list(self._results)

    @property
    def recorded_gaze(self) -> List[RecordedKeyFrames]:
        return list(self._recorded_gaze)

    def current_sample(self) -> Optional[Tuple[str, KeyGeometryRow]]:
        if self.finished:
            return None
        return self._samples[self._index]

    def instruction_text(self) -> str:
        cur = self.current_sample()
        if cur is None:
            return "Keyboard accuracy debug complete"
        label, _row = cur
        if self._phase == "settle":
            return f"Look at key: {label}  (settling…)"
        return f"Look at key: {label}  (collecting…)"

    def begin(self, now_ms: int) -> None:
        self._index = 0
        self._phase = "settle"
        self._phase_start_ms = int(now_ms)
        self._collect_features = []
        self._recorded_gaze = []
        self._results = []

    def tick(
        self,
        now_ms: int,
        features: Optional[FrameFeatures] = None,
    ) -> Optional[KeyAccuracyResultRow]:
        """
        Advance settle/collect timers. During collect, store raw per-frame features.

        Returns a completed result row when a key's collection window ends.
        """
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
        if self._on_collect_begin is not None:
            self._on_collect_begin()
        row = evaluate_key_accuracy_from_frames(
            target_label=label,
            target=target,
            frames=frames,
            keys=self._keys,
            predict_screen_xy=self._predict_screen_xy,
        )
        self._results.append(row)
        if frames:
            self._recorded_gaze.append(
                RecordedKeyFrames(target_label=label, target=target, frames=frames)
            )
        self._index += 1
        self._collect_features = []
        if not self.finished:
            self._phase = "settle"
            self._phase_start_ms = int(now_ms)
        return row


class KeyAccuracyDebugCsv:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or default_key_accuracy_debug_path()

    def write(self, rows: Sequence[KeyAccuracyResultRow], *, overwrite: bool = True) -> None:
        mode = "w" if overwrite else "a"
        write_header = overwrite or not self.path.exists()
        with self.path.open(mode, encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(CSV_FIELDNAMES))
            if write_header:
                writer.writeheader()
            for r in rows:
                writer.writerow(
                    {
                        "target_key": r.target_key,
                        "target_center_x": f"{r.target_center_x:.2f}",
                        "target_center_y": f"{r.target_center_y:.2f}",
                        "predicted_x": f"{r.predicted_x:.2f}",
                        "predicted_y": f"{r.predicted_y:.2f}",
                        "predicted_key": r.predicted_key,
                        "error_px": f"{r.error_px:.2f}",
                        "dx": f"{r.dx:.2f}",
                        "dy": f"{r.dy:.2f}",
                        "is_correct": "1" if r.is_correct else "0",
                    }
                )


def print_accuracy_summary(rows: Sequence[KeyAccuracyResultRow]) -> None:
    if not rows:
        print("[key_accuracy] no results")
        return
    n = len(rows)
    correct = sum(1 for r in rows if r.is_correct)
    errs = np.array([r.error_px for r in rows], dtype=np.float64)
    mean_err = float(np.mean(errs))
    max_err = float(np.max(errs))
    worst = sorted(rows, key=lambda r: r.error_px, reverse=True)[:5]

    print("[key_accuracy] --- summary ---")
    print(f"[key_accuracy] total tested keys: {n}")
    print(f"[key_accuracy] correct: {correct}")
    print(f"[key_accuracy] accuracy: {100.0 * correct / n:.1f}%")
    print(f"[key_accuracy] mean error px: {mean_err:.1f}")
    print(f"[key_accuracy] max error px: {max_err:.1f}")
    if worst:
        print("[key_accuracy] worst keys:")
        for r in worst:
            print(
                f"[key_accuracy]   target {r.target_key} -> predicted {r.predicted_key} "
                f"err={r.error_px:.1f}px dx={r.dx:+.1f} dy={r.dy:+.1f}"
            )

    confusion: dict[Tuple[str, str], int] = {}
    for r in rows:
        if r.is_correct:
            continue
        pair = (r.target_key, r.predicted_key)
        confusion[pair] = confusion.get(pair, 0) + 1
    if confusion:
        print("[key_accuracy] confusion pairs (target -> predicted):")
        for (tgt, pred), count in sorted(confusion.items(), key=lambda x: (-x[1], x[0])):
            suffix = f" x{count}" if count > 1 else ""
            print(f"[key_accuracy]   {tgt} -> {pred}{suffix}")
