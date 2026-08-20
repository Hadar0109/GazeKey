"""Tests for run summary formatting and SC-001–SC-004 threshold checks."""

from __future__ import annotations

import pytest

from tools.evaluation.benchmark_runner import (
    BenchmarkMetrics,
    KeyAccuracyResultRow,
    build_benchmark_run,
    compute_benchmark_metrics,
    evaluate_benchmark_pass,
)
from tools.evaluation.run_summary import (
    DEFAULT_FIDELITY_NOTES,
    RunSummary,
    RunSummaryWriter,
    benchmark_thresholds,
    classify_quality_gate_kind,
)


def _row(*, correct: bool, err: float, row_ok: bool = True) -> KeyAccuracyResultRow:
    return KeyAccuracyResultRow(
        target_key="Q",
        target_center_x=100.0,
        target_center_y=100.0,
        predicted_x=100.0,
        predicted_y=100.0,
        predicted_key="Q" if correct else "W",
        error_px=err,
        dx=0.0,
        dy=0.0,
        is_correct=correct,
        target_row_index=0,
        predicted_row_index=0 if row_ok else 1,
        row_correct=row_ok,
    )


def test_benchmark_thresholds_match_cq1():
    t = benchmark_thresholds()
    assert t.benchmark_key_count == 15
    assert t.min_keys_correct == 10
    assert t.max_median_error_px == 55.0
    assert t.min_row_accuracy == 0.80
    assert t.min_session_floor_keys == 8


def test_display_key_hit_pct_rounds_10_of_15():
    from tools.evaluation.run_summary import display_key_hit_pct

    assert display_key_hit_pct(10, 15) == 67


def test_evaluate_benchmark_pass_sc001_sc003():
    # SC-001: 10/15 passes (not strict fractional 0.67).
    passing = [_row(correct=True, err=30.0) for _ in range(10)] + [
        _row(correct=False, err=80.0) for _ in range(5)
    ]
    metrics = compute_benchmark_metrics(passing)
    passed, reason = evaluate_benchmark_pass(metrics)
    assert passed, reason
    assert metrics.keys_correct == 10
    assert metrics.row_accuracy == 1.0

    failing = [_row(correct=True, err=30.0) for _ in range(9)] + [
        _row(correct=False, err=80.0) for _ in range(6)
    ]
    metrics_fail = compute_benchmark_metrics(failing)
    passed_fail, reason_fail = evaluate_benchmark_pass(metrics_fail)
    assert not passed_fail
    assert "key-hit" in reason_fail


def test_evaluate_benchmark_pass_sc002_median_error():
    rows = [_row(correct=True, err=60.0) for _ in range(15)]
    metrics = compute_benchmark_metrics(rows)
    passed, reason = evaluate_benchmark_pass(metrics)
    assert not passed
    assert "median_err" in reason


def test_run_summary_console_format_benchmark():
    writer = RunSummaryWriter()
    summary = RunSummary(
        session_id="test01",
        run_type="benchmark",
        status="passed",
        primary_metrics={
            "keys_correct": 11,
            "keys_total": 15,
            "key_hit_pct": 73.3,
            "rows_correct": 13,
            "median_error_px": 48.0,
        },
    )
    text = writer.format_console(summary)
    assert "[benchmark] PASS" in text
    assert "keys=11/15" in text
    assert "median_err=48px" in text


def test_build_benchmark_run_status():
    rows = [_row(correct=True, err=40.0) for _ in range(10)] + [
        _row(correct=False, err=70.0) for _ in range(5)
    ]
    run = build_benchmark_run(rows)
    assert run.status == "passed"
    assert run.metrics.keys_correct == 10


def test_write_benchmark_summary_appends_failure_analysis(tmp_path):
    from tools.evaluation.failure_analysis import format_failure_analysis

    writer = RunSummaryWriter(runs_dir=tmp_path)
    rows = [_row(correct=False, err=80.0) for _ in range(15)]
    metrics = compute_benchmark_metrics(rows)
    analysis = format_failure_analysis(rows, likely_cause="mapping")
    writer.write_benchmark_summary(
        session_id="bench02",
        metrics=metrics,
        status="failed",
        failure_reason="key-hit",
        failure_analysis=analysis,
    )
    body = (tmp_path / "bench02" / "benchmark_summary.txt").read_text(encoding="utf-8")
    assert "failure_analysis:" in body
    assert "likely_cause: mapping" in body
    assert "fidelity_notes:" in body
    assert "inside_tight" in DEFAULT_FIDELITY_NOTES or "tight rect" in DEFAULT_FIDELITY_NOTES


def test_location_inside_tight_and_key_relative_fields_in_summary(tmp_path):
    from tools.evaluation.session import format_location_results

    rows = [_row(correct=True, err=20.0) for _ in range(3)]
    text = format_location_results(rows)
    assert "inside_tight" in text
    assert "focus_stability" in text
    writer = RunSummaryWriter(runs_dir=tmp_path)
    metrics = compute_benchmark_metrics(rows)
    writer.write_benchmark_summary(
        session_id="loc01",
        metrics=metrics,
        status="passed",
        location_results_text=text,
    )
    body = (tmp_path / "loc01" / "benchmark_summary.txt").read_text(encoding="utf-8")
    assert "dx/w" in body or "dx_over_width" in body or "dx/w=" in body


def test_classify_quality_gate_kind_does_not_invent_policy():
    class Q:
        def __init__(self, usable, warnings, reasons):
            self.usable = usable
            self.warnings = warnings
            self.reasons = reasons

    assert classify_quality_gate_kind(None) == "blocking"
    assert classify_quality_gate_kind(Q(False, [], ["predict returned none"])) == "blocking"
    assert classify_quality_gate_kind(Q(True, ["loocv high"], [])) == "warning_only"
    assert classify_quality_gate_kind(Q(True, [], [])) == "clean"
