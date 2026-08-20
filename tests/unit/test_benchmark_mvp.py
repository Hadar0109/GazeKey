"""US3: evaluation auto-benchmark trigger and summary."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gazekey.app_config import AppConfig, apply_config
from tools.evaluation.benchmark_runner import (
    EDITING_CONTROL_KEYS,
    HELD_OUT_LETTERS_DEFAULT,
    DEFAULT_SAMPLE_KEYS,
    KeyAccuracyResultRow,
    build_benchmark_run,
    calibration_labels_from_targets,
    evaluate_benchmark_pass,
    evaluate_key_accuracy_from_frames,
    point_in_tight_rect,
    unique_evaluation_labels,
)
from tools.evaluation.failure_analysis import format_failure_analysis, infer_likely_cause
from tools.evaluation.run_summary import DEFAULT_FIDELITY_NOTES, RunSummaryWriter


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


def _rect_key(label: str, x: int, y: int, w: int = 40, h: int = 40):
    from PySide6.QtCore import QRect
    from gazekey.layout.layout_inspector import KeyGeometryRow

    rect = QRect(x, y, w, h)
    return KeyGeometryRow(
        key_id=label.lower(),
        key_label=label,
        key_action=label.lower() if label != "Space" else " ",
        row_index=0,
        col_index=0,
        button=MagicMock(),
        rect=rect,
        center=(float(rect.center().x()), float(rect.center().y())),
        hitbox=rect,
        is_special_key=False,
        weight=1.0,
    )


def _feat_ts(ts: int = 0):
    from gazekey.features.feature_types import FrameFeatures

    return FrameFeatures(
        timestamp_ms=ts,
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


def test_inside_tight_rect_is_primary_snap_is_not_success():
    target = _rect_key("Q", 100, 100, 40, 40)
    keys = [target]
    inside_pt = (110, 110)
    # Outside tight rect, within snap distance of the key.
    snap_pt = (150, 120)

    assert point_in_tight_rect(target, *inside_pt)
    assert not point_in_tight_rect(target, *snap_pt)

    row = evaluate_key_accuracy_from_frames(
        target_label="Q",
        target=target,
        frames=[_feat_ts(1), _feat_ts(2), _feat_ts(3)],
        keys=keys,
        predict_screen_xy=lambda _f: snap_pt,
    )
    # Snap may still hit-test the key; that is not mapped-key success.
    assert row.inside_tight is False
    assert row.is_correct is False
    assert row.dx != 0.0 or row.dy != 0.0


def test_focus_stability_is_frame_hit_fraction_not_mean_point():
    target = _rect_key("Q", 100, 100, 40, 40)
    keys = [target]
    pts = [(110, 110), (110, 110), (200, 200)]
    it = iter(pts)

    row = evaluate_key_accuracy_from_frames(
        target_label="Q",
        target=target,
        frames=[_feat_ts(i) for i in range(3)],
        keys=keys,
        predict_screen_xy=lambda _f: next(it),
    )
    assert row.inside_tight is True  # median still inside
    assert row.focus_stability == pytest.approx(2.0 / 3.0)


def test_held_out_letters_not_identical_to_keyboard15_anchors():
    anchors = set(DEFAULT_SAMPLE_KEYS)
    held = set(HELD_OUT_LETTERS_DEFAULT)
    assert held != anchors
    letter_anchors = anchors - {"Space"}
    assert held.isdisjoint(letter_anchors)


def test_editing_control_slice_present_in_evaluation_walk():
    labels = unique_evaluation_labels()
    normalized = {str(x).lower() for x in labels}
    for name in EDITING_CONTROL_KEYS:
        assert name.lower() in normalized
    # Space is a calib target: present once in the walk, still flagged editing.
    assert labels.count("Space") == 1
    # Suggestion keys are not in the mapped-key walk.
    assert not any(str(x).startswith("suggestion:") for x in labels)


def test_calibration_labels_from_unmapped_targets_fall_back_to_keyboard15():
    class T:
        def __init__(self, label):
            self.label = label

    assert calibration_labels_from_targets([T(f"T{i:02d}") for i in range(1, 16)]) == list(
        DEFAULT_SAMPLE_KEYS
    )
    real = [T("key_q"), T("key_e"), T("key_t"), T("key_space"), T("key_a")]
    assert "Q" in calibration_labels_from_targets(real)
    assert "Space" in calibration_labels_from_targets(real)


def test_benchmark_summary_records_fidelity_notes(tmp_path):
    rows = [_row(correct=True, err=30.0) for _ in range(15)]
    run = build_benchmark_run(rows)
    writer = RunSummaryWriter(runs_dir=tmp_path)
    writer.write_benchmark_summary(
        session_id="sess-fid",
        metrics=run.metrics,
        status="passed",
    )
    from tools.evaluation.session_paths import folder_session_id

    text = (tmp_path / folder_session_id("sess-fid") / "benchmark_summary.txt").read_text(
        encoding="utf-8"
    )
    assert "fidelity_notes:" in text
    assert "reset per evaluation key" in text or "EMA" in DEFAULT_FIDELITY_NOTES

