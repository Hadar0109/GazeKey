"""Post-calibration geometry overlay (expected vs predicted gaze points)."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class CalibrationGeometryOverlay(QWidget):
    """
    Draw calibration targets, train predictions, LOOCV predictions, and error segments.

    Coordinates are global screen space; the widget covers the primary screen.
    """

    def __init__(
        self,
        *,
        expected: Sequence[Tuple[float, float]],
        train_pred: Sequence[Optional[Tuple[float, float]]],
        loocv_pred: Sequence[Optional[Tuple[float, float]]],
        labels: Sequence[str],
        parent=None,
        auto_close_ms: int = 12000,
    ) -> None:
        super().__init__(parent)
        self._expected = list(expected)
        self._train_pred = list(train_pred)
        self._loocv_pred = list(loocv_pred)
        self._labels = list(labels)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        if auto_close_ms > 0:
            QTimer.singleShot(auto_close_ms, self.close)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        origin = self.geometry().topLeft()

        def to_local(gx: float, gy: float) -> Tuple[int, int]:
            return int(gx - origin.x()), int(gy - origin.y())

        for i, (ex, ey) in enumerate(self._expected):
            lx, ly = to_local(ex, ey)
            painter.setPen(QPen(QColor(34, 197, 94, 230), 2))
            painter.setBrush(QBrush(QColor(34, 197, 94, 80)))
            painter.drawEllipse(lx - 7, ly - 7, 14, 14)

            tp = self._train_pred[i] if i < len(self._train_pred) else None
            if tp is not None:
                tx, ty = to_local(tp[0], tp[1])
                painter.setPen(QPen(QColor(59, 130, 246, 220), 2))
                painter.setBrush(QBrush(QColor(59, 130, 246, 120)))
                painter.drawEllipse(tx - 6, ty - 6, 12, 12)
                painter.drawLine(lx, ly, tx, ty)

            lp = self._loocv_pred[i] if i < len(self._loocv_pred) else None
            if lp is not None:
                ux, uy = to_local(lp[0], lp[1])
                painter.setPen(QPen(QColor(249, 115, 22, 210), 2))
                painter.setBrush(QBrush(QColor(249, 115, 22, 100)))
                painter.drawEllipse(ux - 5, uy - 5, 10, 10)
                painter.drawLine(lx, ly, ux, uy)

            if i < len(self._labels):
                painter.setPen(QPen(QColor(255, 255, 255, 200)))
                painter.drawText(lx + 10, ly - 10, self._labels[i])

        # Legend
        painter.setPen(QPen(QColor(255, 255, 255, 220)))
        painter.drawText(20, 30, "Green=target  Blue=train  Orange=LOOCV  lines=error")
        painter.end()
