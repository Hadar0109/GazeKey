"""Contract: dwell/mouse on system:calibrate → existing on_calibrate entry point."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from PySide6.QtCore import QRect

from gazekey.input.os_input_adapter import FakeOsInputAdapter
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DWELL_SEC, DwellEngine
from gazekey.typing.gaze_typing_runtime import GazeTypingRuntime, MappedGazePoint
from gazekey.typing.key_semantics import CALIBRATE_KEY_ID, is_calibrate_action
from gazekey.typing.typing_session import TypingSession


def _key(key_id: str, action: str, rect: QRect) -> SimpleNamespace:
    btn = MagicMock()
    btn.isEnabled.return_value = True
    return SimpleNamespace(
        key_id=key_id,
        key_action=action,
        key_label="CALIBRATE",
        rect=rect,
        button=btn,
    )


def test_is_calibrate_action_accepts_stable_id_and_legacy_action():
    assert is_calibrate_action(CALIBRATE_KEY_ID)
    assert is_calibrate_action("CALIBRATE")
    assert not is_calibrate_action("a")


def test_dwell_calibrate_invokes_existing_recalibration_entry_point():
    session = TypingSession()
    session.activate()
    calls: list[str] = []

    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        ActionDispatcher(FakeOsInputAdapter()),
        on_calibrate=lambda: calls.append("calib"),
    )
    keys = [_key(CALIBRATE_KEY_ID, CALIBRATE_KEY_ID, QRect(0, 0, 120, 60))]
    result = runtime.on_mapped_gaze(MappedGazePoint(60, 30, True), DWELL_SEC, keys)

    assert result.calibrate_requested is True
    assert calls == ["calib"]
    assert result.published is None


def test_mouse_calibrate_same_entry_point():
    session = TypingSession()
    session.activate()
    calls: list[str] = []
    runtime = GazeTypingRuntime(
        session,
        DwellEngine(),
        ActionDispatcher(FakeOsInputAdapter()),
        on_calibrate=lambda: calls.append("calib"),
    )
    runtime.on_mouse_key(key_id=CALIBRATE_KEY_ID, action=CALIBRATE_KEY_ID)
    assert calls == ["calib"]


def test_product_calibrate_button_wires_runtime_callback(qapp):
    """Composition root: GazeTypingRuntime.on_calibrate is VirtualKeyboard.on_calibrate_clicked."""
    from gazekey.ui.virtual_keyboard import VirtualKeyboard

    vk = VirtualKeyboard()
    vk._needs_first_calibration = False
    cb = vk._typing_runtime._on_calibrate
    assert cb is not None
    assert getattr(cb, "__self__", None) is vk
    assert getattr(cb, "__func__", None) is VirtualKeyboard.on_calibrate_clicked
    assert vk.calibrate_btn.property("gazeKeyId") == CALIBRATE_KEY_ID
    assert vk.calibrate_btn.property("gazeKeyAction") in {CALIBRATE_KEY_ID, "CALIBRATE"}
