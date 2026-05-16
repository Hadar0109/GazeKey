"""Map calibrated gaze ratios to on-screen typing UI coordinates."""

from typing import List, Optional, Tuple

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QPushButton, QWidget

# Allow gaze slightly past the bottom calibration dot to reach Space / Ctrl row.
_BOTTOM_EXTRAPOLATION = 0.15


def map_gaze_to_typing_ui(
    gaze_h: float,
    gaze_v: float,
    mapper,
    keyboard_widget: QWidget,
    calibrate_button: QPushButton,
) -> Tuple[float, float]:
    """
    Convert gaze ratios to global screen coordinates for hit-testing.

    1. Use the saved calibration mapper (IDW) to get screen-space gaze.
    2. Stretch that position from the calibration screen bounds onto the
       typing region: control bar + full keyboard (all rows).
    """
    if mapper is None:
        return 0.0, 0.0

    screen_x, screen_y = mapper.map_point(gaze_h, gaze_v)
    screen_points: Optional[List[Tuple[float, float]]] = getattr(
        mapper, "screen_points", None
    )
    if not screen_points or len(screen_points) < 5:
        return screen_x, screen_y

    xs = [float(p[0]) for p in screen_points]
    ys = [float(p[1]) for p in screen_points]
    sx0, sx1 = min(xs), max(xs)
    sy0, sy1 = min(ys), max(ys)
    if sx1 <= sx0 or sy1 <= sy0:
        return screen_x, screen_y

    kb_tl = keyboard_widget.mapToGlobal(QPoint(0, 0))
    kb_w = float(keyboard_widget.width())
    kb_h = float(keyboard_widget.height())
    if kb_w < 1.0 or kb_h < 1.0:
        return screen_x, screen_y

    bar_h = float(calibrate_button.height())
    if bar_h < 1.0:
        bar_h = 56.0

    region_x = float(kb_tl.x())
    region_y = float(kb_tl.y()) - bar_h
    region_w = kb_w
    region_h = kb_h + bar_h

    tx = (screen_x - sx0) / (sx1 - sx0)
    ty = (screen_y - sy0) / (sy1 - sy0)
    tx = max(0.0, min(1.0, tx))
    ty = max(0.0, min(1.0 + _BOTTOM_EXTRAPOLATION, ty))

    out_x = region_x + tx * region_w
    out_y = region_y + ty * region_h
    return out_x, out_y


def typing_region_rect(
    keyboard_widget: QWidget,
    calibrate_button: QPushButton,
) -> QRect:
    """Global rect covering Calibrate through the bottom keyboard row."""
    kb_tl = keyboard_widget.mapToGlobal(QPoint(0, 0))
    bar_h = float(calibrate_button.height()) or 56.0
    return QRect(
        int(kb_tl.x()),
        int(kb_tl.y() - bar_h),
        int(keyboard_widget.width()),
        int(keyboard_widget.height() + bar_h),
    )
