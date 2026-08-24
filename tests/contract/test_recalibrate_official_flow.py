"""T048: Calibrate invokes official GazeFollower flow, not CalibrationOverlay."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from gazekey.ui.virtual_keyboard import VirtualKeyboard


def test_calibrate_clicked_calls_official_recalibrate_not_legacy(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk.show()
    qapp.processEvents()
    calls: list[str] = []
    monkeypatch.setattr(
        vk,
        "_start_calibration",
        lambda: calls.append("legacy") or None,
    )
    monkeypatch.setattr(
        "gazekey.backend.startup.run_official_recalibrate",
        lambda lifecycle, keyboard: calls.append("official") or True,
    )
    vk._gf_lifecycle = SimpleNamespace()
    vk.on_calibrate_clicked()
    assert calls == ["official"]
    assert vk._calibration_overlay is None
    assert vk.tracking_manager is None


def test_calibrate_without_lifecycle_does_not_start_overlay(qapp, monkeypatch):
    vk = VirtualKeyboard()
    monkeypatch.setattr(vk, "_start_calibration", MagicMock())
    vk._gf_lifecycle = None
    vk.on_calibrate_clicked()
    vk._start_calibration.assert_not_called()
    assert vk._calibration_overlay is None


def test_run_official_recalibrate_hides_keyboard_and_reruns_preview(monkeypatch):
    from gazekey.backend.lifecycle import GazeFollowerLifecycle
    from gazekey.backend.startup import run_official_recalibrate, run_official_startup
    from tests.unit.test_lifecycle import FakeGazeFollower, _patch_official

    _patch_official(monkeypatch)
    life = GazeFollowerLifecycle(gf_factory=FakeGazeFollower)
    monkeypatch.setattr(life, "_ensure_pygame_window", lambda: "win")
    run_official_startup(life)
    hidden: list[int] = []
    shown: list[int] = []
    keyboard = SimpleNamespace(
        _typing_runtime=SimpleNamespace(
            set_os_inject_enabled=lambda _enabled: None,
            dwell=SimpleNamespace(cancel_progress=lambda: None),
        ),
        _official_gaze_ready=True,
        hide=lambda: hidden.append(1),
        show=lambda: shown.append(1),
        raise_=lambda: None,
        activateWindow=lambda: None,
        _gaze_loop=None,
        _ensure_typing_auto_started=lambda: None,
    )
    monkeypatch.setattr("gazekey.backend.startup.wire_debug_gaze_dot", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "gazekey.backend.startup.wire_official_gaze_typing", lambda *_a, **_k: None
    )
    accepted = run_official_recalibrate(life, keyboard)
    assert accepted is True
    assert hidden == [1]
    assert shown == [1]
    assert life.gf.preview_calls == 2
    assert life.gf.calibrate_calls == 2
    assert life.camera_state_name() == "SAMPLING"
