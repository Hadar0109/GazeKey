"""Tests for dense keyboard-aligned calibration targets."""

from PySide6.QtCore import QRect

from gazekey.calibration.targets import keyboard_geometry_targets
from gazekey.layout.layout_inspector import KeyGeometryRow


def _fake_key(
    key_id: str,
    row: int,
    col: int,
    cx: float,
    cy: float,
    *,
    key_action: str | None = None,
    is_special: bool = False,
) -> KeyGeometryRow:
    from unittest.mock import MagicMock

    action = key_action if key_action is not None else key_id[-1]
    rect = QRect(int(cx - 30), int(cy - 20), 60, 40)
    return KeyGeometryRow(
        key_id=key_id,
        key_label=action if action != " " else "Space",
        key_action=action,
        row_index=row,
        col_index=col,
        button=MagicMock(),
        rect=rect,
        center=(cx, cy),
        hitbox=rect,
        is_special_key=is_special,
        weight=1.0,
    )


def _qwerty_like_keys() -> list[KeyGeometryRow]:
    keys: list[KeyGeometryRow] = []
    for i, ch in enumerate("QWERTYUIOP"):
        keys.append(_fake_key(f"r0c{i}:{ch.lower()}", 0, i, 69.0 + i * 126.0, 169.0, key_action=ch))
    for i, ch in enumerate("ASDFGHJKL"):
        keys.append(_fake_key(f"r1c{i}:{ch.lower()}", 1, i, 176.0 + i * 115.0, 237.0, key_action=ch))
    for i, ch in enumerate("ZXCVBNM"):
        keys.append(_fake_key(f"r2c{i}:{ch.lower()}", 2, i + 1, 292.0 + i * 116.0, 305.0, key_action=ch))
    keys.append(
        _fake_key("r3c2:space", 3, 2, 641.0, 373.0, key_action=" ", is_special=True)
    )
    return keys


def test_keyboard15_target_count_and_real_key_actions():
    keys = _qwerty_like_keys()
    region = QRect(8, 135, 1264, 273)
    targets = keyboard_geometry_targets(keys=keys, typing_region_rect=region, mode="keyboard15")
    assert len(targets) == 15
    assert all(t.key_id for t in targets)
    assert [t.label for t in targets] == [
        "key_q",
        "key_e",
        "key_t",
        "key_u",
        "key_p",
        "key_a",
        "key_d",
        "key_g",
        "key_j",
        "key_l",
        "key_z",
        "key_c",
        "key_b",
        "key_m",
        "key_space",
    ]
    assert all(t.screen_x >= region.x() for t in targets)


def test_keyboard15_gap_preserves_legacy_layout():
    keys = _qwerty_like_keys()
    region = QRect(8, 135, 1264, 273)
    targets = keyboard_geometry_targets(keys=keys, typing_region_rect=region, mode="keyboard15_gap")
    assert len(targets) == 15
    assert any(t.label.startswith("gap_") for t in targets)
    assert sum(1 for t in targets if not t.key_id) >= 2


def test_keyboard13_target_count():
    keys = []
    for row in range(1, 4):
        for col, x in enumerate((100.0, 300.0, 500.0)):
            keys.append(_fake_key(f"r{row}c{col}", row, col, x, 100.0 + row * 70))
    region = QRect(0, 80, 600, 280)
    targets = keyboard_geometry_targets(keys=keys, typing_region_rect=region, mode="keyboard13")
    assert len(targets) == 13
