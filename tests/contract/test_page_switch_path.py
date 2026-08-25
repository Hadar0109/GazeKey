"""Contract: dwell/mouse on system:page_* → page-switch callback, no OS input."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QRect

from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_semantics import (
    PAGE_LEFT_KEY_ID,
    PAGE_RIGHT_KEY_ID,
    is_page_switch_action,
)
from gazekey.typing.typing_session import TypingSession


def _key(key_id: str, action: str, rect: QRect) -> SimpleNamespace:
    btn = MagicMock()
    btn.isEnabled.return_value = True
    return SimpleNamespace(
        key_id=key_id,
        key_action=action,
        key_label="→" if key_id == PAGE_RIGHT_KEY_ID else "←",
        rect=rect,
        button=btn,
    )


def test_is_page_switch_action_accepts_stable_ids():
    assert is_page_switch_action(PAGE_RIGHT_KEY_ID)
    assert is_page_switch_action(PAGE_LEFT_KEY_ID)
    assert not is_page_switch_action("system:calibrate")
    assert not is_page_switch_action("a")


def _runtime_with_page_switch():
    session = TypingSession()
    session.activate()
    adapter = FakeOsInputAdapter()
    calls: list[str] = []
    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        ActionDispatcher(adapter),
        on_page_switch=lambda: calls.append("switch"),
    )
    return runtime, adapter, calls


def test_dwell_page_right_invokes_callback_without_os_inject():
    runtime, adapter, calls = _runtime_with_page_switch()
    keys = [_key(PAGE_RIGHT_KEY_ID, PAGE_RIGHT_KEY_ID, QRect(0, 0, 80, 120))]
    result = runtime.on_mapped_gaze(MappedGazePoint(40, 60, True), DWELL_SEC, keys)

    assert calls == ["switch"]
    assert result.published is None
    assert adapter.injected == []


def test_dwell_page_left_invokes_callback_without_os_inject():
    runtime, adapter, calls = _runtime_with_page_switch()
    keys = [_key(PAGE_LEFT_KEY_ID, PAGE_LEFT_KEY_ID, QRect(0, 0, 80, 120))]
    result = runtime.on_mapped_gaze(MappedGazePoint(40, 60, True), DWELL_SEC, keys)

    assert calls == ["switch"]
    assert result.published is None
    assert adapter.injected == []


def test_mouse_page_switch_same_callback_no_os_events():
    runtime, adapter, calls = _runtime_with_page_switch()
    published = runtime.on_mouse_key(key_id=PAGE_RIGHT_KEY_ID, action=PAGE_RIGHT_KEY_ID)
    assert calls == ["switch"]
    assert published is None
    assert adapter.injected == []
    published = runtime.on_mouse_key(key_id=PAGE_LEFT_KEY_ID, action=PAGE_LEFT_KEY_ID)
    assert calls == ["switch", "switch"]
    assert published is None
    assert adapter.injected == []


def test_product_page_switch_wires_runtime_callback(qapp):
    """Composition root: GazeTypingRuntime.on_page_switch is VirtualKeyboard handler."""
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    cb = vk._typing_runtime._on_page_switch
    assert cb is not None
    assert getattr(cb, "__self__", None) is vk
    assert vk.page_switch_btn.property("gazeKeyId") == PAGE_RIGHT_KEY_ID
    assert vk.page_switch_btn.property("gazeKeyAction") == PAGE_RIGHT_KEY_ID
    assert vk.page_switch_btn.objectName() == "gazeTarget"
