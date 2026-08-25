"""Inspect Qt keyboard widgets and derive geometry for gaze targeting.

Design goals:
- No hardcoded screen sizes.
- Deterministic ordering and IDs (stable within a given layout snapshot).
- Provide both tight rects and enlarged hitboxes for intent estimation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QPushButton, QWidget

from gazekey.typing.key_hit_tester import GAZE_HIT_OBJECT_NAMES
from gazekey.typing.key_semantics import action_from_label


@dataclass(frozen=True)
class KeyGeometryRow:
    key_id: str
    key_label: str
    key_action: str
    row_index: int
    col_index: int
    button: QPushButton
    rect: QRect
    center: Tuple[float, float]
    hitbox: QRect
    is_special_key: bool
    weight: float


def _button_global_rect(btn: QPushButton) -> QRect:
    tl = btn.mapToGlobal(QPoint(0, 0))
    return QRect(tl, btn.size())


def _cluster_rows(
    rects: Sequence[QRect],
    y_tol_px: float,
) -> List[int]:
    """
    Assign a row index to each rect (same order as rects).

    We cluster by vertical center coordinate with a tolerance so different key
    heights still fall into the right row.
    """
    centers_y = [r.center().y() for r in rects]
    order = sorted(range(len(rects)), key=lambda i: centers_y[i])
    row_for = [-1] * len(rects)

    current_row = -1
    last_y: Optional[float] = None
    for idx in order:
        y = float(centers_y[idx])
        if last_y is None or abs(y - last_y) > y_tol_px:
            current_row += 1
            last_y = y
        row_for[idx] = current_row
    return row_for


def _enlarged_hitbox(rect: QRect, margin_px: int) -> QRect:
    return rect.adjusted(-margin_px, -margin_px, margin_px, margin_px)


def inspect_keyboard_layout(
    root: QWidget,
    *,
    hitbox_margin_px: int = 6,
    special_key_weight: float = 1.25,
    normal_key_weight: float = 1.0,
) -> List[KeyGeometryRow]:
    """
    Snapshot key geometry for all gaze-hit-testable buttons under root.

    Returns rows sorted by (row_index, col_index).
    """
    buttons = list(root.findChildren(QPushButton))
    candidates: List[QPushButton] = []
    for btn in buttons:
        if btn.objectName() not in GAZE_HIT_OBJECT_NAMES:
            continue
        if not btn.isVisible():
            continue
        # Export disabled suggestion slots (fixed geometry); hit-test skips them.
        candidates.append(btn)

    rects = [_button_global_rect(b) for b in candidates]
    if not rects:
        return []

    # Robust-ish tolerance: roughly half median key height.
    heights = sorted([r.height() for r in rects if r.height() > 0])
    median_h = float(heights[len(heights) // 2]) if heights else 40.0
    y_tol_px = max(8.0, median_h * 0.6)
    row_idxs = _cluster_rows(rects, y_tol_px=y_tol_px)

    # Within each row, order by x-center.
    indices = list(range(len(candidates)))
    indices.sort(key=lambda i: (row_idxs[i], rects[i].center().x()))

    # Compute col indices per row after sorting.
    col_idx_map: dict[int, int] = {}
    rows: List[KeyGeometryRow] = []
    for i in indices:
        row_i = int(row_idxs[i])
        col_i = col_idx_map.get(row_i, 0)
        col_idx_map[row_i] = col_i + 1

        btn = candidates[i]
        rect = rects[i]
        center = (float(rect.center().x()), float(rect.center().y()))

        label = btn.text()
        # Optional stable overrides (suggestion:N, system:calibrate,
        # system:page_right / system:page_left). `system:` actions are special.
        override_id = btn.property("gazeKeyId")
        override_action = btn.property("gazeKeyAction")
        if override_action:
            action = str(override_action)
        else:
            action = action_from_label(label)
        is_special = (
            action in {"BACKSPACE", "ENTER", "SHIFT", "CTRL", "ALT", " ", "PAUSE_RESUME", "CALIBRATE"}
            or str(action).startswith("suggestion:")
            or str(action).startswith("system:")
            or len(action) != 1
        )
        weight = float(special_key_weight if is_special else normal_key_weight)

        hitbox = _enlarged_hitbox(rect, margin_px=int(hitbox_margin_px))

        # Stable within a layout snapshot: override or semantic action + row/col.
        if override_id:
            key_id = str(override_id)
        else:
            key_id = f"r{row_i:02d}c{col_i:02d}:{action}"

        rows.append(
            KeyGeometryRow(
                key_id=key_id,
                key_label=label,
                key_action=action,
                row_index=row_i,
                col_index=col_i,
                button=btn,
                rect=rect,
                center=center,
                hitbox=hitbox,
                is_special_key=is_special,
                weight=weight,
            )
        )

    rows.sort(key=lambda r: (r.row_index, r.col_index))
    return rows

