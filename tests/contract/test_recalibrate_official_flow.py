"""T048 + recalibration resume: official flow, Qt rewire, no prior-model fallback."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QRect

from gazekey.backend.gaze_sample import GazeSample
from gazekey.backend.lifecycle import GazeFollowerLifecycle, GazeFollowerLifecycleError
from gazekey.backend.startup import run_official_recalibrate, run_official_startup
from gazekey.typing.dwell_engine import DwellPhase
from gazekey.ui.virtual_keyboard import VirtualKeyboard
from tests.unit.test_lifecycle import FakeGazeFollower, _patch_official


def test_calibrate_clicked_calls_official_recalibrate_not_legacy(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    calls: list[str] = []
    monkeypatch.setattr(
        "gazekey.backend.startup.run_official_recalibrate",
        lambda lifecycle, keyboard: calls.append("official") or True,
    )
    vk._gf_lifecycle = SimpleNamespace()
    vk.on_calibrate_clicked()
    assert calls == ["official"]
    assert not hasattr(vk, "_start_calibration")
    assert not hasattr(vk, "_calibration_overlay")
    assert not hasattr(vk, "tracking_manager")


def test_calibrate_without_lifecycle_does_not_start_overlay(qapp):
    vk = VirtualKeyboard()
    vk._gf_lifecycle = None
    vk.on_calibrate_clicked()
    assert not hasattr(vk, "_start_calibration")
    assert not hasattr(vk, "_calibration_overlay")


def _stub_keyboard() -> SimpleNamespace:
    return SimpleNamespace(
        _typing_runtime=SimpleNamespace(
            set_os_inject_enabled=lambda _enabled: None,
            dwell=SimpleNamespace(cancel_progress=lambda: None),
        ),
        _official_gaze_ready=True,
        hide=lambda: None,
        show=lambda: None,
        raise_=lambda: None,
        activateWindow=lambda: None,
        _gaze_loop=None,
        _ensure_typing_auto_started=lambda: None,
    )


def test_run_official_recalibrate_hides_keyboard_and_reruns_preview(qapp, monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    hidden: list[int] = []
    shown: list[int] = []
    keyboard = _stub_keyboard()
    keyboard.hide = lambda: hidden.append(1)
    keyboard.show = lambda: shown.append(1)
    monkeypatch.setattr("gazekey.backend.startup.wire_debug_gaze_dot", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "gazekey.backend.startup.wire_official_gaze_typing", lambda *_a, **_k: None
    )
    original = life.gf.calibration
    kept_new = run_official_recalibrate(life, keyboard)
    qapp.processEvents()
    assert kept_new is True
    assert hidden == [1]
    assert shown == [1]
    assert life.gf.preview_calls == 2
    assert life.gf.calibrate_calls == 2
    assert life.camera_state_name() == "SAMPLING"
    assert life.gf.calibration is original
    assert life.gf.calibration.token == "new"
    assert life.gf.calibration.has_calibrated is True


def _ready_keyboard(qapp) -> VirtualKeyboard:
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    vk._is_calibrating = False
    vk._official_gaze_ready = True
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(True)
    return vk


def _valid_sample() -> GazeSample:
    return GazeSample(
        timestamp_ns=1,
        valid=True,
        x=20.0,
        y=20.0,
        calibrated_x=20.0,
        calibrated_y=20.0,
        tracking_state="SUCCESS",
        left_openness=20.0,
        right_openness=21.0,
    )


def _invalid_sample() -> GazeSample:
    return GazeSample(
        timestamp_ns=2,
        valid=False,
        x=20.0,
        y=20.0,
        calibrated_x=None,
        calibrated_y=None,
        tracking_state="SUCCESS",
        left_openness=5.0,
        right_openness=20.0,
    )


def test_active_session_regains_os_inject_after_recalibrate(qapp, monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    vk = _ready_keyboard(qapp)
    vk._gf_lifecycle = life
    vk._typing_runtime.set_os_inject_enabled(True)
    kept_new = run_official_recalibrate(life, vk)
    qapp.processEvents()
    assert kept_new is True
    assert vk._typing_runtime.session.is_active
    assert vk._typing_runtime.os_inject_enabled is True


def test_qt_bridge_rewired_after_successful_recalibrate(qapp, monkeypatch):
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    vk = _ready_keyboard(qapp)
    vk._gf_lifecycle = life
    life.attach_debug_get_gaze_info_bridge(SimpleNamespace(update_xy=lambda *_a: None), parent=vk)
    life.attach_qt_bridge(parent=vk)
    assert life._qt_consumers
    kept_new = run_official_recalibrate(life, vk)
    assert life._qt_consumers == []
    qapp.processEvents()
    assert kept_new is True
    assert len(life._qt_consumers) >= 2
    for bridge in life._qt_consumers:
        assert bridge._timer.isActive()
    assert vk._gf_sample_bridge is not None
    assert vk._gf_typing_bridge is not None
    assert vk._gf_debug_overlay is not None


def test_lifecycle_error_fails_closed_without_stale_typing(qapp, monkeypatch):
    class BoomPreview(FakeGazeFollower):
        def preview(self, win=None) -> None:
            raise RuntimeError("pygame exploded")

    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=BoomPreview)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    life.construct()
    life.gf.camera.camera_running_state = SimpleNamespace(name="SAMPLING")
    vk = _ready_keyboard(qapp)
    vk._gf_lifecycle = life
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed"):
        run_official_recalibrate(life, vk)
    qapp.processEvents()
    assert life.gf.calibration.has_calibrated is False
    assert life.calibration_model_usable() is False
    assert vk._official_gaze_ready is False
    assert vk._typing_runtime.os_inject_enabled is False
    assert vk.isVisible()
    assert life._qt_consumers == []


def test_rejected_new_calibration_fails_closed_without_prior_model(qapp, monkeypatch):
    class FailOnSecond(FakeGazeFollower):
        def calibrate(self, win=None) -> None:
            self.calibrate_calls += 1
            self._win = win
            if self.calibrate_calls == 1:
                self.calibration.has_calibrated = True
                self._calibration_controller.cali_available = True
                return
            self.calibration.has_calibrated = False
            self.calibration.token = "failed"
            self._calibration_controller.cali_available = True

    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FailOnSecond)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    original = life.gf.calibration
    vk = _ready_keyboard(qapp)
    vk._gf_lifecycle = life
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed"):
        run_official_recalibrate(life, vk)
    qapp.processEvents()
    assert life.gf.calibration is original
    assert life.gf.calibration.token == "failed"
    assert life.gf.calibration.has_calibrated is False
    assert life.calibration_model_usable() is False
    assert vk._official_gaze_ready is False
    assert vk._typing_runtime.os_inject_enabled is False
    assert life._qt_consumers == []


def test_no_usable_old_or_new_model_fails_closed(qapp, monkeypatch):
    class NoModel(FakeGazeFollower):
        def __init__(self, config=None) -> None:
            super().__init__(config)
            self.calibration.has_calibrated = False
            self._calibration_controller.cali_available = False

        def calibrate(self, win=None) -> None:
            self.calibrate_calls += 1
            self.calibration.has_calibrated = False
            self._calibration_controller.cali_available = False

    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=NoModel)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    life.construct()
    shown: list[int] = []
    keyboard = _stub_keyboard()
    keyboard._official_gaze_ready = False
    keyboard.show = lambda: shown.append(1)
    with pytest.raises(GazeFollowerLifecycleError, match="Failing closed") as err:
        run_official_recalibrate(life, keyboard)
    qapp.processEvents()
    assert shown == [1]
    assert "not accepted" in str(err.value)
    assert "PCA4" in str(err.value)
    assert "TrackingManager" in str(err.value)
    assert life._qt_consumers == []


def test_recalibrate_production_gaze_path_unchanged(qapp, monkeypatch):
    times = iter([100.0, 100.4, 100.45, 100.5, 100.55, 100.6])
    monkeypatch.setattr("gazekey.runtime.gaze_loop.time.perf_counter", lambda: next(times))
    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    vk = _ready_keyboard(qapp)
    vk._gf_lifecycle = life
    vk._layout_keys = [
        SimpleNamespace(key_id="key_a", key_action="a", key_label="a", rect=QRect(0, 0, 40, 40))
    ]
    run_official_recalibrate(life, vk)
    qapp.processEvents()
    vk._gaze_loop.on_gaze_sample(_valid_sample())
    vk._gaze_loop.on_gaze_sample(_valid_sample())
    assert vk._dwell_engine.phase is DwellPhase.PROGRESSING
    vk._gaze_loop.on_gaze_sample(_invalid_sample())
    assert vk._dwell_engine.phase is DwellPhase.CANCELLED
    assert not hasattr(vk, "_gaze_smoother")
    src = (Path(__file__).resolve().parents[2] / "gazekey" / "backend" / "startup.py").read_text(
        encoding="utf-8"
    )
    fn = src.split("def run_official_recalibrate", 1)[1]
    assert "PCA4" not in fn
    assert "Ridge" not in fn
    assert "HeuristicFilter" not in fn
    assert "detach_usable_calibration" not in fn
    assert "restore_calibration_snapshot" not in fn
    assert "QTimer.singleShot" in src
    assert "_schedule_qt_consumer_resume" in fn
