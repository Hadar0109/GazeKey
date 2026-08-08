"""Read-only gaze preview dot overlay (FR-008, SC-007)."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget


class GazePreviewDot(QWidget):
    """Transparent overlay drawing smoothed (and optional raw) gaze position."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._pos: Optional[Tuple[int, int]] = None
        self._raw_pos: Optional[Tuple[int, int]] = None
        self._row_rect: Optional[QRect] = None
        self._label = ""

    def set_pos(self, x: int, y: int, *, raw: Tuple[int, int] | None = None) -> None:
        self._pos = (int(x), int(y))
        self._raw_pos = raw
        self.update()

    def clear_state(self) -> None:
        self._pos = None
        self._raw_pos = None
        self._row_rect = None
        self._label = ""
        self.update()

    def set_row_rect_and_label(self, row_rect: QRect | None, label: str) -> None:
        self._row_rect = row_rect
        self._label = str(label or "")
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._row_rect is not None and not self._row_rect.isNull():
            painter.setPen(QPen(QColor(16, 185, 129, 160), 3))
            painter.setBrush(QBrush(QColor(16, 185, 129, 35)))
            painter.drawRoundedRect(self._row_rect, 10, 10)

        if self._raw_pos is not None:
            rx, ry = self._raw_pos
            rr = 8
            painter.setPen(QPen(QColor(255, 200, 80, 220), 2))
            painter.setBrush(QBrush(QColor(255, 180, 60, 160)))
            painter.drawEllipse(int(rx - rr), int(ry - rr), int(rr * 2), int(rr * 2))

        if self._pos is not None:
            x, y = self._pos
            r = 10
            painter.setPen(QPen(QColor(255, 255, 255, 220), 2))
            painter.setBrush(QBrush(QColor(16, 185, 129, 210)))
            painter.drawEllipse(int(x - r), int(y - r), int(r * 2), int(r * 2))

        if self._label:
            painter.setPen(QPen(QColor(255, 255, 255, 230), 1))
            painter.setBrush(QBrush(QColor(0, 0, 0, 140)))
            x0, y0 = 10, 10
            w, h = 360, 32
            painter.drawRoundedRect(x0, y0, w, h, 10, 10)
            painter.drawText(QRect(x0 + 10, y0 + 6, w - 20, h - 12), Qt.AlignmentFlag.AlignLeft, self._label)
        painter.end()


class GazePreviewController:
    """Manage read-only gaze dot on the keyboard widget."""

    def __init__(self, keyboard_widget: QWidget) -> None:
        self._keyboard = keyboard_widget
        self._dot: GazePreviewDot | None = None

    def ensure_dot(self) -> GazePreviewDot:
        if self._dot is None:
            self._dot = GazePreviewDot(self._keyboard)
            self._dot.setGeometry(self._keyboard.rect())
            self._dot.raise_()
        return self._dot

    def hide(self) -> None:
        if self._dot is not None:
            self._dot.hide()

    def clear_gaze(self) -> None:
        """Reset dot state (e.g. after benchmark); does not destroy the overlay."""
        if self._dot is not None:
            self._dot.clear_state()

    def resize_to_keyboard(self) -> None:
        if self._dot is not None:
            self._dot.setGeometry(self._keyboard.rect())

    def show_gaze(
        self,
        screen_x: float,
        screen_y: float,
        *,
        label: str = "",
        raw_global: Tuple[float, float] | None = None,
        show_raw: bool = False,
    ) -> None:
        """Show one mapped gaze dot; optional second raw dot only when ``show_raw``."""
        dot = self.ensure_dot()
        local = self._keyboard.mapFromGlobal(QPoint(int(screen_x), int(screen_y)))
        raw_local = None
        if show_raw and raw_global is not None:
            pr = self._keyboard.mapFromGlobal(
                QPoint(int(raw_global[0]), int(raw_global[1]))
            )
            raw_local = (pr.x(), pr.y())
        dot.set_row_rect_and_label(None, str(label or ""))
        dot.set_pos(local.x(), local.y(), raw=raw_local)
        dot.show()
        dot.raise_()
