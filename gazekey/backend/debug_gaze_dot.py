"""Temporary Stage C debug gaze overlay driven only by GazeSample.x/y.

Does not call GazeTypingRuntime.on_mapped_gaze, DwellEngine, or ActionDispatcher.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gazekey.backend.gaze_sample import GazeSample


class DebugGazeDot(QWidget):
    """Transparent overlay drawing official filtered gaze on the keyboard."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._pos: Optional[Tuple[int, int]] = None
        self._valid = False

    def set_local_pos(self, x: int, y: int, *, valid: bool) -> None:
        self._pos = (int(x), int(y))
        self._valid = bool(valid)
        self.update()

    def clear_state(self) -> None:
        self._pos = None
        self._valid = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        if self._pos is None or not self._valid:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x, y = self._pos
        radius = 10
        painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
        painter.setBrush(QBrush(QColor(16, 185, 129, 210)))
        painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2), int(radius * 2))
        painter.end()


class DebugGazeOverlay:
    """Developer overlay: GazeSample.x/y → keyboard-local dot."""

    def __init__(self, keyboard_widget: QWidget) -> None:
        self._keyboard = keyboard_widget
        self._dot = DebugGazeDot(keyboard_widget)
        self._dot.setGeometry(keyboard_widget.rect())
        self._dot.raise_()

    def resize_to_keyboard(self) -> None:
        self._dot.setGeometry(self._keyboard.rect())

    def update_sample(self, sample: GazeSample) -> None:
        if not sample.valid:
            self._dot.clear_state()
            return
        local = self._keyboard.mapFromGlobal(QPoint(int(sample.x), int(sample.y)))
        self._dot.set_local_pos(local.x(), local.y(), valid=True)
        self._dot.show()
        self._dot.raise_()

    def hide(self) -> None:
        self._dot.clear_state()
        self._dot.hide()
