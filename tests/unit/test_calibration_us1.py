"""US1: distraction-free calibration overlay and controller."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QPushButton, QWidget

from gazekey.calibration.fixation_gate import FixationGateConfig
from gazekey.calibration.session import CalibrationResult, CalibrationSession
from gazekey.calibration.targets import CalibrationTarget
from tools.evaluation.run_summary import RunSummaryWriter
from gazekey.ui.calibration_controller import CalibrationController
from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.ui.camera_preview_window import CameraPreviewWindow
from gazekey.typing.key_hit_tester import KEY_OBJECT_NAME


def _targets(n: int = 3):
    return [
        CalibrationTarget(
            target_id=f"T{i+1:02d}",
            label=f"p{i}",
            key_id="",
            screen_x=100.0 + i * 50,
            screen_y=200.0,
        )
        for i in range(n)
    ]


def test_calibration_overlay_minimal_progress_only(qapp):
    finished = []

    def on_done(res):
        finished.append(res)

    dots = [(100.0, 200.0), (150.0, 200.0), (200.0, 200.0)]
    session = CalibrationSession(
        targets=_targets(3),
        session_id="test-session",
        calibration_mode="keyboard15",
    )
    overlay = CalibrationOverlay(
        dot_targets=dots,
        screen_targets=[(x, y) for x, y in dots],
        on_finished=on_done,
        session=session,
        minimal_fixation_ui=True,
    )
    overlay.show()
    qapp.processEvents()

    assert overlay._title_label.isHidden()
    overlay._update_progress_only()
    assert overlay.status_label.text() == "1 / 3"
    assert "Look at" not in overlay.status_label.text()
    assert "avg_v" not in overlay.status_label.text()


def test_calibration_overlay_closes_without_pass_message_on_collection_complete(qapp):
    finished = []

    overlay = CalibrationOverlay(
        dot_targets=[(10.0, 10.0)],
        screen_targets=[(10.0, 10.0)],
        on_finished=lambda r: finished.append(r),
        session=CalibrationSession(targets=_targets(1), session_id="t1"),
        minimal_fixation_ui=True,
    )
    overlay.show()
    qapp.processEvents()

    result = CalibrationResult(success=True, message="Target collection complete.", targets=_targets(1))
    overlay._show_result(result)
    qapp.processEvents()

    assert len(finished) == 1
    assert "PASS" not in (overlay.status_label.text() or "").upper()


def test_camera_preview_blocked_during_calibration(qapp):
    win = CameraPreviewWindow()
    win.set_calibration_blocked(True)
    win.show()
    qapp.processEvents()
    assert not win.isVisible()
    win.set_calibration_blocked(False)
    win.show_post_calibration()
    qapp.processEvents()
    assert win.isVisible()


def test_camera_preview_during_calib_flag_default_off(monkeypatch):
    monkeypatch.delenv("GAZEKEY_CAMERA_PREVIEW_DURING_CALIB", raising=False)
    from gazekey.ui.env_flags import camera_preview_during_calib

    assert camera_preview_during_calib() is False


def test_camera_preview_during_calib_flag_opt_in(monkeypatch):
    monkeypatch.setenv("GAZEKEY_CAMERA_PREVIEW_DURING_CALIB", "1")
    from gazekey.ui.env_flags import camera_preview_during_calib

    assert camera_preview_during_calib() is True


def test_camera_preview_visible_during_calib_uses_same_window_path(qapp):
    """Flag on uses show_post_calibration — same bottom-right window as after calibration."""
    win = CameraPreviewWindow(dock="bottom_right")
    win.set_calibration_blocked(False)
    win.show_post_calibration()
    qapp.processEvents()
    assert win.isVisible()
    screen = win.screen().availableGeometry()
    margin = 20
    expected_x = screen.x() + screen.width() - win.width() - margin
    expected_y = screen.y() + screen.height() - win.height() - margin
    assert win.x() == expected_x
    assert win.y() == expected_y


def test_calibration_run_summary_format(tmp_path):
    writer = RunSummaryWriter(runs_dir=tmp_path)
    summary = writer.write_calibration_summary(
        session_id="abc123",
        status="passed",
        layout="keyboard15",
        targets_collected=15,
        targets_total=15,
        ridge_alpha=0.5,
        loocv_rms_px=48.5,
        quality_warnings=["LOOCV RMS 120.0px > 95.0px"],
    )
    text = writer.format_console(summary)
    assert "[calibration] PASS" in text
    assert "targets=15/15" in text
    assert "ridge_alpha=0.5" in text
    assert "loocv_rms=48.5px (supplementary)" in text
    assert "quality_warnings=1" in text


def test_calibration_overlay_hides_before_finish_callback(qapp):
    visibility = []

    def on_finished(_res):
        visibility.append(overlay.isVisible())

    dots = [(100.0, 200.0)]
    session = CalibrationSession(targets=_targets(1), session_id="t2")
    overlay = CalibrationOverlay(
        dot_targets=dots,
        screen_targets=dots,
        on_finished=on_finished,
        session=session,
        minimal_fixation_ui=True,
    )
    overlay.show()
    qapp.processEvents()

    overlay._show_result(
        CalibrationResult(success=True, message="Target collection complete.", targets=_targets(1))
    )
    qapp.processEvents()

    assert visibility == [False]


def test_calibration_controller_starts_session(qapp):
    root = QWidget()
    root.setGeometry(0, 0, 800, 400)
    y_rows = (50, 120, 190)
    keys = "QWEASDZXC"
    for i, ch in enumerate(keys):
        btn = QPushButton(ch, root)
        btn.setObjectName(KEY_OBJECT_NAME)
        btn.setGeometry(50 + (i % 3) * 70, y_rows[i // 3], 50, 40)
    root.show()
    qapp.processEvents()

    controller = CalibrationController()
    ctx = controller.start(
        keyboard_widget=root,
        on_finished=MagicMock(),
        gate_cfg=FixationGateConfig(),
        calibration_mode="keyboard15",
    )
    qapp.processEvents()

    assert ctx.session is controller.session
    assert ctx.overlay is controller.overlay
    assert controller.session_id
    assert len(ctx.session.targets) == 15
    assert ctx.overlay._minimal_fixation_ui is True

    controller.reset()
