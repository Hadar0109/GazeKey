"""Compare ridge mapper candidates on recorded keyboard-accuracy gaze features."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

from gazekey.debug.keyboard_accuracy import (
    DEFAULT_FEATURE_SMOOTHER_ALPHA,
    KeyAccuracyResultRow,
    RecordedKeyFrames,
    evaluate_key_accuracy_from_frames,
    predict_key_accuracy_screen_xy,
    print_accuracy_summary,
)
from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.layout.layout_inspector import KeyGeometryRow
from gazekey.mapping.ridge import MapperCandidateReport, _keyboard_assessment_model

# Backward-compatible alias for callers that imported RecordedKeyGaze.
RecordedKeyGaze = RecordedKeyFrames


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_compare_csv_path() -> Path:
    return _repo_root() / "key_accuracy_compare.csv"


def evaluate_recorded_frames(
    *,
    recorded: Sequence[RecordedKeyFrames],
    keys: Sequence[KeyGeometryRow],
    model: object,
    gaze_bias_x: float = 0.0,
    gaze_bias_y: float = 0.0,
    clamp_xy: Optional[Callable[[float, float], Tuple[float, float]]] = None,
    min_quality: Optional[float] = None,
    feature_smoother_alpha: float = DEFAULT_FEATURE_SMOOTHER_ALPHA,
) -> List[KeyAccuracyResultRow]:
    """
    Replay frozen per-key frame lists with the same recipe as live keyboard accuracy.

    Resets the feature smoother at the start of each key's collect window.
    """
    smoother = PcaFeatureSmoother(alpha=float(feature_smoother_alpha))
    rows: List[KeyAccuracyResultRow] = []

    def predict(raw) -> Optional[Tuple[float, float]]:
        return predict_key_accuracy_screen_xy(
            raw,
            model=model,
            feature_smoother=smoother,
            gaze_bias_x=gaze_bias_x,
            gaze_bias_y=gaze_bias_y,
            clamp_xy=clamp_xy,
            min_quality=min_quality,
        )

    for item in recorded:
        smoother.reset()
        rows.append(
            evaluate_key_accuracy_from_frames(
                target_label=item.target_label,
                target=item.target,
                frames=item.frames,
                keys=keys,
                predict_screen_xy=predict,
            )
        )
    return rows


def compare_mapper_candidates(
    *,
    recorded: Sequence[RecordedKeyFrames],
    keys: Sequence[KeyGeometryRow],
    candidates: Sequence[MapperCandidateReport],
    calib_samples: Sequence[Tuple[object, Tuple[float, float]]],
    calib_targets: Sequence[object],
    runtime_model: Optional[object] = None,
    runtime_mapper_type: str = "",
    gaze_bias_x: float = 0.0,
    gaze_bias_y: float = 0.0,
    clamp_xy: Optional[Callable[[float, float], Tuple[float, float]]] = None,
    min_quality: Optional[float] = None,
    feature_smoother_alpha: float = DEFAULT_FEATURE_SMOOTHER_ALPHA,
    verbose: bool = True,
) -> List[Tuple[str, List[KeyAccuracyResultRow]]]:
    """
    Evaluate each successful ridge candidate on the same recorded gaze frame lists.

    For the selected runtime mapper type, replays through ``runtime_model`` so compare
    matches ``key_accuracy_debug.csv`` on the same session.
    """
    out: List[Tuple[str, List[KeyAccuracyResultRow]]] = []
    runtime_type = str(runtime_mapper_type).strip()
    for report in candidates:
        if not report.success or report.model is None:
            continue
        mapper_type = str(report.mapper_type)
        if runtime_model is not None and mapper_type == runtime_type:
            model = runtime_model
        else:
            model = report.model
            if calib_targets is not None and len(calib_targets) >= len(calib_samples):
                model = _keyboard_assessment_model(
                    model,
                    samples=calib_samples,
                    targets=calib_targets,
                    verbose=False,
                )

        rows = evaluate_recorded_frames(
            recorded=recorded,
            keys=keys,
            model=model,
            gaze_bias_x=gaze_bias_x,
            gaze_bias_y=gaze_bias_y,
            clamp_xy=clamp_xy,
            min_quality=min_quality,
            feature_smoother_alpha=feature_smoother_alpha,
        )
        out.append((mapper_type, rows))
        if verbose:
            print(f"[key_accuracy_compare] --- {mapper_type} ---")
            print_accuracy_summary(rows)
    return out


def validate_selected_mapper_matches_debug(
    debug_rows: Sequence[KeyAccuracyResultRow],
    compare_results: Sequence[Tuple[str, List[KeyAccuracyResultRow]]],
    selected_mapper_type: str,
    *,
    coord_tol_px: float = 0.05,
) -> None:
    """Raise AssertionError if debug and compare disagree for the selected mapper."""
    selected = str(selected_mapper_type).strip()
    compare_rows: Optional[List[KeyAccuracyResultRow]] = None
    for mapper_type, rows in compare_results:
        if str(mapper_type) == selected:
            compare_rows = list(rows)
            break
    if compare_rows is None:
        raise AssertionError(f"compare results missing selected mapper {selected!r}")

    if len(debug_rows) != len(compare_rows):
        raise AssertionError(
            f"row count mismatch: debug={len(debug_rows)} compare={len(compare_rows)}"
        )

    debug_ok = sum(1 for r in debug_rows if r.is_correct)
    compare_ok = sum(1 for r in compare_rows if r.is_correct)
    if debug_ok != compare_ok:
        raise AssertionError(
            f"accuracy mismatch for {selected}: debug={debug_ok}/{len(debug_rows)} "
            f"compare={compare_ok}/{len(compare_rows)}"
        )

    for dbg, cmp in zip(debug_rows, compare_rows):
        if dbg.target_key != cmp.target_key:
            raise AssertionError(
                f"target order mismatch: debug={dbg.target_key} compare={cmp.target_key}"
            )
        if dbg.is_correct != cmp.is_correct:
            raise AssertionError(
                f"{dbg.target_key}: is_correct debug={dbg.is_correct} compare={cmp.is_correct} "
                f"(debug pred={dbg.predicted_key!r} compare pred={cmp.predicted_key!r})"
            )
        if abs(dbg.predicted_x - cmp.predicted_x) > coord_tol_px:
            raise AssertionError(
                f"{dbg.target_key}: predicted_x debug={dbg.predicted_x:.2f} "
                f"compare={cmp.predicted_x:.2f}"
            )
        if abs(dbg.predicted_y - cmp.predicted_y) > coord_tol_px:
            raise AssertionError(
                f"{dbg.target_key}: predicted_y debug={dbg.predicted_y:.2f} "
                f"compare={cmp.predicted_y:.2f}"
            )
        if dbg.predicted_key != cmp.predicted_key:
            raise AssertionError(
                f"{dbg.target_key}: predicted_key debug={dbg.predicted_key!r} "
                f"compare={cmp.predicted_key!r}"
            )


def write_compare_csv(
    results: Sequence[Tuple[str, List[KeyAccuracyResultRow]]],
    *,
    path: Optional[Path] = None,
) -> Path:
    dest = path or default_compare_csv_path()
    fieldnames = [
        "mapper_type",
        *(
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
        ),
    ]
    with dest.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for mapper_type, rows in results:
            for r in rows:
                writer.writerow(
                    {
                        "mapper_type": mapper_type,
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
    return dest


def print_compare_leaderboard(results: Sequence[Tuple[str, List[KeyAccuracyResultRow]]]) -> None:
    """Rank mapper types by keyboard-level accuracy on the same recorded gaze."""
    if not results:
        print("[key_accuracy_compare] no candidate results")
        return
    stats = []
    for mapper_type, rows in results:
        if not rows:
            continue
        n = len(rows)
        correct = sum(1 for r in rows if r.is_correct)
        errs = np.array([r.error_px for r in rows], dtype=np.float64)
        abs_dx = np.array([abs(r.dx) for r in rows], dtype=np.float64)
        abs_dy = np.array([abs(r.dy) for r in rows], dtype=np.float64)
        stats.append(
            (
                mapper_type,
                100.0 * correct / n,
                correct,
                n,
                float(np.mean(errs)),
                float(np.max(errs)),
                float(np.mean(abs_dx)),
                float(np.mean(abs_dy)),
            )
        )
    stats.sort(key=lambda t: (-t[1], t[4], -t[2]))
    print("[key_accuracy_compare] --- leaderboard (same gaze, different mappers) ---")
    print(
        "[key_accuracy_compare] "
        f"{'mapper':<32} {'acc%':>6} {'ok':>5} {'mean_err':>9} {'max_err':>9} "
        f"{'mean|dx|':>9} {'mean|dy|':>9}"
    )
    for mapper_type, acc, ok, n, mean_e, max_e, mdx, mdy in stats:
        print(
            f"[key_accuracy_compare] "
            f"{mapper_type:<32} {acc:6.1f} {ok:>2}/{n:<2} {mean_e:9.1f} {max_e:9.1f} "
            f"{mdx:9.1f} {mdy:9.1f}"
        )
