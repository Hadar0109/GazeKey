"""T032 Iteration 4: candidate calibration layouts (keyboard_full9, keyboard_wide9).

These verify anchor placement/count and that the 3-band row grouping stays intact, so the
row-Y bias 3-row assumption is not corrupted by the new full-keyboard / wide layouts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from PySide6.QtCore import QRect

from gazekey.calibration2.targets import (
    calibration_row_groups,
    keyboard_geometry_targets,
)


@dataclass(frozen=True)
class FakeKey:
    """Duck-typed stand-in for KeyGeometryRow (no Qt widgets needed)."""

    key_id: str
    key_label: str
    key_action: str
    row_index: int
    center: Tuple[float, float]
    is_special_key: bool = False


def _fake_keyboard() -> list[FakeKey]:
    keys: list[FakeKey] = []
    # Row 0: Q..P letters (y=169)
    for i, ch in enumerate("QWERTYUIOP"):
        x = 69.0 + i * 126.0
        keys.append(FakeKey(f"r00c{i:02d}:{ch.lower()}", ch, ch.lower(), 0, (x, 169.0)))
    # Row 1: A..L letters (y=237)
    for i, ch in enumerate("ASDFGHJKL"):
        x = 176.0 + i * 115.0
        keys.append(FakeKey(f"r01c{i:02d}:{ch.lower()}", ch, ch.lower(), 1, (x, 237.0)))
    # Row 2: Shift, Z..M, Backspace (y=305) -- specials at the true left/right edges
    keys.append(FakeKey("r02c00:SHIFT", "Shift", "SHIFT", 2, (40.0, 305.0), True))
    for i, ch in enumerate("ZXCVBNM"):
        x = 292.0 + i * 116.0
        keys.append(FakeKey(f"r02c{i+1:02d}:{ch.lower()}", ch, ch.lower(), 2, (x, 305.0)))
    keys.append(FakeKey("r02c08:BACKSPACE", "\u232b", "BACKSPACE", 2, (1240.0, 305.0), True))
    # Row 3: Ctrl, Alt, Space, Enter (y=373)
    keys.append(FakeKey("r03c00:CTRL", "Ctrl", "CTRL", 3, (60.0, 373.0), True))
    keys.append(FakeKey("r03c01:ALT", "Alt", "ALT", 3, (200.0, 373.0), True))
    keys.append(FakeKey("r03c02:SPACE", "Space", " ", 3, (641.0, 373.0), True))
    keys.append(FakeKey("r03c03:ENTER", "\u21b5", "ENTER", 3, (1200.0, 373.0), True))
    return keys


def _kb_rect() -> QRect:
    # x, y, w, h roughly matching the diagnostics calibration box span
    return QRect(8, 135, 1264, 273)


def _screen_rect() -> QRect:
    return QRect(0, 0, 1280, 800)


def test_keyboard_full9_produces_nine_anchors_spanning_full_keyboard():
    keys = _fake_keyboard()
    targets = keyboard_geometry_targets(
        keys=keys,
        typing_region_rect=_kb_rect(),
        mode="keyboard_full9",
    )
    assert len(targets) == 9

    xs = [t.screen_x for t in targets]
    ys = [t.screen_y for t in targets]
    # Reaches the true left/right edges (Shift/Ctrl ~ 40/60, Backspace/Enter ~1240/1200)
    assert min(xs) <= 70.0
    assert max(xs) >= 1190.0
    # Spans top letter row down to the bottom Ctrl/Space/Enter row
    assert min(ys) == 169.0
    assert max(ys) == 373.0


def test_keyboard_full9_keeps_three_row_bands_intact():
    keys = _fake_keyboard()
    targets = keyboard_geometry_targets(
        keys=keys,
        typing_region_rect=_kb_rect(),
        mode="keyboard_full9",
    )
    top, mid, bot = calibration_row_groups(targets)
    # Row-Y bias 3-row assumption must still see three non-empty bands.
    assert len(top) == 3
    assert len(mid) == 3
    assert len(bot) == 3
    # Bands must be vertically ordered top < mid < bottom.
    y_top = targets[top[0]].screen_y
    y_mid = targets[mid[0]].screen_y
    y_bot = targets[bot[0]].screen_y
    assert y_top < y_mid < y_bot


def test_keyboard_wide9_is_wider_than_keyboard_and_clamped_to_screen():
    keys = _fake_keyboard()
    kb = _kb_rect()
    screen = _screen_rect()
    targets = keyboard_geometry_targets(
        keys=keys,
        typing_region_rect=kb,
        mode="keyboard_wide9",
        screen_rect=screen,
    )
    assert len(targets) == 9

    xs = [t.screen_x for t in targets]
    ys = [t.screen_y for t in targets]
    # Wider than the keyboard rect on at least one side (when the keyboard already spans
    # most of the screen width, horizontal is screen-clamped and the excursion is vertical).
    assert (
        min(xs) < kb.x()
        or max(xs) > kb.x() + kb.width()
        or min(ys) < kb.y()
        or max(ys) > kb.y() + kb.height()
    )
    # ...but never off-screen (clamped within the inset screen bounds).
    assert min(xs) >= screen.x()
    assert max(xs) <= screen.x() + screen.width()
    assert min(ys) >= screen.y()
    assert max(ys) <= screen.y() + screen.height()

    # Still three usable row bands for the row model.
    top, mid, bot = calibration_row_groups(targets)
    assert len(top) == 3 and len(mid) == 3 and len(bot) == 3


def test_keyboard_full9_falls_back_when_too_few_rows():
    # Only one row of keys -> cannot form three bands -> fall back to standard layout.
    keys = [
        FakeKey(f"r00c{i:02d}:{c.lower()}", c, c.lower(), 0, (69.0 + i * 126.0, 169.0))
        for i, c in enumerate("QWERTYUIOP")
    ]
    targets = keyboard_geometry_targets(
        keys=keys,
        typing_region_rect=_kb_rect(),
        mode="keyboard_full9",
    )
    # Falls back (keyboard15 over a single row still yields a valid non-empty target set).
    assert len(targets) >= 1
