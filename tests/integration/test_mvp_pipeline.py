"""Integration coverage for MVP pipeline: calibrate → preview → optional dev benchmark (FR-017)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtTest import QTest

from gazekey.calibration2.quality import CalibrationQualityResult
from gazekey.calibration2.session import CalibrationV2Result
from gazekey.evaluation.benchmark_runner import KeyAccuracyResultRow, build_benchmark_run
from gazekey.evaluation.run_summary import RunSummaryWriter
from gazekey.layout.layout_inspector import inspect_keyboard_layout
from gazekey.calibration2.targets import keyboard_geometry_targets
from gazekey.typing.gaze_ui_mapper import letter_keys_region_rect
from tests.unit.test_layout_geometry import _build_test_keyboard


def _minimal_calibration_samples():
    from tests.test_typing_candidate import _minimal_calibration_samples as samples

    return samples()


def _bench_row(*, correct: bool = True, err: float = 30.0, target: str = "Q") -> KeyAccuracyResultRow:
    return KeyAccuracyResultRow(
        target_key=target,
        target_center_x=100.0,
        target_center_y=100.0,
        predicted_x=100.0,
        predicted_y=100.0,
        predicted_key=target if correct else "W",
        error_px=err,
        dx=0.0,
        dy=0.0,
        is_correct=correct,
        target_row_index=0,
        predicted_row_index=0,
        row_correct=True,
    )


def _mock_ridge_fit(monkeypatch):
    mock_model = MagicMock()
    mock_model.mapper_type = "pca4_baseline"
    mock_model.leave_one_out_detail_px.return_value = []
    mock_model.predict.return_value = MagicMock(x=100.0, y=100.0)

    mock_fit = MagicMock(
        success=True,
        model=mock_model,
        rms_px=12.0,
        message="ok",
        candidate_reports=(),
        best_effort=False,
    )
    monkeypatch.setattr(
        "gazekey.ui.mapper_runtime.fit_calibration_mapper",
        lambda **kwargs: mock_fit,
    )
    return mock_fit


def _mock_quality(monkeypatch):
    quality = CalibrationQualityResult(
        usable=True,
        accepted=True,
        loocv_rms_px=45.0,
        warnings=[],
        reasons=[],
    )
    monkeypatch.setattr(
        "gazekey.ui.mapper_runtime.evaluate_calibration_quality",
        lambda **kwargs: quality,
    )
    return quality


def _prepare_session(vk, qapp, monkeypatch):
    targets = [MagicMock(label=f"T{i+1:02d}", screen_x=100.0 + i, screen_y=200.0) for i in range(15)]
    session = MagicMock()
    session.targets = targets
    session.accepted_count_for_target = lambda i: 1
    session.get_training_samples = _minimal_calibration_samples
    session.csv.session_id = "mvp-int-001"
    session.write_summary = MagicMock()
    session.print_training_means = MagicMock()

    vk._calibration_v2_session = session
    vk._calib2_mode = "keyboard15"
    vk._calib_clip_rect = (0.0, 0.0, 800.0, 400.0)
    csv_logger = MagicMock(session_id="mvp-int-001")
    vk._calibration_controller.csv_logger = csv_logger
    vk._is_calibrating = True

    monkeypatch.setattr(vk, "_ensure_camera_preview", MagicMock())
    monkeypatch.setattr(vk, "_mapper_store", MagicMock())
    monkeypatch.setattr(vk, "_write_calibration_debug_csv", MagicMock())
    monkeypatch.setattr(vk, "_print_target_sample_quality", MagicMock())
    monkeypatch.setattr(vk, "_print_row_v_stats_and_export_ratio_space", MagicMock())
    monkeypatch.setattr(
        "gazekey.ui.calibration_finish.print_geometric_diagnostics",
        MagicMock(),
    )
    monkeypatch.setattr(
        "gazekey.ui.mapper_runtime.assess_fullscreen_feasibility",
        MagicMock(),
    )

    _mock_ridge_fit(monkeypatch)
    _mock_quality(monkeypatch)
    vk.show()
    qapp.processEvents()
    vk._export_keyboard_layout()
    qapp.processEvents()
    return session


def _finish_calibration(vk, qapp):
    result = CalibrationV2Result(success=True, message="Target collection complete.", targets=vk._calibration_v2_session.targets)
    vk._on_calibration_finished(result)
    qapp.processEvents()
    from PySide6.QtTest import QTest

    QTest.qWait(200)
    qapp.processEvents()


def test_geometry_sanity_key_centers_match_layout_snapshot(qapp):
    """Visible key centers must match calibration target layout snapshot (pre-baseline gate)."""
    root = _build_test_keyboard(qapp)
    layout_keys = inspect_keyboard_layout(root)
    region = letter_keys_region_rect(root)
    targets = keyboard_geometry_targets(
        keys=layout_keys,
        typing_region_rect=region,
        mode="keyboard15",
    )
    by_key_id = {k.key_id: k for k in layout_keys}
    for t in targets:
        if not t.key_id:
            continue
        key = by_key_id[t.key_id]
        assert t.screen_x == pytest.approx(key.center[0])
        assert t.screen_y == pytest.approx(key.center[1])


def test_normal_flow_calibrate_preview_only(qapp, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GAZEKEY_DEV_BENCHMARK", raising=False)
    monkeypatch.delenv("GAZEKEY_VERBOSE", raising=False)

    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk._run_summary_writer = RunSummaryWriter(runs_dir=tmp_path)
    qapp.processEvents()

    start_benchmark = MagicMock()
    vk._start_mvp_benchmark = start_benchmark
    _prepare_session(vk, qapp, monkeypatch)
    _finish_calibration(vk, qapp)

    assert vk._gaze_mapper_v2 is not None
    assert vk._preview_mode is True
    assert vk._gaze_preview_active() is True
    assert vk._keyboard_accuracy_session is None
    start_benchmark.assert_not_called()

    cal_files = list(tmp_path.glob("calibration_*.txt"))
    assert len(cal_files) == 1
    assert "[calibration] PASS" in cal_files[0].read_text(encoding="utf-8")

    out = capsys.readouterr().out
    assert out.count("[calibration] PASS") == 1
    assert "[benchmark]" not in out
    assert "[calib2] t=" not in out
    assert "mapper freeze" not in out
    assert "per-target training means" not in out


def test_dev_benchmark_flow_auto_start_and_summary(qapp, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GAZEKEY_DEV_BENCHMARK", "1")
    monkeypatch.delenv("GAZEKEY_VERBOSE", raising=False)

    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk._run_summary_writer = RunSummaryWriter(runs_dir=tmp_path)
    qapp.processEvents()

    _prepare_session(vk, qapp, monkeypatch)
    _finish_calibration(vk, qapp)

    assert vk._preview_mode is True
    assert vk._keyboard_accuracy_session is not None

    rows = [_bench_row(correct=True, err=25.0, target=f"K{i}") for i in range(15)]
    vk._finish_mvp_benchmark(rows)
    qapp.processEvents()

    cal_files = list(tmp_path.glob("calibration_*.txt"))
    bench_files = list(tmp_path.glob("benchmark_*.txt"))
    assert len(cal_files) == 1
    assert len(bench_files) == 1
    assert "[calibration] PASS" in cal_files[0].read_text(encoding="utf-8")
    bench_text = bench_files[0].read_text(encoding="utf-8")
    assert "[benchmark]" in bench_text
    assert "keys=" in bench_text

    out = capsys.readouterr().out
    assert out.count("[calibration] PASS") == 1
    assert out.count("[benchmark]") == 1


def test_run_summary_writes_once_per_session(tmp_path):
    writer = RunSummaryWriter(runs_dir=tmp_path)
    writer.write_calibration_summary(
        session_id="once",
        status="passed",
        layout="keyboard15",
        targets_collected=15,
        targets_total=15,
    )
    writer.write_calibration_summary(
        session_id="once",
        status="passed",
        layout="keyboard15",
        targets_collected=15,
        targets_total=15,
    )
    assert len(list(tmp_path.glob("calibration_once.txt"))) == 1
