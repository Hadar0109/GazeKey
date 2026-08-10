"""Layout-region helpers for typing UI geometry metadata and calibration bounds."""

from __future__ import annotations

from typing import Sequence

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QPushButton, QWidget


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
