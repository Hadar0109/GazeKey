"""Contract tests: selection → KeyAction → ActionDispatcher → FakeOsInputAdapter."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QRect

from gazekey.input.os_input_adapter import FakeOsInputAdapter, OsInjectResult
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_action import KeyActionKind, KeyActionSource
from gazekey.typing.typing_session import TypingSession


def _key(key_id: str, action: str, rect: QRect) -> SimpleNamespace:
    return SimpleNamespace(key_id=key_id, key_action=action, key_label=action, rect=rect)


def _runtime(adapter: FakeOsInputAdapter | None = None) -> tuple[GazeTypingRuntime, FakeOsInputAdapter]:
    fake = adapter or FakeOsInputAdapter()
    session = TypingSession()
    session.activate()
    runtime = GazeTypingRuntime(session, DwellEngine(), ActionDispatcher(fake))
    return runtime, fake


def test_dwell_completion_dispatches_key_action():
    runtime, adapter = _runtime()
    keys = [_key("key_a", "a", QRect(0, 0, 40, 40))]
    requested: list = []
    delivered: list = []
    runtime.dispatcher.on_action_requested(requested.append)
    runtime.dispatcher.on_action_delivered(lambda a, r: delivered.append((a, r)))

    runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), DWELL_SEC - 0.05, keys)
    assert adapter.injected == []

    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), 0.05, keys)
    assert result.published is not None
    assert result.published.kind is KeyActionKind.CHAR
    assert result.published.source is KeyActionSource.DWELL
    assert len(requested) == 1
    assert len(delivered) == 1
    assert delivered[0][1].ok is True
    assert adapter.injected[0].text == "a"


def test_mouse_click_same_dispatch_path():
    runtime, adapter = _runtime()
    published = runtime.on_mouse_key(key_id="key_b", action="b")
    assert published is not None
    assert published.source is KeyActionSource.MOUSE
    assert adapter.injected[0].text == "b"


def test_paused_state_no_os_inject():
    runtime, adapter = _runtime()
    runtime.session.pause()
    keys = [_key("key_a", "a", QRect(0, 0, 40, 40))]
    result = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), DWELL_SEC, keys)
    assert result.published is None
    assert adapter.injected == []
    assert runtime.on_mouse_key(key_id="key_a", action="a") is None
    assert adapter.injected == []


def test_delivery_failure_still_emits_delivered_with_ok_false():
    adapter = FakeOsInputAdapter(fail=True, error="no_target")
    runtime, _ = _runtime(adapter)
    delivered: list[tuple] = []
    runtime.dispatcher.on_action_delivered(lambda a, r: delivered.append((a, r)))

    published = runtime.on_mouse_key(key_id="key_x", action="x")
    assert published is not None
    assert len(delivered) == 1
    assert delivered[0][1] == OsInjectResult(ok=False, error="no_target")
    assert adapter.injected[0].text == "x"


def test_space_backspace_enter_still_dispatch():
    """T027: OS path unchanged for Space, Backspace, and Enter."""
    runtime, adapter = _runtime()
    space = runtime.on_mouse_key(key_id="key_space", action=" ")
    assert space is not None
    assert space.kind is KeyActionKind.CHAR
    assert space.text == " "
    backspace = runtime.on_mouse_key(key_id="key_bs", action="BACKSPACE")
    assert backspace is not None
    assert backspace.kind is KeyActionKind.BACKSPACE
    enter = runtime.on_mouse_key(key_id="key_enter", action="ENTER")
    assert enter is not None
    assert enter.kind is KeyActionKind.ENTER
    assert [a.kind for a in adapter.injected] == [
        KeyActionKind.CHAR,
        KeyActionKind.BACKSPACE,
        KeyActionKind.ENTER,
    ]
