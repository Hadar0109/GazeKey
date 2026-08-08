"""Unit tests for GazeTypingRuntime hit-test → dwell → KeyAction path."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QRect

from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_action import KeyActionKind, KeyActionSource
from gazekey.typing.key_semantics import is_os_bound_action, role_for_action, KeyRole
from gazekey.typing.typing_session import TypingSession


def _key(key_id: str, action: str, rect: QRect) -> SimpleNamespace:
    return SimpleNamespace(key_id=key_id, key_action=action, key_label=action, rect=rect)


def _runtime() -> tuple[GazeTypingRuntime, FakeOsInputAdapter, list]:
    adapter = FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    runtime = GazeTypingRuntime(session, DwellEngine(), ActionDispatcher(adapter))
    keys = [_key("key_a", "a", QRect(0, 0, 40, 40))]
    return runtime, adapter, keys


def test_os_bound_semantics():
    assert is_os_bound_action("a")
    assert is_os_bound_action(" ")
    assert is_os_bound_action("BACKSPACE")
    assert is_os_bound_action("ENTER")
    assert not is_os_bound_action("SHIFT")
    assert not is_os_bound_action("CTRL")
    assert not is_os_bound_action("ALT")
    assert not is_os_bound_action("1")
    assert role_for_action("SHIFT") is KeyRole.SHIFT_ONESHOT


def test_dwell_completion_publishes_char():
    runtime, adapter, keys = _runtime()
    requested: list = []
    runtime.dispatcher.on_action_requested(requested.append)

    gaze = MappedGazePoint(x=20, y=20, valid=True)
    runtime.on_mapped_gaze(gaze, DWELL_SEC - 0.1, keys)
    assert adapter.injected == []

    result = runtime.on_mapped_gaze(gaze, 0.1, keys)
    assert result.published is not None
    assert result.published.kind is KeyActionKind.CHAR
    assert result.published.text == "a"
    assert result.published.source is KeyActionSource.DWELL
    assert len(requested) == 1
    assert adapter.injected[0].text == "a"


def test_gaze_loss_cancels_no_publish():
    runtime, adapter, keys = _runtime()
    gaze = MappedGazePoint(x=20, y=20, valid=True)
    runtime.on_mapped_gaze(gaze, 0.8, keys)
    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, False), 0.2, keys)
    assert result.published is None
    assert adapter.injected == []


def test_paused_drops_os_dwell_but_allows_pause_resume():
    runtime, adapter, keys = _runtime()
    runtime.session.pause()
    gaze = MappedGazePoint(x=20, y=20, valid=True)
    result = runtime.on_mapped_gaze(gaze, DWELL_SEC, keys)
    assert result.published is None
    assert adapter.injected == []

    pause_keys = [_key("pause", "PAUSE_RESUME", QRect(0, 0, 40, 40))]
    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), DWELL_SEC, pause_keys)
    assert result.system_toggled is True
    assert runtime.session.is_active
    assert adapter.injected == []


def test_shift_then_letter_uppercase():
    runtime, adapter, keys = _runtime()
    keys_shift = [
        _key("key_shift", "SHIFT", QRect(100, 0, 40, 40)),
        _key("key_a", "a", QRect(0, 0, 40, 40)),
    ]
    runtime.on_mapped_gaze(MappedGazePoint(120, 20, True), DWELL_SEC, keys_shift)
    assert runtime.session.shift_oneshot_armed is True
    assert adapter.injected == []

    # Leave shift lock, drain cooldown
    for _ in range(5):
        runtime.on_mapped_gaze(MappedGazePoint(-100, -100, True), 0.05, keys_shift)
    runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), 1.0, keys_shift)

    assert adapter.injected[-1].text == "A"
    assert runtime.session.shift_oneshot_armed is False


def test_mouse_same_key_action_path():
    runtime, adapter, _keys = _runtime()
    published = runtime.on_mouse_key(key_id="key_b", action="b")
    assert published is not None
    assert published.text == "b"
    assert published.source is KeyActionSource.MOUSE
    assert adapter.injected[0].text == "b"


def test_ctrl_alt_no_os_action():
    runtime, adapter, _keys = _runtime()
    assert runtime.on_mouse_key(key_id="ctrl", action="CTRL") is None
    assert runtime.on_mouse_key(key_id="alt", action="ALT") is None
    assert adapter.injected == []
