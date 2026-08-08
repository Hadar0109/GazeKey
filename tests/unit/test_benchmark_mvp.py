"""US3: evaluation auto-benchmark trigger and summary."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gazekey.app_config import AppConfig, apply_config
from tools.evaluation.benchmark_runner import (
    KeyAccuracyResultRow,
    build_benchmark_run,
    evaluate_benchmark_pass,
)
from tools.evaluation.failure_analysis import format_failure_analysis, infer_likely_cause
from tools.evaluation.run_summary import RunSummaryWriter


def _row(*, correct: bool, err: float, row_ok: bool = True, target: str = "Q") -> KeyAccuracyResultRow:
    return KeyAccuracyResultRow(
        target_key=target,
        target_center_x=100.0,
        target_center_y=100.0,
        predicted_x=120.0,
        predicted_y=100.0,
        predicted_key=target if correct else "W",
        error_px=err,
        dx=20.0,
        dy=0.0,
        is_correct=correct,
        target_row_index=0,
        predicted_row_index=0 if row_ok else 1,
        row_correct=row_ok,
    )


def _bare_keyboard():
    from gazekey.ui.devtools_api import NullDevTools
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    kb = VirtualKeyboard.__new__(VirtualKeyboard)
    kb._mapper_runtime = MagicMock()
    kb._mapper_runtime.model = None
    kb._mapper_runtime.usable.return_value = False
    kb._devtools = NullDevTools()
    kb._benchmark_controller = None
    kb._is_calibrating = False
    kb._preview_mode = False
    kb._verbose = False
    kb._log_verbose = MagicMock()
    return kb


def _set_usable_mapper(kb, model=object()):
    kb._mapper_runtime.model = model
    kb._mapper_runtime.usable.return_value = model is not None


def test_benchmark_run_summary_includes_failure_analysis(tmp_path):
    rows = [_row(correct=True, err=30.0, target="Q") for _ in range(7)] + [
        _row(correct=False, err=90.0, target=f"K{i}")
        for i in range(8)
    ]
    run = build_benchmark_run(rows)
    passed, reason = evaluate_benchmark_pass(run.metrics)
    assert not passed
    cause = infer_likely_cause(rows)
    analysis = format_failure_analysis(rows, likely_cause=cause)

    writer = RunSummaryWriter(runs_dir=tmp_path)
    summary = writer.write_benchmark_summary(
        session_id="sess-bench1",
        metrics=run.metrics,
        status="failed",
        failure_reason=reason,
        failure_analysis=analysis,
    )
    from tools.evaluation.session_paths import folder_session_id

    text = (
        tmp_path / folder_session_id(summary.session_id) / "benchmark_summary.txt"
    ).read_text(encoding="utf-8")
    assert "[benchmark] FAIL" in text
    assert "failure_analysis:" in text
    assert "keys_failed:" in text
    assert "reason=" in text


def test_no_benchmark_button_in_control_bar(qapp):
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    kb = VirtualKeyboard()
    qapp.processEvents()
    assert not hasattr(kb, "benchmark_btn")


def test_benchmark_does_not_auto_start_without_evaluation_entry():
    from tools.evaluation.benchmark_controller import BenchmarkController

    apply_config(AppConfig())  # product/preview defaults
    kb = _bare_keyboard()
    _set_usable_mapper(kb)
    kb._preview_mode = True
    ctrl = BenchmarkController(kb)
    ctrl.start_mvp_benchmark = MagicMock()
    kb._devtools = MagicMock()
    kb._devtools.maybe_start_dev_benchmark = ctrl.maybe_start_dev_benchmark

    kb._maybe_start_dev_benchmark()

    ctrl.start_mvp_benchmark.assert_not_called()


def test_evaluation_auto_starts_when_usable_and_preview_ready():
    from tools.evaluation.benchmark_controller import BenchmarkController

    apply_config(AppConfig(auto_benchmark=True))
    kb = _bare_keyboard()
    _set_usable_mapper(kb)
    kb._preview_mode = True
    ctrl = BenchmarkController(kb)
    ctrl.start_mvp_benchmark = MagicMock()
    kb._devtools = MagicMock()
    kb._devtools.maybe_start_dev_benchmark = ctrl.maybe_start_dev_benchmark
    kb._benchmark_controller = ctrl

    kb._maybe_start_dev_benchmark()

    ctrl.start_mvp_benchmark.assert_called_once()


def test_evaluation_benchmark_blocked_without_usable_mapper():
    from tools.evaluation.benchmark_controller import BenchmarkController

    apply_config(AppConfig(auto_benchmark=True))
    kb = _bare_keyboard()
    kb._preview_mode = True
    ctrl = BenchmarkController(kb)
    ctrl.start_mvp_benchmark = MagicMock()
    kb._devtools = MagicMock()
    kb._devtools.maybe_start_dev_benchmark = ctrl.maybe_start_dev_benchmark

    kb._maybe_start_dev_benchmark()

    ctrl.start_mvp_benchmark.assert_not_called()


def test_evaluation_benchmark_blocked_until_preview_ready():
    from tools.evaluation.benchmark_controller import BenchmarkController

    apply_config(AppConfig(auto_benchmark=True))
    kb = _bare_keyboard()
    _set_usable_mapper(kb)
    kb._preview_mode = False
    ctrl = BenchmarkController(kb)
    ctrl.start_mvp_benchmark = MagicMock()
    kb._devtools = MagicMock()
    kb._devtools.maybe_start_dev_benchmark = ctrl.maybe_start_dev_benchmark

    kb._maybe_start_dev_benchmark()

    ctrl.start_mvp_benchmark.assert_not_called()


def test_evaluation_benchmark_blocked_during_calibration():
    from tools.evaluation.benchmark_controller import BenchmarkController

    apply_config(AppConfig(auto_benchmark=True))
    kb = _bare_keyboard()
    _set_usable_mapper(kb)
    kb._preview_mode = True
    kb._is_calibrating = True
    ctrl = BenchmarkController(kb)
    ctrl.start_mvp_benchmark = MagicMock()
    kb._devtools = MagicMock()
    kb._devtools.maybe_start_dev_benchmark = ctrl.maybe_start_dev_benchmark

    kb._maybe_start_dev_benchmark()

    ctrl.start_mvp_benchmark.assert_not_called()


def test_calibration_usable_gate_blocks_benchmark_without_mapper():
    kb = _bare_keyboard()
    assert not kb._calibration_usable()
