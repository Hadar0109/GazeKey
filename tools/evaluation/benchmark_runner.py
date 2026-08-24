"""Benchmark scoring for the MVP calibration-mapping path.

Feature 004: score the same predict + hit-test path as product typing.
Primary correctness is inside the intended tight rect (snap is not success).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Set, Tuple

import numpy as np
from PySide6.QtCore import QPoint

from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.typing.key_hit_tester import hit_test_layout_keys
from gazekey.typing.key_semantics import SUGGESTION_KEY_ID_PREFIX, is_suggestion_action

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

# Research R3 default while keyboard15 (DEFAULT_SAMPLE_KEYS) is the active layout.
HELD_OUT_LETTERS_DEFAULT: Tuple[str, ...] = (
    "W",
    "R",
    "Y",
    "I",
    "O",
    "S",
    "F",
    "H",
    "K",
    "X",
    "V",
    "N",
)

EDITING_CONTROL_KEYS: Tuple[str, ...] = (
    "Shift",
    "Backspace",
    "Space",
    "Enter",
    "Calibrate",
)

SETTLE_MS = 1200
COLLECT_MS = 2500

PredictFn = Callable[[Any], Optional[Tuple[float, float]]]


def _normalize_match_token(label: str) -> str:
    s = str(label).strip()
    low = s.lower().replace("👁", "").strip()
    if low in {"space", " "}:
        return " "
    if low in {"backspace", "⌫"}:
        return "backspace"
    if low in {"enter", "↵"}:
        return "enter"
    if low == "shift":
        return "shift"
    if low in {"calibrate", "recalibrate", "system:calibrate"}:
        return "calibrate"
    if len(s) == 1:
        return s.lower()
    return low


def _key_match_tokens(row: KeyGeometryRow) -> Set[str]:
    tokens = {
        _normalize_match_token(row.key_action),
        _normalize_match_token(row.key_label),
        _normalize_match_token(row.key_id),
    }
    blob = f"{row.key_id} {row.key_action} {row.key_label}".lower()
    if "calibrate" in blob:
        tokens.add("calibrate")
    return tokens


def is_suggestion_layout_key(row: KeyGeometryRow) -> bool:
    return is_suggestion_action(str(row.key_action)) or str(row.key_id).startswith(
        SUGGESTION_KEY_ID_PREFIX
    )


def _letter_labels_from_keys(keys: Sequence[KeyGeometryRow]) -> List[str]:
    out: List[str] = []
    for k in keys:
        if is_suggestion_layout_key(k):
            continue
        act = str(k.key_action)
        if len(act) == 1 and act.isalpha():
            out.append(act.upper())
    return out


def held_out_letters_for_layout(
    *,
    calibration_labels: Optional[Sequence[str]] = None,
    layout_mode: str = "keyboard15",
    keys: Optional[Sequence[KeyGeometryRow]] = None,
) -> Tuple[str, ...]:
    """Letter keys whose centers are not active calibration coordinates (research R3)."""
    calib = {_normalize_match_token(x) for x in (calibration_labels or DEFAULT_SAMPLE_KEYS)}
    mode = str(layout_mode).lower()
    if mode.startswith("keyboard15") and calibration_labels is None:
        return HELD_OUT_LETTERS_DEFAULT
    letters: Sequence[str]
    if keys is not None:
        letters = _letter_labels_from_keys(keys)
    else:
        letters = HELD_OUT_LETTERS_DEFAULT
    held = [lab for lab in letters if _normalize_match_token(lab) not in calib]
    return tuple(held)


def calibration_labels_from_targets(targets: Optional[Sequence[object]]) -> List[str]:
    """Map calibration target labels to evaluation sample names; fall back to keyboard15."""
    if not targets:
        return list(DEFAULT_SAMPLE_KEYS)
    labels: List[str] = []
    for t in targets:
        raw = str(getattr(t, "label", "") or "").strip()
        low = raw.lower()
        if low.endswith("space") or low in {"space", "key_space"}:
            labels.append("Space")
            continue
        if raw.startswith("key_") and len(raw) > 4:
            token = raw[4:]
            labels.append(token.upper() if len(token) == 1 else token)
            continue
        if len(raw) == 1 and raw.isalpha():
            labels.append(raw.upper())
    if len(labels) < 5:
        return list(DEFAULT_SAMPLE_KEYS)
    return labels


def unique_evaluation_labels(
    *,
    calibration_labels: Optional[Sequence[str]] = None,
    layout_mode: str = "keyboard15",
    keys: Optional[Sequence[KeyGeometryRow]] = None,
) -> List[str]:
    """Ordered unique walk: repeatability, then held-out letters, then editing/control.

    Suggestion / prediction-bar keys are never included (SC-010). A calib-target
    key (e.g. Space) is listed once in the walk; slice flags still mark it as
    editing/control coverage without double-counting in the primary held-out rate.
    """
    calib = list(calibration_labels or DEFAULT_SAMPLE_KEYS)
    held = list(
        held_out_letters_for_layout(
            calibration_labels=calibration_labels,
            layout_mode=layout_mode,
            keys=keys,
        )
    )
    seen: Set[str] = set()
    out: List[str] = []
    for label in [*calib, *held, *EDITING_CONTROL_KEYS]:
        token = _normalize_match_token(label)
        if token in seen:
            continue
        seen.add(token)
        out.append(str(label))
    return out


def slice_flags_for_label(
    label: str,
    *,
    calibration_labels: Optional[Sequence[str]] = None,
    held_out_letters: Optional[Sequence[str]] = None,
) -> Tuple[bool, bool, bool]:
    """Return (was_calibration_location, in_held_out_letter_slice, in_editing_control_slice)."""
    token = _normalize_match_token(label)
    calib = {_normalize_match_token(x) for x in (calibration_labels or DEFAULT_SAMPLE_KEYS)}
    held = {_normalize_match_token(x) for x in (held_out_letters or HELD_OUT_LETTERS_DEFAULT)}
    editing = {_normalize_match_token(x) for x in EDITING_CONTROL_KEYS}
    was_cal = token in calib
    in_held = token in held and not was_cal
    in_edit = token in editing
    return was_cal, in_held, in_edit


def resolve_sample_keys(
    keys: Sequence[KeyGeometryRow],
    sample_labels: Sequence[str] = DEFAULT_SAMPLE_KEYS,
) -> List[Tuple[str, KeyGeometryRow]]:
    """Map human-readable sample labels to layout keys."""
    usable = [k for k in keys if not is_suggestion_layout_key(k)]
    by_token: dict[str, List[KeyGeometryRow]] = {}
    for k in usable:
        for tok in _key_match_tokens(k):
            by_token.setdefault(tok, []).append(k)

    out: List[Tuple[str, KeyGeometryRow]] = []
    for sample in sample_labels:
        token = _normalize_match_token(sample)
        candidates = by_token.get(token) or []
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
    if is_suggestion_layout_key(row):
        return str(row.key_id)
    tokens = _key_match_tokens(row)
    if "calibrate" in tokens:
        return "Calibrate"
    if "backspace" in tokens:
        return "Backspace"
    if "enter" in tokens:
        return "Enter"
    if "shift" in tokens:
        return "Shift"
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


def point_in_tight_rect(target: KeyGeometryRow, screen_x: float, screen_y: float) -> bool:
    """True when the point is inside the intended key's tight rect (no snap)."""
    rect = getattr(target, "rect", None)
    if rect is None:
        return False
    try:
        return bool(rect.contains(QPoint(int(screen_x), int(screen_y))))
    except Exception:
        return False


def _key_size_px(target: KeyGeometryRow) -> Tuple[float, float]:
    rect = getattr(target, "rect", None)
    try:
        w = float(rect.width())
        h = float(rect.height())
        return (w if w > 0 else 1.0, h if h > 0 else 1.0)
    except Exception:
        return 1.0, 1.0


def _median_xy(preds: Sequence[Tuple[float, float]]) -> Tuple[float, float]:
    xs = np.array([p[0] for p in preds], dtype=np.float64)
    ys = np.array([p[1] for p in preds], dtype=np.float64)
    return float(np.median(xs)), float(np.median(ys))


def _same_layout_key(a: KeyGeometryRow, b: KeyGeometryRow) -> bool:
    if a.key_id and b.key_id and a.key_id == b.key_id:
        return True
    return bool(_key_match_tokens(a) & _key_match_tokens(b))


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
    inside_tight: bool = False
    focus_stability: float = 0.0
    dx_over_width: float = 0.0
    dy_over_height: float = 0.0
    was_calibration_location: bool = True
    in_held_out_letter_slice: bool = False
    in_editing_control_slice: bool = False
    unclamped_x: Optional[float] = None
    unclamped_y: Optional[float] = None
    unclamped_inside_tight: Optional[bool] = None
    clamp_hit: bool = False
    collect_frames: int = 0
    clamp_frames: int = 0


def build_result_row(
    *,
    target_label: str,
    target: KeyGeometryRow,
    predicted_x: float,
    predicted_y: float,
    predicted: KeyGeometryRow,
    inside_tight: Optional[bool] = None,
    focus_stability: float = 0.0,
    was_calibration_location: bool = True,
    in_held_out_letter_slice: bool = False,
    in_editing_control_slice: bool = False,
    unclamped_x: Optional[float] = None,
    unclamped_y: Optional[float] = None,
    unclamped_inside_tight: Optional[bool] = None,
    clamp_hit: bool = False,
    collect_frames: int = 0,
    clamp_frames: int = 0,
) -> KeyAccuracyResultRow:
    tcx, tcy = target.center
    err = float(math.hypot(predicted_x - tcx, predicted_y - tcy))
    pred_name = display_key_name(predicted)
    if inside_tight is None:
        inside_tight = point_in_tight_rect(target, predicted_x, predicted_y)
    width, height = _key_size_px(target)
    dx = float(predicted_x - tcx)
    dy = float(predicted_y - tcy)
    row_correct = int(predicted.row_index) == int(target.row_index)
    return KeyAccuracyResultRow(
        target_key=str(target_label),
        target_center_x=float(tcx),
        target_center_y=float(tcy),
        predicted_x=float(predicted_x),
        predicted_y=float(predicted_y),
        predicted_key=pred_name,
        error_px=err,
        dx=dx,
        dy=dy,
        is_correct=bool(inside_tight),
        target_row_index=int(target.row_index),
        predicted_row_index=int(predicted.row_index),
        row_correct=bool(row_correct),
        inside_tight=bool(inside_tight),
        focus_stability=float(focus_stability),
        dx_over_width=abs(dx) / width,
        dy_over_height=abs(dy) / height,
        was_calibration_location=bool(was_calibration_location),
        in_held_out_letter_slice=bool(in_held_out_letter_slice),
        in_editing_control_slice=bool(in_editing_control_slice),
        unclamped_x=unclamped_x,
        unclamped_y=unclamped_y,
        unclamped_inside_tight=unclamped_inside_tight,
        clamp_hit=bool(clamp_hit),
        collect_frames=int(collect_frames),
        clamp_frames=int(clamp_frames),
    )


def evaluate_key_accuracy_from_frames(
    *,
    target_label: str,
    target: KeyGeometryRow,
    frames: Sequence[Any],
    keys: Sequence[KeyGeometryRow],
    predict_screen_xy: PredictFn,
    predict_unclamped_screen_xy: Optional[PredictFn] = None,
    clip_bounds: Optional[Tuple[float, float, float, float]] = None,
    calibration_labels: Optional[Sequence[str]] = None,
    held_out_letters: Optional[Sequence[str]] = None,
) -> KeyAccuracyResultRow:
    """Per-frame product predict + hit-test; median representative; snap ≠ success."""
    clamped: List[Tuple[float, float]] = []
    unclamped: List[Tuple[float, float]] = []
    intended_hits = 0
    scored_frames = 0
    clamp_hits = 0
    for feat in frames:
        xy = predict_screen_xy(feat)
        uxy = None
        if predict_unclamped_screen_xy is not None:
            uxy = predict_unclamped_screen_xy(feat)
        if xy is None:
            continue
        px, py = float(xy[0]), float(xy[1])
        clamped.append((px, py))
        scored_frames += 1
        hit_id = hit_test_layout_keys(keys, px, py)
        if hit_id is not None and _same_layout_key(keys[int(hit_id)], target):
            intended_hits += 1
        if uxy is not None:
            ux, uy = float(uxy[0]), float(uxy[1])
            unclamped.append((ux, uy))
            if clip_bounds is not None:
                x0, y0, x1, y1 = clip_bounds
                if ux < x0 or ux > x1 or uy < y0 or uy > y1:
                    clamp_hits += 1
            elif (ux, uy) != (px, py):
                clamp_hits += 1
        elif clip_bounds is not None:
            x0, y0, x1, y1 = clip_bounds
            if px <= x0 or px >= x1 or py <= y0 or py >= y1:
                clamp_hits += 1

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

    ux = uy = None
    u_inside: Optional[bool] = None
    if unclamped:
        ux, uy = _median_xy(unclamped)
        u_inside = point_in_tight_rect(target, ux, uy)

    stability = float(intended_hits) / float(scored_frames) if scored_frames else 0.0
    was_cal, in_held, in_edit = slice_flags_for_label(
        target_label,
        calibration_labels=calibration_labels,
        held_out_letters=held_out_letters,
    )
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
        unclamped_x=ux,
        unclamped_y=uy,
        unclamped_inside_tight=u_inside,
        clamp_hit=bool(clamp_hits > 0),
        collect_frames=int(scored_frames),
        clamp_frames=int(clamp_hits),
    )


@dataclass(frozen=True)
class BenchmarkMetrics:
    key_hit_accuracy: float
    row_accuracy: float
    median_pixel_error: float
    keys_correct: int
    keys_total: int
    rows_correct: int
    held_out_inside_key_rate: float = 0.0
    editing_control_inside_key_rate: float = 0.0
    repeatability_inside_key_rate: float = 0.0
    mean_focus_stability_held_out: float = 0.0
    median_dx_over_width: float = 0.0
    median_dy_over_height: float = 0.0
    clamp_hit_rate: float = 0.0
    unclamped_inside_key_rate: Optional[float] = None
    repeatability_keys_correct: int = 0
    repeatability_keys_total: int = 0
    held_out_keys_correct: int = 0
    held_out_keys_total: int = 0
    editing_keys_correct: int = 0
    editing_keys_total: int = 0


@dataclass(frozen=True)
class BenchmarkRun:
    results: Tuple[KeyAccuracyResultRow, ...]
    metrics: BenchmarkMetrics
    status: str  # passed | failed  (reference floors on repeatability slice)


def _mapped_ok(r: KeyAccuracyResultRow) -> bool:
    """Inside-tight when scored by 004; ``is_correct`` for legacy constructed rows."""
    return bool(r.inside_tight or r.is_correct)


def _rate(correct: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return float(correct) / float(total)


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
    keys_correct = sum(1 for r in rows if _mapped_ok(r))
    rows_correct = sum(1 for r in rows if r.row_correct)
    errs = np.array([r.error_px for r in rows], dtype=np.float64)
    rep = [r for r in rows if r.was_calibration_location]
    held = [r for r in rows if r.in_held_out_letter_slice]
    edit = [r for r in rows if r.in_editing_control_slice]
    unclamped_flags = [r.unclamped_inside_tight for r in rows if r.unclamped_inside_tight is not None]
    clamp_frames = sum(int(getattr(r, "clamp_frames", 0) or 0) for r in rows)
    collect_frames = sum(int(getattr(r, "collect_frames", 0) or 0) for r in rows)
    if collect_frames <= 0:
        clamp_rate = _rate(sum(1 for r in rows if r.clamp_hit), n)
    else:
        clamp_rate = _rate(clamp_frames, collect_frames)
    return BenchmarkMetrics(
        key_hit_accuracy=float(keys_correct) / float(n),
        row_accuracy=float(rows_correct) / float(n),
        median_pixel_error=float(np.median(errs)),
        keys_correct=int(keys_correct),
        keys_total=int(n),
        rows_correct=int(rows_correct),
        held_out_inside_key_rate=_rate(sum(1 for r in held if _mapped_ok(r)), len(held)),
        editing_control_inside_key_rate=_rate(sum(1 for r in edit if _mapped_ok(r)), len(edit)),
        repeatability_inside_key_rate=_rate(sum(1 for r in rep if _mapped_ok(r)), len(rep)),
        mean_focus_stability_held_out=(
            float(np.mean([r.focus_stability for r in held])) if held else 0.0
        ),
        median_dx_over_width=float(np.median([r.dx_over_width for r in rows])),
        median_dy_over_height=float(np.median([r.dy_over_height for r in rows])),
        clamp_hit_rate=clamp_rate,
        unclamped_inside_key_rate=(
            _rate(sum(1 for v in unclamped_flags if v), len(unclamped_flags))
            if unclamped_flags
            else None
        ),
        repeatability_keys_correct=sum(1 for r in rep if _mapped_ok(r)),
        repeatability_keys_total=len(rep),
        held_out_keys_correct=sum(1 for r in held if _mapped_ok(r)),
        held_out_keys_total=len(held),
        editing_keys_correct=sum(1 for r in edit if _mapped_ok(r)),
        editing_keys_total=len(edit),
    )


def evaluate_benchmark_pass(metrics: BenchmarkMetrics) -> Tuple[bool, str]:
    """Return (passed, failure_reason) against SC-001–SC-003 reference floors.

    Historical 10/15 is applied to the **repeatability** slice when present so
    held-out / editing keys are not mixed into that floor. Feature 004 accept
    is vs baseline A/B, not this floor.
    """
    from tools.evaluation.run_summary import benchmark_thresholds, display_key_hit_pct

    t = benchmark_thresholds()
    reasons: List[str] = []
    keys_correct = (
        metrics.repeatability_keys_correct
        if metrics.repeatability_keys_total
        else metrics.keys_correct
    )
    keys_total = (
        metrics.repeatability_keys_total
        if metrics.repeatability_keys_total
        else metrics.keys_total
    )
    min_keys = t.min_keys_correct if keys_total == t.benchmark_key_count else max(
        1, int(round(t.min_keys_correct * keys_total / t.benchmark_key_count))
    )
    if keys_correct < min_keys:
        pct = display_key_hit_pct(keys_correct, keys_total)
        target_pct = display_key_hit_pct(t.min_keys_correct, t.benchmark_key_count)
        reasons.append(
            f"key-hit {keys_correct}/{keys_total} "
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
