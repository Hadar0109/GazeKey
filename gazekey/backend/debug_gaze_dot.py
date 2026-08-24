"""Temporary Stage C debug overlay: official-style GREEN ring.

Step B reads gf.get_gaze_info() filtered xy after the approved transform.
Hold-last is visualization-only. Does not call GazeTypingRuntime.on_mapped_gaze,
DwellEngine, or ActionDispatcher. Does not change GazeSample.valid.
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
OFFICIAL_RING_COLOR = QColor(0, 255, 0)


def overlay_ring_metrics(dpr: float) -> tuple[float, float]:
    """Map official GF-pixel ring size into current overlay (logical) pixels."""
    scale = float(dpr) if dpr and float(dpr) > 0 else 1.0
    return OFFICIAL_RING_RADIUS_GF_PX / scale, OFFICIAL_RING_STROKE_GF_PX / scale


class DebugGazeDot(QWidget):
    """Transparent overlay drawing official filtered gaze as a GREEN ring."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        radius: float = OFFICIAL_RING_RADIUS_GF_PX,
        stroke: float = OFFICIAL_RING_STROKE_GF_PX,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._pos: Optional[Tuple[int, int]] = None
        self._radius = float(radius)
        self._stroke = max(1.0, float(stroke))

    def set_local_pos(self, x: int, y: int) -> None:
        self._pos = (int(x), int(y))
        self.update()

    def clear_state(self) -> None:
        self._pos = None
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        if self._pos is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        x, y = self._pos
        radius = self._radius
        painter.setPen(QPen(OFFICIAL_RING_COLOR, self._stroke))
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.drawEllipse(
            int(round(x - radius)),
            int(round(y - radius)),
            int(round(radius * 2)),
            int(round(radius * 2)),
        )
        painter.end()


class DebugGazeOverlay:
    """Developer overlay: GazeSample.x/y after the approved transform. Hold-last viz only."""

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
        """Place the ring at Qt-global xy. Hold-last is the caller's job when skipped."""
        local = self._keyboard.mapFromGlobal(QPoint(int(x), int(y)))
        self._dot.set_local_pos(local.x(), local.y())
        self._dot.show()
        self._dot.raise_()

    def hide(self) -> None:
        self._dot.clear_state()
        self._dot.hide()
