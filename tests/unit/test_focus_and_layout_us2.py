"""T051–T053: layout preservation and focus policies after typing integration."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.ui.virtual_keyboard import VirtualKeyboard


def test_top_half_keyboard_geometry_preserved(qapp):
    vk = VirtualKeyboard()
    vk._needs_first_calibration = False
    vk.show()
    qapp.processEvents()
    vk._keyboard_layout_builder.apply_full_keyboard_geometry()
    qapp.processEvents()

    screen = qapp.primaryScreen().availableGeometry()
    geo = vk.geometry()
    expected_h = int(screen.height() * 0.62)
    assert geo.x() == screen.x()
    assert geo.y() == screen.y()
    assert geo.width() == screen.width()
    assert abs(geo.height() - min(expected_h, screen.height())) <= 1


def test_calibration_overlay_uses_fullscreen_primary_geometry():
    """T051: calib presentation remains fullscreen primaryScreen().geometry()."""
    import inspect

    from gazekey.ui.calibration_overlay import CalibrationOverlay

    src = inspect.getsource(CalibrationOverlay._setup_window)
    assert "primaryScreen().geometry()" in src
    assert "availableGeometry" not in src


def test_keyboard_window_does_not_accept_focus(qapp):
    vk = VirtualKeyboard()
    vk._needs_first_calibration = False
    flags = vk.windowFlags()
    assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
    assert flags & Qt.WindowType.Tool
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert vk.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert vk.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_key_and_chrome_widgets_use_no_focus(qapp):
    vk = VirtualKeyboard()
    vk._needs_first_calibration = False
    qapp.processEvents()
    assert vk.text_display.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert vk.calibrate_btn.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert vk.pause_resume_btn.focusPolicy() == Qt.FocusPolicy.NoFocus
    keys = [b for b in vk.findChildren(QPushButton) if b.objectName() in ("keyboardKey", "gazeTarget")]
    assert keys, "expected keyboard keys"
    for btn in keys:
        assert btn.focusPolicy() == Qt.FocusPolicy.NoFocus, btn.text()
