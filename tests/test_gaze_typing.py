"""Unit tests for gaze typing logic."""

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QLineEdit

from gazekey.typing.dwell_selector import DwellSelector
from gazekey.typing.gaze_smoother import GazeSmoother
from gazekey.typing.key_hit_tester import hit_test_rects
from gazekey.typing.key_semantics import action_from_label
from gazekey.typing.text_buffer import TextBufferController


def test_action_from_label_special_keys():
    assert action_from_label("⌫") == "BACKSPACE"
    assert action_from_label("Space") == " "
    assert action_from_label("↵") == "ENTER"
    assert action_from_label("&&") == "&"
    assert action_from_label("Shift") == "SHIFT"


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


def test_dwell_progress_reaches_one():
    dwell = DwellSelector(dwell_duration_sec=1.0, global_cooldown_sec=0.0)
    dt = 0.1
    activated = False
    for _ in range(11):
        state = dwell.update(42, dt)
        if state.should_activate:
            activated = True
        assert state.progress <= 1.0
    assert activated is True


def test_dwell_fires_once_until_leave_and_return():
    dwell = DwellSelector(
        dwell_duration_sec=0.5,
        global_cooldown_sec=1.0,
    )
    dt = 0.05
    fired = 0
    for _ in range(12):
        state = dwell.update(7, dt)
        if state.should_activate:
            fired += 1
    assert fired == 1

    for _ in range(5):
        dwell.update(7, dt)
    assert fired == 1

    dwell.update(99, dt)
    for _ in range(25):
        dwell.update(None, dt)
    for _ in range(12):
        state = dwell.update(7, dt)
        if state.should_activate:
            fired += 1
    assert fired == 2


def test_global_cooldown_blocks_rapid_refire():
    dwell = DwellSelector(
        dwell_duration_sec=0.2,
        global_cooldown_sec=0.5,
    )
    dt = 0.05
    activated = False
    for _ in range(8):
        state = dwell.update(1, dt)
        if state.should_activate:
            activated = True
    assert activated is True

    dwell.update(2, dt)
    fired_during_cooldown = False
    for _ in range(6):
        state = dwell.update(2, dt)
        if state.should_activate:
            fired_during_cooldown = True
    assert fired_during_cooldown is False


def test_dwell_survives_brief_miss():
    dwell = DwellSelector(
        dwell_duration_sec=1.0,
        global_cooldown_sec=0.0,
        miss_frames_to_reset=5,
    )
    dt = 0.033
    for _ in range(25):
        dwell.update(5, dt)
    for _ in range(3):
        state = dwell.update(None, dt)
        assert state.progress > 0.0
    activated = False
    for _ in range(18):
        state = dwell.update(5, dt)
        if state.should_activate:
            activated = True
    assert activated is True


def test_gaze_smoother_reduces_jitter():
    smooth = GazeSmoother(alpha=0.5)
    x1, y1 = smooth.filter(100.0, 200.0)
    x2, y2 = smooth.filter(110.0, 190.0)
    assert x1 == 100.0
    assert 100.0 < x2 < 110.0
    assert 190.0 < y2 < 200.0


def test_text_buffer_letters_and_shift(qapp):
    line = QLineEdit()
    buf = TextBufferController(line)
    buf.apply_key("a", shift_active=False)
    assert line.text() == "a"
    buf.apply_key("b", shift_active=True)
    assert line.text() == "aB"


def test_text_buffer_space_backspace_enter(qapp):
    line = QLineEdit()
    buf = TextBufferController(line)
    for ch in "hi":
        buf.apply_key(ch)
    buf.apply_key(" ")
    assert line.text() == "hi "
    buf.apply_key("BACKSPACE")
    assert line.text() == "hi"
    buf.apply_key("ENTER")
    assert "\n" in line.text()


def test_text_buffer_ignores_ctrl_alt_shift(qapp):
    line = QLineEdit()
    buf = TextBufferController(line)
    buf.apply_key("CTRL")
    buf.apply_key("ALT")
    buf.apply_key("SHIFT")
    assert line.text() == ""
