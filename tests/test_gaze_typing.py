"""Unit tests for active typing utilities (hit-test, smoother).

In-app TextBufferController removed in 002 T046 — OS is the typing destination.
"""

from PySide6.QtCore import QRect

from gazekey.typing.key_hit_tester import hit_test_rects
from gazekey.typing.key_semantics import action_from_label


def test_action_from_label_special_keys():
    assert action_from_label("⌫") == "BACKSPACE"
    assert action_from_label("Space") == " "
    assert action_from_label("↵") == "ENTER"
    assert action_from_label("&&") == "&"
    assert action_from_label("Shift") == "SHIFT"
    assert action_from_label("Pause") == "PAUSE_RESUME"


def test_hit_test_no_key():
    regions = [(1, QRect(0, 0, 50, 50))]
    assert hit_test_rects(regions, 100, 100) is None


def test_hit_test_one_key():
    regions = [(1, QRect(0, 0, 50, 50))]
    assert hit_test_rects(regions, 25, 25) == 1


def test_hit_test_smallest_containing_wins():
    regions = [
        (1, QRect(0, 0, 100, 100)),
        (2, QRect(10, 10, 50, 50)),
    ]
    assert hit_test_rects(regions, 30, 30) == 2


def test_hit_test_snap_to_nearest():
    regions = [(1, QRect(0, 0, 50, 50))]
    assert hit_test_rects(regions, 60, 25, snap_distance=30) is None
    assert hit_test_rects(regions, 60, 25, snap_distance=40) == 1
