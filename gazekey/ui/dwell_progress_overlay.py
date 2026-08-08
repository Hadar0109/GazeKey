"""Semi-transparent circular dwell progress ring over a key (existing geometry)."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QPoint, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QWidget


class DwellProgressOverlay(QWidget):
    """
    Transparent overlay that draws a progress arc centered on the gaze key.

    Does not change keyboard layout, size, or position — paint-only feedback.
    """

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        self._progress = 0.0
        self._local_center: Optional[QPoint] = None
        self._radius = 0.0
        self.hide()

    def clear(self) -> None:
        self._progress = 0.0
        self._local_center = None
        self._radius = 0.0
        self.hide()
        self.update()

    def show_on_button(self, button: Optional[QPushButton], progress: float) -> None:
        """Show/update ring on ``button`` with ``progress`` in [0, 1]."""
        if button is None or progress <= 0.0:
            self.clear()
            return

        parent = self.parentWidget()
        if parent is None:
            self.clear()
            return

        self.setGeometry(parent.rect())
        top_left = button.mapTo(parent, QPoint(0, 0))
        br = button.rect()
        center = QPoint(top_left.x() + br.width() // 2, top_left.y() + br.height() // 2)
        radius = max(8.0, min(br.width(), br.height()) * 0.42)

        self._local_center = center
        self._radius = float(radius)
        self._progress = max(0.0, min(1.0, float(progress)))
        self.show()
        self.raise_()
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        del event
        if self._local_center is None or self._progress <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = float(self._local_center.x())
        cy = float(self._local_center.y())
        r = self._radius
        rect = QRectF(cx - r, cy - r, r * 2.0, r * 2.0)

        track = QPen(QColor(255, 255, 255, 55), 3.0)
        track.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(track)
        painter.drawEllipse(rect)

        fill = QPen(QColor(16, 185, 129, 200), 3.5)
        fill.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fill)
        # Qt angles: 16ths of a degree; 0° at 3 o'clock; span counterclockwise.
        start = 90 * 16
        span = int(-360 * 16 * self._progress)
        painter.drawArc(rect, start, span)
        painter.end()
