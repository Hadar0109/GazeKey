"""US2 / SC-007: read-only gaze preview does not activate keys or text fields."""

from __future__ import annotations

from unittest.mock import MagicMock

from PySide6.QtWidgets import QWidget

from tools.preview.gaze_preview import GazePreviewController
from tools.devtools_install import install_devtools
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def test_gaze_preview_controller_updates_dot_only(qapp):
    root = QWidget()
    root.setGeometry(0, 0, 400, 200)
    root.show()
    qapp.processEvents()

    preview = GazePreviewController(root)
    preview.show_gaze(50.0, 60.0)
    qapp.processEvents()

    dot = preview.ensure_dot()
    assert dot.isVisible()
    assert dot._pos is not None


def test_mvp_product_exposes_typing_and_tools_preview_is_readonly(qapp):
    """Product has typing path; tools preview mode must not claim OS typing active."""
    vk = VirtualKeyboard()
    vk._gaze_mapper = MagicMock()
    vk._is_calibrating = False
    vk.is_expanded = True

    assert hasattr(vk._gaze_loop, "process_gaze_typing")
    assert hasattr(vk._gaze_loop, "gaze_typing_active")
    assert not hasattr(vk, "_text_buffer")

    # Default product path is not tools-preview; session may still be inactive
    # until calib activates a usable mapper (see test_gaze_loop_typing).
    assert vk._preview_mode is False
    assert vk._gaze_preview_active() is False

    # When tools preview is explicitly on, preview is active and typing is not.
    vk._preview_mode = True
    assert vk._gaze_preview_active() is True
    assert vk._gaze_loop.gaze_typing_active() is False


def test_process_gaze_preview_does_not_update_text_display(qapp, monkeypatch):
    vk = VirtualKeyboard()
    install_devtools(vk, enable_preview=True, enable_benchmark=False, auto_preview_after_calib=False)
    text_before = vk.text_display.text()
    vk._gaze_mapper = MagicMock()
    vk._preview_mode = True
    vk._is_calibrating = False
    vk.is_expanded = True

    monkeypatch.setattr(
        vk,
        "_preview_mapped_screen_xy",
        lambda eye_data, now_ms: (120.0, 80.0),
    )
    activate_calls = []
    monkeypatch.setattr(vk, "_on_gaze_activate_key", lambda btn: activate_calls.append(btn))

    vk._process_gaze_preview(MagicMock(), 0.016)
    qapp.processEvents()

    assert vk.text_display.text() == text_before
    assert not activate_calls
    assert vk._gaze_preview is not None


def test_preview_shows_single_mapped_dot_by_default(qapp, monkeypatch):
    vk = VirtualKeyboard()
    install_devtools(vk, enable_preview=True, enable_benchmark=False, auto_preview_after_calib=False)
    vk._gaze_mapper = MagicMock()
    vk._preview_mode = True
    vk._is_calibrating = False
    vk.is_expanded = True
    vk._rt2_debug = False

    monkeypatch.setattr(
        vk,
        "_preview_mapped_screen_xy",
        lambda eye_data, now_ms: (100.0, 200.0),
    )

    vk._process_gaze_preview(MagicMock(), 0.016)
    qapp.processEvents()

    dot = vk._gaze_preview.ensure_dot()
    assert dot._pos is not None
    assert dot._raw_pos is None
    assert dot._label == ""


def test_gaze_preview_clear_removes_benchmark_label(qapp):
    root = QWidget()
    root.setGeometry(0, 0, 400, 200)
    root.show()
    qapp.processEvents()

    preview = GazePreviewController(root)
    preview.show_gaze(50.0, 60.0, label="benchmark: Q", raw_global=(48.0, 58.0), show_raw=True)
    preview.clear_gaze()
    qapp.processEvents()

    dot = preview.ensure_dot()
    assert dot._pos is None
    assert dot._raw_pos is None
    assert dot._label == ""


def test_delivery_failure_shows_nonblocking_status(qapp):
    vk = VirtualKeyboard()
    vk._typing_runtime.session.activate()
    from gazekey.input.os_input_adapter import OsInjectResult
    from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource

    action = KeyAction(
        kind=KeyActionKind.CHAR,
        text="z",
        source=KeyActionSource.MOUSE,
        key_id="k",
        timestamp=1.0,
    )
    mapper_before = vk._gaze_mapper
    vk._on_os_action_delivered(action, OsInjectResult(ok=False, error="no_target"))
    assert "OS typing unavailable" in vk.text_display.text()
    assert vk._typing_runtime.session.is_active
    assert vk._gaze_mapper is mapper_before
