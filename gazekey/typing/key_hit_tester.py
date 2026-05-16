"""Hit-test screen gaze points against keyboard key geometry."""

import math
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QPushButton, QWidget

KEY_OBJECT_NAME = "keyboardKey"
GAZE_TARGET_OBJECT_NAME = "gazeTarget"
GAZE_HIT_OBJECT_NAMES = frozenset({KEY_OBJECT_NAME, GAZE_TARGET_OBJECT_NAME})
# Tight bounds first; modest snap for edge keys and wide targets (e.g. Space).
HIT_MARGIN_PX = 4
SNAP_DISTANCE_PX = 40


@dataclass
class KeyRegion:
    button: QPushButton
    tight_rect: QRect
    snap_rect: QRect

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
        self._dirty = True

    def mark_dirty(self) -> None:
        self._dirty = True

    def refresh(self) -> None:
        self.mark_dirty()
        self._rebuild_regions()

    def _rebuild_regions(self) -> None:
        buttons = self._root.findChildren(QPushButton)
        self._regions = []
        for btn in buttons:
            if btn.objectName() not in GAZE_HIT_OBJECT_NAMES:
                continue
            if not btn.isVisible():
                continue
            top_left = btn.mapToGlobal(QPoint(0, 0))
            tight = QRect(top_left, btn.size())
            snap = tight.adjusted(
                -self._hit_margin,
                -self._hit_margin,
                self._hit_margin,
                self._hit_margin,
            )
            self._regions.append(
                KeyRegion(button=btn, tight_rect=tight, snap_rect=snap)
            )
        self._dirty = len(self._regions) == 0

    @staticmethod
    def _distance_to_rect(screen_x: float, screen_y: float, rect: QRect) -> float:
        if rect.contains(QPoint(int(screen_x), int(screen_y))):
            return 0.0
        dx = 0.0
        if screen_x < rect.left():
            dx = rect.left() - screen_x
        elif screen_x > rect.right():
            dx = screen_x - rect.right()
        dy = 0.0
        if screen_y < rect.top():
            dy = rect.top() - screen_y
        elif screen_y > rect.bottom():
            dy = screen_y - rect.bottom()
        return math.hypot(dx, dy)

    @staticmethod
    def _distance_to_center(
        screen_x: float,
        screen_y: float,
        rect: QRect,
    ) -> float:
        center = rect.center()
        return math.hypot(screen_x - center.x(), screen_y - center.y())

    def hit_test(self, screen_x: float, screen_y: float) -> Optional[QPushButton]:
        if self._dirty or not self._regions:
            self._rebuild_regions()

        point = QPoint(int(screen_x), int(screen_y))

        containing: List[KeyRegion] = []
        for region in self._regions:
            if region.tight_rect.contains(point):
                containing.append(region)

        if containing:
            if len(containing) == 1:
                return containing[0].button
            containing.sort(
                key=lambda r: self._distance_to_center(
                    screen_x, screen_y, r.tight_rect
                )
            )
            return containing[0].button

        best: Optional[KeyRegion] = None
        best_dist = float("inf")
        second_dist = float("inf")
        for region in self._regions:
            dist = self._distance_to_rect(screen_x, screen_y, region.snap_rect)
            if dist < best_dist:
                second_dist = best_dist
                best_dist = dist
                best = region
            elif dist < second_dist:
                second_dist = dist

        if best is None or best_dist > self._snap_distance:
            return None
        if second_dist - best_dist < 4.0:
            return None
        return best.button

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
