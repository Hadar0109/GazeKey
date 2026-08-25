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


def test_shift_survives_page_switch_then_letter_consumes():
    """T026: armed one-shot Shift still applies after page switch; then clears."""
    from gazekey.typing.key_semantics import PAGE_RIGHT_KEY_ID

    runtime, adapter, _keys = _runtime()
    switches: list[str] = []
    runtime._on_page_switch = lambda: switches.append("switch")

    runtime.on_mouse_key(key_id="key_shift", action="SHIFT")
    assert runtime.session.shift_oneshot_armed is True
    assert adapter.injected == []

    published = runtime.on_mouse_key(key_id=PAGE_RIGHT_KEY_ID, action=PAGE_RIGHT_KEY_ID)
    assert published is None
    assert switches == ["switch"]
    assert runtime.session.shift_oneshot_armed is True
    assert adapter.injected == []

    published = runtime.on_mouse_key(key_id="key_h", action="h")
    assert published is not None
    assert published.text == "H"
    assert runtime.session.shift_oneshot_armed is False
    assert adapter.injected[-1].text == "H"


def test_in_progress_letter_dwell_cancelled_by_page_switch_does_not_publish():
    """T034: completed arrow must not publish the previous letter (US4 scenario 4)."""
    from gazekey.typing.dwell_engine import KEY_SWITCH_CONFIRM_SEC
    from gazekey.typing.key_semantics import PAGE_RIGHT_KEY_ID

    runtime, adapter, _keys = _runtime()
    switches: list[str] = []
    runtime._on_page_switch = lambda: switches.append("switch")
    keys = [
        _key("key_q", "q", QRect(0, 0, 40, 40)),
        _key(PAGE_RIGHT_KEY_ID, PAGE_RIGHT_KEY_ID, QRect(100, 0, 80, 80)),
    ]

    mid = runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), 0.5, keys)
    assert mid.published is None
    assert adapter.injected == []

    switched = runtime.on_mapped_gaze(
        MappedGazePoint(140, 40, True), KEY_SWITCH_CONFIRM_SEC, keys
    )
    assert switched.published is None
    assert switched.dwell.target_key_id == PAGE_RIGHT_KEY_ID

    result = runtime.on_mapped_gaze(MappedGazePoint(140, 40, True), DWELL_SEC, keys)
    assert result.published is None
    assert result.page_switch_requested is True
    assert switches == ["switch"]
    assert adapter.injected == []
    assert runtime.dwell.progress_01 == 0.0


def test_in_progress_suggestion_dwell_cancelled_by_page_switch_does_not_accept():
    """T034: completed arrow must not accept a suggestion (US4 edge case)."""
    from gazekey.typing.dwell_engine import KEY_SWITCH_CONFIRM_SEC
    from gazekey.typing.key_semantics import PAGE_RIGHT_KEY_ID

    runtime, adapter, _keys = _runtime()
    switches: list[str] = []
    accepts: list[str] = []
    runtime._on_page_switch = lambda: switches.append("switch")
    runtime._on_suggestion_accept = lambda key_id, source: accepts.append(key_id)
    keys = [
        _key("suggestion:0", "suggestion:0", QRect(0, 0, 80, 40)),
        _key(PAGE_RIGHT_KEY_ID, PAGE_RIGHT_KEY_ID, QRect(200, 0, 80, 80)),
    ]

    mid = runtime.on_mapped_gaze(MappedGazePoint(40, 20, True), 0.5, keys)
    assert mid.suggestion_accepted is False
    assert accepts == []

    runtime.on_mapped_gaze(
        MappedGazePoint(240, 40, True), KEY_SWITCH_CONFIRM_SEC, keys
    )
    result = runtime.on_mapped_gaze(MappedGazePoint(240, 40, True), DWELL_SEC, keys)
    assert result.suggestion_accepted is False
    assert result.page_switch_requested is True
    assert result.published is None
    assert accepts == []
    assert switches == ["switch"]
    assert adapter.injected == []


def test_mouse_page_switch_cancels_in_progress_letter_and_suggestion_dwell():
    """T034: mouse arrow uses the same cancel path; no letter or suggestion fire."""
    from gazekey.typing.key_semantics import PAGE_RIGHT_KEY_ID

    runtime, adapter, _keys = _runtime()
    switches: list[str] = []
    accepts: list[str] = []
    runtime._on_page_switch = lambda: switches.append("switch")
    runtime._on_suggestion_accept = lambda key_id, source: accepts.append(key_id)
    letter_keys = [
        _key("key_q", "q", QRect(0, 0, 40, 40)),
        _key(PAGE_RIGHT_KEY_ID, PAGE_RIGHT_KEY_ID, QRect(100, 0, 80, 80)),
    ]
    runtime.on_mapped_gaze(MappedGazePoint(20, 20, True), 0.5, letter_keys)
    published = runtime.on_mouse_key(key_id=PAGE_RIGHT_KEY_ID, action=PAGE_RIGHT_KEY_ID)
    assert published is None
    assert switches == ["switch"]
    assert adapter.injected == []
    assert runtime.dwell.progress_01 == 0.0

    suggestion_keys = [
        _key("suggestion:0", "suggestion:0", QRect(0, 0, 80, 40)),
        _key(PAGE_RIGHT_KEY_ID, PAGE_RIGHT_KEY_ID, QRect(200, 0, 80, 80)),
    ]
    runtime.on_mapped_gaze(MappedGazePoint(40, 20, True), 0.5, suggestion_keys)
    published = runtime.on_mouse_key(key_id=PAGE_RIGHT_KEY_ID, action=PAGE_RIGHT_KEY_ID)
    assert published is None
    assert accepts == []
    assert switches == ["switch", "switch"]
    assert adapter.injected == []
