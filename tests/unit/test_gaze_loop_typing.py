"""T042–T045: gaze-loop typing auto-start, Pause/Resume, mouse path, calib guard."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QRect

from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_semantics import PAUSE_RESUME_ACTION, action_from_label, is_pause_resume_action
from gazekey.typing.typing_session import TypingSession
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def _key(key_id: str, action: str, rect: QRect) -> SimpleNamespace:
    return SimpleNamespace(key_id=key_id, key_action=action, key_label=action, rect=rect)


def test_pause_resume_label_maps_to_system_action():
    assert action_from_label("Pause") == PAUSE_RESUME_ACTION
    assert action_from_label("Resume") == PAUSE_RESUME_ACTION
    assert is_pause_resume_action(PAUSE_RESUME_ACTION)


def test_pause_resume_dwell_toggles_without_os_inject():
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    dwell = DwellEngine()
    runtime = GazeTypingRuntime(session, dwell, ActionDispatcher(adapter))
    keys = [_key("pause", PAUSE_RESUME_ACTION, QRect(0, 0, 40, 40))]

    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), DWELL_SEC, keys)
    assert result.published is None
    assert result.system_toggled is True
    assert session.is_paused
    assert adapter.injected == []

    # Confirmed leave + drain cooldown far from the key geometry.
    for _ in range(5):
        runtime.on_mapped_gaze(MappedGazePoint(-1000, -1000, True), 0.05, keys)
    assert dwell.locked_key_id is None

    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), DWELL_SEC, keys)
    assert result.system_toggled is True
    assert session.is_active
    assert adapter.injected == []


def test_mouse_os_key_uses_dispatcher():
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    runtime = GazeTypingRuntime(session, DwellEngine(), ActionDispatcher(adapter))
    published = runtime.on_mouse_key(key_id="key_a", action="a")
    assert published is not None
    assert adapter.injected[0].text == "a"


def test_os_inject_disabled_during_calibration_guard():
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    runtime = GazeTypingRuntime(session, DwellEngine(), ActionDispatcher(adapter))
    runtime.set_os_inject_enabled(False)
    keys = [_key("key_a", "a", QRect(0, 0, 40, 40))]
    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), DWELL_SEC, keys)
    assert result.published is None
    assert adapter.injected == []
    assert runtime.on_mouse_key(key_id="key_a", action="a") is None


def test_gaze_loop_typing_active_when_usable_mapper(qapp):
    vk = VirtualKeyboard()
    vk._is_calibrating = False
    vk.is_expanded = True
    vk._gaze_mapper = MagicMock()
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(True)

    assert hasattr(vk._gaze_loop, "process_gaze_typing")
    assert vk._gaze_loop.gaze_typing_active() is True


def test_gaze_loop_skips_typing_while_calibrating(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk._is_calibrating = True
    vk._calibration_overlay = MagicMock()
    vk.is_expanded = True
    vk._gaze_mapper = MagicMock()
    vk._typing_runtime.session.activate()

    calls = []
    monkeypatch.setattr(vk._gaze_loop, "process_gaze_typing", lambda *a, **k: calls.append("typing"))
    monkeypatch.setattr(vk._gaze_loop, "_process_calibration_eye_data", lambda *a, **k: calls.append("calib"))

    eye = MagicMock()
    eye.face_detected = False
    eye.left_iris_center = None
    eye.right_iris_center = None
    vk.tracking_manager = None
    vk._gaze_loop.on_eye_data_main_thread(eye)

    assert calls == ["calib"]
    assert vk._gaze_loop.gaze_typing_active() is False


def test_virtual_keyboard_mouse_routes_to_dispatcher_when_active(qapp, monkeypatch):
    vk = VirtualKeyboard()
    vk._is_calibrating = False
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(True)
    injected = []
    monkeypatch.setattr(
        vk._typing_runtime,
        "on_mouse_key",
        lambda **kwargs: injected.append(kwargs) or None,
    )

    vk.on_key_pressed("a")
    assert injected and injected[0]["action"] == "a"
    assert not hasattr(vk, "_text_buffer")


def test_ensure_typing_auto_started_reenables_inject_when_official_session_active(qapp):
    vk = VirtualKeyboard()
    vk._is_calibrating = False
    vk._official_gaze_ready = True
    vk._typing_runtime.session.activate()
    vk._typing_runtime.set_os_inject_enabled(False)
    vk._ensure_typing_auto_started()
    assert vk._typing_runtime.os_inject_enabled is True
    assert vk._typing_runtime.session.is_active
