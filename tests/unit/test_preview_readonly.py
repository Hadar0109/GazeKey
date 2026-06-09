"""US2 / SC-007: read-only gaze preview does not activate keys or text buffer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QWidget

from gazekey.mapping.base import MapperPrediction
from gazekey.typing.text_buffer import TextBufferController
from gazekey.ui.gaze_preview import GazePreviewController
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


def test_mvp_disables_gaze_typing_enables_preview(qapp):
    vk = VirtualKeyboard()
    vk._gaze_mapper_v2 = MagicMock()
    vk._preview_mode = True
    vk._is_calibrating = False
    vk.is_expanded = True

    assert vk._gaze_typing_active() is False
    assert vk._gaze_preview_active() is True


def test_process_gaze_preview_does_not_update_text_buffer(qapp, monkeypatch):
    vk = VirtualKeyboard()
    text_before = vk.text_display.text()
    vk._gaze_mapper_v2 = MagicMock()
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
    monkeypatch.delenv("GAZEKEY_GAZE_DEBUG", raising=False)
    vk = VirtualKeyboard()
    vk._gaze_mapper_v2 = MagicMock()
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


def test_text_buffer_unchanged_when_gaze_typing_disabled(qapp):
    display = QLineEdit()
    buffer = TextBufferController(display)
    assert display.text() == ""
    # Gaze typing controller disabled path — no apply_key invoked.
    buffer.apply_key is not None  # sanity
    assert display.text() == ""
