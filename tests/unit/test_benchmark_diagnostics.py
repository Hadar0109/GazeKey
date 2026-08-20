"""Phase 8 (post-Iter-3): all-target benchmark diagnostics (reporting only).

Verifies the diagnostics record persists EVERY benchmark target (hits + misses),
not only failed keys, plus the metadata needed for data-driven experiment
selection (alpha, points, row assignments, residual stats by row / hits / misses).
"""

from __future__ import annotations

import json

from gazekey.calibration.targets import CalibrationTarget
from tools.evaluation.benchmark_diagnostics import (
    build_benchmark_diagnostics,
    compute_residual_stats,
    diagnostics_path,
    write_benchmark_diagnostics,
)
from tools.evaluation.benchmark_runner import KeyAccuracyResultRow, build_benchmark_run


def _row(
    *,
    target: str,
    correct: bool,
    dx: float,
    dy: float,
    row: int = 0,
    row_ok: bool = True,
) -> KeyAccuracyResultRow:
    tx, ty = 100.0, 100.0 + 60.0 * row
    return KeyAccuracyResultRow(
        target_key=target,
        target_center_x=tx,
        target_center_y=ty,
        predicted_x=tx + dx,
        predicted_y=ty + dy,
        predicted_key=target if correct else "?",
        error_px=float((dx ** 2 + dy ** 2) ** 0.5),
        dx=dx,
        dy=dy,
        is_correct=correct,
        target_row_index=row,
        predicted_row_index=row if row_ok else row + 1,
        row_correct=row_ok,
    )


def _fifteen_rows():
    rows = []
    # 5 hits (small residuals), 10 misses (mixed dy signs across rows).
    for i in range(5):
        rows.append(_row(target=f"H{i}", correct=True, dx=5.0, dy=3.0, row=i % 3))
    for i in range(10):
        dy = 40.0 if i % 2 == 0 else -40.0
        rows.append(_row(target=f"M{i}", correct=False, dx=-20.0, dy=dy, row=i % 3, row_ok=False))
    return rows


class _StubMapper:
    mapper_type = "pca4_baseline"
    alpha = 0.3
    clip_bounds = (0.0, 0.0, 1920.0, 1080.0)
    row_y_centers = (100.0, 160.0, 220.0)
    row_y_bias = (12.0, -7.0, 4.0)

    def leave_one_out_rms_px(self):
        return 53.2


def _targets():
    return [
        CalibrationTarget(
            target_id=f"T{i:02d}",
            label=f"r{i // 5}",
            key_id="",
            screen_x=float(50 + 30 * i),
            screen_y=float(100 + 60 * (i // 5)),
            grid_row=i // 5,
            grid_col=i % 5,
        )
        for i in range(15)
    ]


def _build():
    rows = _fifteen_rows()
    run = build_benchmark_run(rows)
    return rows, build_benchmark_diagnostics(
        session_id="abc123-bench999",
        rows=rows,
        metrics=run.metrics,
        status=run.status,
        failure_reason="key-hit 5/15 (33%) < 10/15 (~67%)",
        likely_cause="mapping",
        model=_StubMapper(),
        calibration_targets=_targets(),
        calibration_loocv_rms_px=50.8,
        feature_smoother_alpha=0.28,
        gaze_smoother_alpha=0.35,
        gaze_bias_x=1.0,
        gaze_bias_y=-2.0,
    )


def test_persists_all_fifteen_targets_including_hits():
    rows, diag = _build()
    assert len(diag["targets"]) == 15
    keys = {t["target_key"] for t in diag["targets"]}
    # Hits are present too (the gap this instrumentation closes).
    assert {"H0", "H1", "H2", "H3", "H4"}.issubset(keys)
    correct_count = sum(1 for t in diag["targets"] if t["is_correct"])
    assert correct_count == 5
    for t in diag["targets"]:
        for field in ("target_x", "target_y", "pred_x", "pred_y", "dx", "dy", "error_px"):
            assert field in t


def test_residual_stats_cover_all_rows_and_hits_vs_misses():
    rows, diag = _build()
    stats = diag["residual_stats"]
    assert stats["overall"]["dy"]["n"] == 15
    assert stats["hits"]["dy"]["n"] == 5
    assert stats["misses"]["dy"]["n"] == 10
    # by_target_row keys present for rows 0,1,2
    assert set(stats["by_target_row"].keys()) == {"0", "1", "2"}
    # Mixed miss dy must not be hidden: misses include both signs -> min<0<max.
    assert stats["misses"]["dy"]["min"] < 0 < stats["misses"]["dy"]["max"]
    # compute_residual_stats is consistent when called directly.
    direct = compute_residual_stats(rows)
    assert direct["overall"]["dy"]["n"] == 15


def test_metadata_includes_alpha_points_and_config():
    _rows, diag = _build()
    assert diag["mapper"]["mapper_type"] == "pca4_baseline"
    assert diag["mapper"]["ridge_alpha"] == 0.3
    assert diag["mapper"]["row_y_centers"] == [100.0, 160.0, 220.0]
    assert diag["mapper"]["row_y_bias"] == [12.0, -7.0, 4.0]
    assert diag["mapper"]["loocv_rms_px"] == 53.2
    assert diag["mapper"]["calibration_loocv_rms_px"] == 50.8
    assert len(diag["calibration_targets"]) == 15
    assert diag["calibration_targets"][0]["screen_x"] == 50.0
    # Frozen config flags that explain experiment differences.
    assert "apply_row_y_bias" in diag["config"]
    assert "apply_local_y_correction" in diag["config"]
    assert "alpha_grid" in diag["config"]
    assert diag["runtime"]["feature_smoother_alpha"] == 0.28
    assert diag["runtime"]["gaze_smoother_alpha"] == 0.35


def test_write_round_trips_to_json(tmp_path):
    _rows, diag = _build()
    path = write_benchmark_diagnostics(diag, session_id="abc123-bench999", runs_dir=tmp_path)
    assert path == diagnostics_path("abc123-bench999", runs_dir=tmp_path)
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["session_id"] == "abc123-bench999"
    assert len(loaded["targets"]) == 15
    assert loaded["metrics"]["keys_total"] == 15
    assert loaded["schema_version"] == diag["schema_version"]


def test_handles_missing_model_and_targets_gracefully():
    rows = _fifteen_rows()
    run = build_benchmark_run(rows)
    diag = build_benchmark_diagnostics(
        session_id="s-bench1",
        rows=rows,
        metrics=run.metrics,
        status=run.status,
        model=None,
        calibration_targets=None,
    )
    assert diag["mapper"] == {}
    assert diag["calibration_targets"] is None
    assert len(diag["targets"]) == 15


def test_unclamped_clamped_diagnostic_fields_exist_without_altering_product_clamp():
    import inspect

    from gazekey.mapping.ridge import Pca4BaselineMapper, _clip_xy
    from gazekey.runtime.mapper_runtime import MapperRuntime
    from tools.evaluation.benchmark_runner import evaluate_key_accuracy_from_frames
    from tools.evaluation.clamp_diagnostic import unclamped_xy_from_model
    from unittest.mock import MagicMock
    from PySide6.QtCore import QRect
    from gazekey.layout.layout_inspector import KeyGeometryRow
    from gazekey.features.feature_types import FrameFeatures

    # Product clamp helpers still clip (Phase 2 must not change them).
    assert inspect.getsource(_clip_xy).count("min(") >= 1
    assert "clip_bounds" in inspect.getsource(MapperRuntime.clamp_xy)

    target = KeyGeometryRow(
        key_id="q",
        key_label="Q",
        key_action="q",
        row_index=0,
        col_index=0,
        button=MagicMock(),
        rect=QRect(100, 100, 40, 40),
        center=(120.0, 120.0),
        hitbox=QRect(100, 100, 40, 40),
        is_special_key=False,
        weight=1.0,
    )
    feat = FrameFeatures(
        timestamp_ms=0,
        face_detected=True,
        blink=False,
        confidence=1.0,
        Lh=0.5,
        Lv=0.5,
        Rh=0.5,
        Rv=0.5,
        avg_h=0.5,
        avg_v=0.5,
        eye_box_w=1.0,
        eye_box_h=1.0,
        face_x=0.0,
        face_y=0.0,
        pca_uL=0.0,
        pca_vL=0.0,
        pca_uR=0.0,
        pca_vR=0.0,
    )
    bounds = (0.0, 0.0, 200.0, 200.0)
    row = evaluate_key_accuracy_from_frames(
        target_label="Q",
        target=target,
        frames=[feat, feat],
        keys=[target],
        predict_screen_xy=lambda _f: (110.0, 110.0),
        predict_unclamped_screen_xy=lambda _f: (250.0, 110.0),
        clip_bounds=bounds,
    )
    assert row.unclamped_x == 250.0
    assert row.unclamped_y == 110.0
    assert row.unclamped_inside_tight is False
    assert row.inside_tight is True
    assert row.clamp_frames >= 1
    assert row.collect_frames == 2

    # Diagnostic helper does not mutate mapper clip_bounds.
    model = Pca4BaselineMapper(
        w_x=__import__("numpy").array([1.0, 0.0]),
        b_x=0.0,
        mu_x=__import__("numpy").array([0.0, 0.0]),
        sigma_x=__import__("numpy").array([1.0, 1.0]),
        w_y=__import__("numpy").array([1.0, 0.0]),
        b_y=0.0,
        mu_y=__import__("numpy").array([0.0, 0.0]),
        sigma_y=__import__("numpy").array([1.0, 1.0]),
        alpha=1.0,
        train_u_l=__import__("numpy").zeros(5),
        train_u_r=__import__("numpy").zeros(5),
        train_v_l=__import__("numpy").zeros(5),
        train_v_r=__import__("numpy").zeros(5),
        train_Y=__import__("numpy").zeros((5, 2)),
        clip_bounds=bounds,
    )
    before = model.clip_bounds
    unclamped_xy_from_model(model, feat)
    assert model.clip_bounds == before
    clipped = _clip_xy(250.0, 110.0, bounds)
    assert clipped == (200.0, 110.0)
