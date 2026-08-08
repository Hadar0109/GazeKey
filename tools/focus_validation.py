"""
Early Windows focus validation harness (quickstart.md §B / T034).

Simulates: external typing target focused → product keyboard at current
top-half geometry (with a fullscreen-calib overlay show/hide cycle) →
inject KeyActions via ActionDispatcher + PynputOsInputAdapter without
restoring focus between characters.

Does not change calibration/PCA4 behavior or keyboard geometry.
"""

from __future__ import annotations

import sys
import time

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QPlainTextEdit, QWidget

from gazekey.input.pynput_adapter import PynputOsInputAdapter
from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.key_action import KeyAction, KeyActionKind, KeyActionSource
from gazekey.ui.virtual_keyboard import VirtualKeyboard


EXPECTED = "hi"


class ExternalTarget(QMainWindow):
    """Stand-in for an external editor in the lower half of the screen."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("FocusValidationTarget")
        self.editor = QPlainTextEdit()
        self.setCentralWidget(self.editor)
        screen = QApplication.primaryScreen().availableGeometry()
        # Leave the top ~62% free for the product keyboard geometry.
        top = screen.y() + int(screen.height() * 0.62)
        self.setGeometry(
            screen.x(),
            top,
            screen.width(),
            screen.height() - int(screen.height() * 0.62),
        )


def _fullscreen_calib_like_overlay() -> QWidget:
    """Minimal fullscreen overlay matching product calib window flags."""
    overlay = QWidget()
    screen = QApplication.primaryScreen().geometry()
    overlay.setGeometry(screen)
    overlay.setWindowFlags(
        Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
        | Qt.WindowType.Tool
    )
    overlay.setStyleSheet("background-color: rgba(10, 10, 20, 230);")
    return overlay


def _publish_chars(dispatcher: ActionDispatcher, text: str) -> list:
    results = []
    for ch in text:
        action = KeyAction(
            kind=KeyActionKind.CHAR,
            text=ch,
            source=KeyActionSource.DWELL,
            key_id=f"key_{ch}",
            timestamp=time.time(),
        )
        results.append(dispatcher.publish(action))
        # No focus restore between characters — intentional.
        QApplication.processEvents()
        time.sleep(0.05)
    return results


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    target = ExternalTarget()
    target.show()
    target.raise_()
    target.activateWindow()
    target.editor.setFocus(Qt.FocusReason.OtherFocusReason)
    app.processEvents()
    time.sleep(0.2)

    keyboard = VirtualKeyboard()
    # Skip auto-start calibration; we only need post-calib geometry + inject path.
    keyboard._needs_first_calibration = False
    keyboard.show()
    # Do NOT activate/raise keyboard — external target must keep OS focus.
    app.processEvents()

    builder = keyboard._keyboard_layout_builder
    builder.apply_full_keyboard_geometry()
    app.processEvents()

    geo = keyboard.geometry()
    screen = app.primaryScreen().availableGeometry()
    expected_h = int(screen.height() * 0.62)
    geometry_ok = (
        geo.x() == screen.x()
        and geo.y() == screen.y()
        and geo.width() == screen.width()
        and abs(geo.height() - min(expected_h, screen.height())) <= 1
    )

    # Simulate fullscreen calibration overlay lifecycle (steals focus, then closes).
    overlay = _fullscreen_calib_like_overlay()
    overlay.show()
    overlay.raise_()
    overlay.activateWindow()
    app.processEvents()
    time.sleep(0.15)
    overlay.hide()
    overlay.close()
    app.processEvents()

    # Re-assert top-half keyboard without activating it (post-calib product state).
    # Critical: do NOT re-activate the external target here — quickstart requires
    # inject to reach the external app without restoring focus between characters
    # after the post-calib keyboard is visible.
    builder.apply_full_keyboard_geometry()
    keyboard.show()
    app.processEvents()
    time.sleep(0.2)

    focus_widget = app.focusWidget()
    target_had_focus = focus_widget is target.editor
    print(f"  focus_after_calib_cycle={type(focus_widget).__name__ if focus_widget else None}")

    dispatcher = ActionDispatcher(PynputOsInputAdapter())
    delivered: list = []
    dispatcher.on_action_delivered(lambda _a, r: delivered.append(r))
    inject_results = _publish_chars(dispatcher, EXPECTED)

    app.processEvents()
    time.sleep(0.25)
    app.processEvents()

    got = target.editor.toPlainText()
    keyboard_text = ""
    if hasattr(keyboard, "text_display"):
        keyboard_text = keyboard.text_display.text()

    all_ok = all(r.ok for r in inject_results)
    chars_in_target = got == EXPECTED
    chars_not_in_keyboard = EXPECTED not in keyboard_text
    passed = (
        geometry_ok
        and target_had_focus
        and all_ok
        and chars_in_target
        and chars_not_in_keyboard
    )

    print("FOCUS_VALIDATION_RESULT")
    print(
        f"  geometry_ok={geometry_ok} geo=({geo.x()},{geo.y()} "
        f"{geo.width()}x{geo.height()}) expected_h~={expected_h}"
    )
    print(f"  target_had_focus_before_inject={target_had_focus}")
    print(f"  inject_all_ok={all_ok} delivered={[r.ok for r in delivered]}")
    print(f"  target_text={got!r} expected={EXPECTED!r}")
    print(f"  keyboard_text_display={keyboard_text!r}")
    print(f"  PASS={passed}")

    keyboard.close()
    target.close()
    QTimer.singleShot(0, app.quit)
    app.exec()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
