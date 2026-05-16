"""Hit-test screen gaze points against keyboard key geometry."""

import math
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QPushButton, QWidget

KEY_OBJECT_NAME = "keyboardKey"
HIT_MARGIN_PX = 18
SNAP_DISTANCE_PX = 72


@dataclass
class KeyRegion:
    button: QPushButton
    global_rect: QRect

    @property
    def key_id(self) -> int:
        return id(self.button)


class KeyHitTester:
    """Collect keyboard key global rects and hit-test gaze points."""

    def __init__(
        self,
        root: QWidget,
        hit_margin_px: int = HIT_MARGIN_PX,
        snap_distance_px: float = SNAP_DISTANCE_PX,
    ) -> None:
        self._root = root
        self._hit_margin = hit_margin_px
        self._snap_distance = snap_distance_px
        self._regions: List[KeyRegion] = []

    def refresh(self) -> None:
        buttons = self._root.findChildren(QPushButton)
        self._regions = []
        for btn in buttons:
            if btn.objectName() != KEY_OBJECT_NAME:
                continue
            if not btn.isVisible():
                continue
            top_left = btn.mapToGlobal(QPoint(0, 0))
            rect = QRect(top_left, btn.size())
            rect = rect.adjusted(
                -self._hit_margin,
                -self._hit_margin,
                self._hit_margin,
                self._hit_margin,
            )
            self._regions.append(KeyRegion(button=btn, global_rect=rect))

    def hit_test(self, screen_x: float, screen_y: float) -> Optional[QPushButton]:
        point = QPoint(int(screen_x), int(screen_y))

        containing: List[KeyRegion] = []
        for region in self._regions:
            if region.global_rect.contains(point):
                containing.append(region)

        if containing:
            if len(containing) == 1:
                return containing[0].button
            containing.sort(key=lambda r: r.global_rect.width() * r.global_rect.height())
            return containing[0].button

        best: Optional[KeyRegion] = None
        best_dist = float("inf")
        for region in self._regions:
            center = region.global_rect.center()
            dist = math.hypot(screen_x - center.x(), screen_y - center.y())
            if dist < best_dist:
                best_dist = dist
                best = region

        if best is not None and best_dist <= self._snap_distance:
            return best.button
        return None

    @property
    def regions(self) -> List[KeyRegion]:
        return list(self._regions)


def hit_test_rects(
    regions: List[tuple[int, QRect]],
    screen_x: float,
    screen_y: float,
    snap_distance: float = SNAP_DISTANCE_PX,
) -> Optional[int]:
    """Pure hit-test over (id, rect) pairs; smallest containing rect wins."""
    point = QPoint(int(screen_x), int(screen_y))
    containing = [(kid, rect) for kid, rect in regions if rect.contains(point)]
    if containing:
        containing.sort(key=lambda item: item[1].width() * item[1].height())
        return containing[0][0]

    best_id: Optional[int] = None
    best_dist = float("inf")
    for key_id, rect in regions:
        center = rect.center()
        dist = math.hypot(screen_x - center.x(), screen_y - center.y())
        if dist < best_dist:
            best_dist = dist
            best_id = key_id
    if best_id is not None and best_dist <= snap_distance:
        return best_id
    return None
