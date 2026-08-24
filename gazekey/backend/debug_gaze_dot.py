"""Temporary Stage C debug overlay: GREEN official-style origin+dpr ring.

Hold-last is visualization-only. Does not call GazeTypingRuntime.on_mapped_gaze,
DwellEngine, or ActionDispatcher. Does not change GazeSample.valid or the
production transform.
"""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from gazekey.backend.gaze_sample import GazeSample

# pygame_example.py: pygame.draw.circle(win, (0, 255, 0), (gx, gy), 50, 5)
OFFICIAL_RING_RADIUS_GF_PX = 50.0
OFFICIAL_RING_STROKE_GF_PX = 5.0
ORIGIN_DPR_RING_COLOR = QColor(0, 255, 0)


def overlay_ring_metrics(dpr: float) -> tuple[float, float]:
    """Map official GF-pixel ring size into current overlay (logical) pixels."""
    scale = float(dpr) if dpr and float(dpr) > 0 else 1.0
    return OFFICIAL_RING_RADIUS_GF_PX / scale, OFFICIAL_RING_STROKE_GF_PX / scale


class DebugGazeDot(QWidget):
    """GREEN origin+dpr official-style ring."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        radius: float = OFFICIAL_RING_RADIUS_GF_PX,
        stroke: float = OFFICIAL_RING_STROKE_GF_PX,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._dpr_pos: Optional[Tuple[int, int]] = None
        self._radius = float(radius)
        self._stroke = max(1.0, float(stroke))

    def set_pos(self, pos: Tuple[int, int] | None) -> None:
        if pos is not None:
            self._dpr_pos = (int(pos[0]), int(pos[1]))
        self.update()

    def clear_state(self) -> None:
        self._dpr_pos = None
        self.update()

    def _draw_ring(self, painter: QPainter, pos: Tuple[int, int], color: QColor) -> None:
        x, y = pos
        radius = self._radius
        painter.setPen(QPen(color, self._stroke))
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawEllipse(
            int(round(x - radius)),
            int(round(y - radius)),
            int(round(radius * 2)),
            int(round(radius * 2)),
        )

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        if self._dpr_pos is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_ring(painter, self._dpr_pos, ORIGIN_DPR_RING_COLOR)
        painter.end()


class DebugGazeOverlay:
    """GREEN origin+dpr ring from official filtered gaze. Hold-last viz only."""

    def __init__(self, parent: QWidget, *, dpr: float = 1.0) -> None:
        self._keyboard = parent
        radius, stroke = overlay_ring_metrics(dpr)
        self._dot = DebugGazeDot(parent, radius=radius, stroke=stroke)
        self._dot.setGeometry(parent.rect())
        self._dot.raise_()

    def resize_to_keyboard(self) -> None:
        self._dot.setGeometry(self._keyboard.rect())

    def update_sample(self, sample: GazeSample) -> None:
        if not sample.valid:
            return
        self.update_xy(sample.x, sample.y)

    def update_xy(self, x: float, y: float) -> None:
        local = self._keyboard.mapFromGlobal(QPoint(int(x), int(y)))
        self._dot.set_pos((local.x(), local.y()))
        self._dot.show()
        self._dot.raise_()

    def hide(self) -> None:
        self._dot.clear_state()
        self._dot.hide()
