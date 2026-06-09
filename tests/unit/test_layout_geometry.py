"""Layout geometry and calibration-target alignment tests (FR-024)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtWidgets import QPushButton, QWidget

from gazekey.calibration2.targets import keyboard_geometry_targets
from gazekey.layout.geometry_check import format_geometry_report, verify_keyboard_geometry
from gazekey.layout.layout_inspector import inspect_keyboard_layout
from gazekey.typing.gaze_ui_mapper import letter_keys_region_rect
from gazekey.evaluation.benchmark_runner import predict_key_at
from gazekey.typing.key_hit_tester import (
    GAZE_HIT_OBJECT_NAMES,
    KEY_OBJECT_NAME,
    KeyHitTester,
    hit_test_layout_keys,
)


def _make_key_button(parent: QWidget, label: str, x: int, y: int) -> QPushButton:
    btn = QPushButton(label, parent)
    btn.setObjectName(KEY_OBJECT_NAME)
    btn.setGeometry(x, y, 60, 40)
    btn.show()
    return btn


def _build_test_keyboard(qapp) -> QWidget:
    root = QWidget()
    root.setGeometry(0, 0, 800, 400)
    # Row 0
    _make_key_button(root, "Q", 50, 50)
    _make_key_button(root, "W", 120, 50)
    _make_key_button(root, "E", 190, 50)
    _make_key_button(root, "T", 260, 50)
    _make_key_button(root, "Y", 330, 50)
    _make_key_button(root, "U", 400, 50)
    _make_key_button(root, "I", 470, 50)
    _make_key_button(root, "O", 540, 50)
    _make_key_button(root, "P", 610, 50)
    # Row 1
    _make_key_button(root, "A", 80, 110)
    _make_key_button(root, "S", 150, 110)
    _make_key_button(root, "D", 220, 110)
    _make_key_button(root, "G", 290, 110)
    _make_key_button(root, "H", 360, 110)
    _make_key_button(root, "J", 430, 110)
    _make_key_button(root, "K", 500, 110)
    _make_key_button(root, "L", 570, 110)
    # Row 2
    _make_key_button(root, "Z", 110, 170)
    _make_key_button(root, "X", 180, 170)
    _make_key_button(root, "C", 250, 170)
    _make_key_button(root, "V", 320, 170)
    _make_key_button(root, "B", 390, 170)
    _make_key_button(root, "N", 460, 170)
    _make_key_button(root, "M", 530, 170)
    _make_key_button(root, "Space", 200, 240)
    root.show()
    qapp.processEvents()
    return root


def test_layout_inspector_matches_key_hit_tester(qapp, tmp_path):
    root = _build_test_keyboard(qapp)
    layout_keys, mismatches = verify_keyboard_geometry(root)
    assert layout_keys, "expected keys from test keyboard"
    assert not mismatches, format_geometry_report(layout_keys, mismatches)

    report = format_geometry_report(layout_keys, mismatches)
    runs_dir = Path(__file__).resolve().parents[2] / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "geometry_check.txt").write_text(report, encoding="utf-8")


def test_benchmark_hit_test_matches_key_hit_tester(qapp):
    root = _build_test_keyboard(qapp)
    layout_keys = inspect_keyboard_layout(root)
    tester = KeyHitTester(root)
    tester.refresh()
    btn_by_id = {id(r.button): r for r in layout_keys}
    for k in layout_keys:
        cx, cy = k.center
        idx = hit_test_layout_keys(layout_keys, cx, cy)
        assert idx is not None
        predicted = predict_key_at(cx, cy, layout_keys)
        assert predicted.key_id == layout_keys[idx].key_id
        btn = tester.hit_test(cx, cy)
        assert btn is not None
        assert id(btn) == id(btn_by_id[id(btn)].button)


def test_calibration_targets_use_layout_snapshot(qapp):
    root = _build_test_keyboard(qapp)
    layout_keys = inspect_keyboard_layout(root)
    region = letter_keys_region_rect(root)
    targets = keyboard_geometry_targets(
        keys=layout_keys,
        typing_region_rect=region,
        mode="keyboard15",
    )
    assert len(targets) == 15
    by_key_id = {k.key_id: k for k in layout_keys}
    keyed_targets = [t for t in targets if t.key_id]
    assert keyed_targets, "keyboard15 should anchor targets to key centers"
    for t in keyed_targets:
        assert t.key_id in by_key_id
        key = by_key_id[t.key_id]
        assert t.screen_x == pytest.approx(key.center[0])
        assert t.screen_y == pytest.approx(key.center[1])
