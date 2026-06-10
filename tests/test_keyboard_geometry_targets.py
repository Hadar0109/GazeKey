"""Tests for dense keyboard-aligned calibration targets."""

from PySide6.QtCore import QRect

from gazekey.calibration.targets import keyboard_geometry_targets
from gazekey.layout.layout_inspector import KeyGeometryRow


def _fake_key(key_id: str, row: int, col: int, cx: float, cy: float) -> KeyGeometryRow:
  from PySide6.QtCore import QRect
  from unittest.mock import MagicMock

  rect = QRect(int(cx - 30), int(cy - 20), 60, 40)
  return KeyGeometryRow(
      key_id=key_id,
      key_label=key_id[-1],
      key_action=key_id[-1],
      row_index=row,
      col_index=col,
      button=MagicMock(),
      rect=rect,
      center=(cx, cy),
      hitbox=rect,
      is_special_key=False,
      weight=1.0,
  )


def test_keyboard15_target_count_and_key_ids():
    keys = []
    for row in range(1, 4):
        for col, x in enumerate((100.0, 300.0, 500.0)):
            keys.append(_fake_key(f"r{row}c{col}", row, col, x, 100.0 + row * 70))

    region = QRect(0, 80, 600, 280)
    targets = keyboard_geometry_targets(keys=keys, typing_region_rect=region, mode="keyboard15")
    assert len(targets) == 15
    assert sum(1 for t in targets if t.key_id) >= 9
    assert all(t.screen_x >= region.x() for t in targets)


def test_keyboard13_target_count():
    keys = []
    for row in range(1, 4):
        for col, x in enumerate((100.0, 300.0, 500.0)):
            keys.append(_fake_key(f"r{row}c{col}", row, col, x, 100.0 + row * 70))
    region = QRect(0, 80, 600, 280)
    targets = keyboard_geometry_targets(keys=keys, typing_region_rect=region, mode="keyboard13")
    assert len(targets) == 13
