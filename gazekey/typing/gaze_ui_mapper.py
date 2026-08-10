"""Map calibrated gaze ratios to on-screen typing UI coordinates."""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

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

    1. Use the saved calibration mapper (PCA4 ridge) to get screen-space gaze.
    2. Stretch that position from the calibration screen bounds onto the
       typing region: control bar + full keyboard (all rows).

    NOTE (003 audit): product typing currently uses PCA4 screen prediction +
    ``hit_test_layout_keys`` directly and does **not** call this helper.
    Kept for potential tools/legacy use; do not remove without a dedicated cleanup.
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


def typing_region_from_layout_keys(keys: Sequence) -> QRect:
    """
    Global axis-aligned union of exported product gaze-target rects.

    Includes fixed suggestion slots (even when blank/disabled), letter/editing
    keys, and bottom-row Recalibrate / Space / Enter — the full interactive
    gaze-typing surface for layout metadata (FR-011 geometry consistency).

    Does **not** change PCA4 predict or hit-test math; product typing still
    hit-tests absolute mapped screen points against per-key rects.
    """
    rects = [getattr(k, "rect", None) for k in keys]
    rects = [r for r in rects if isinstance(r, QRect) and r.isValid() and not r.isEmpty()]
    if not rects:
        return QRect()
    region = QRect(rects[0])
    for r in rects[1:]:
        region = region.united(r)
    return region


def typing_region_rect(
    keyboard_widget: QWidget,
    calibrate_button: QPushButton,
    *,
    suggestion_bar_widget: QWidget | None = None,
    layout_keys: Sequence | None = None,
) -> QRect:
    """
    Global rect for the product gaze-typing surface (layout export metadata).

    Preferred: pass ``layout_keys`` from ``inspect_keyboard_layout`` so the
    region is the union of exported gaze targets (suggestions + keys +
    Recalibrate), stable even when suggestion slots are disabled.

    Fallback (no keys): union of ``suggestion_bar_widget`` (if given) and
    ``keyboard_widget`` global bounds. ``calibrate_button`` is unused when
    Calibrate lives inside ``keyboard_widget`` (FR-008d).
    """
    del calibrate_button
    if layout_keys is not None:
        return typing_region_from_layout_keys(layout_keys)

    kb_tl = keyboard_widget.mapToGlobal(QPoint(0, 0))
    region = QRect(kb_tl, keyboard_widget.size())
    if suggestion_bar_widget is not None and suggestion_bar_widget.isVisible():
        sug_tl = suggestion_bar_widget.mapToGlobal(QPoint(0, 0))
        region = region.united(QRect(sug_tl, suggestion_bar_widget.size()))
    return region


def letter_keys_region_rect(keyboard_widget: QWidget) -> QRect:
    """Global rect over the letter/editing keyboard widget only.

    Used by calibration target placement helpers. Excludes the separate
    suggestion-bar widget (and top chrome). Does not define live hit-test.
    """
    kb_tl = keyboard_widget.mapToGlobal(QPoint(0, 0))
    return QRect(
        int(kb_tl.x()),
        int(kb_tl.y()),
        int(keyboard_widget.width()),
        int(keyboard_widget.height()),
    )
