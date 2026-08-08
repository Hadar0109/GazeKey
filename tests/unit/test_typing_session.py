"""Unit tests for TypingSession Shift clear / state rules."""

from __future__ import annotations

from gazekey.typing.typing_session import TypingSession, TypingSessionState


def test_activate_from_inactive():
    session = TypingSession()
    assert session.state is TypingSessionState.INACTIVE
    session.activate()
    assert session.is_active
    assert session.shift_oneshot_armed is False


def test_shift_arm_and_consume_on_letter():
    session = TypingSession()
    session.activate()
    session.arm_shift()
    assert session.shift_oneshot_armed is True
    assert session.consume_shift_for_letter() is True
    assert session.shift_oneshot_armed is False
    assert session.consume_shift_for_letter() is False


def test_shift_clears_on_pause():
    session = TypingSession()
    session.activate()
    session.arm_shift()
    session.pause()
    assert session.is_paused
    assert session.shift_oneshot_armed is False


def test_shift_clears_on_recalibration():
    session = TypingSession()
    session.activate()
    session.arm_shift()
    session.on_recalibration()
    assert session.is_inactive
    assert session.shift_oneshot_armed is False


def test_shift_clears_on_mapping_session_reset():
    session = TypingSession()
    session.activate()
    session.arm_shift()
    session.on_mapping_session_reset()
    assert session.is_inactive
    assert session.shift_oneshot_armed is False


def test_shift_clears_on_tracking_terminated():
    session = TypingSession()
    session.activate()
    session.arm_shift()
    session.on_tracking_terminated()
    assert session.is_inactive
    assert session.shift_oneshot_armed is False


def test_pause_resume_cycle():
    session = TypingSession()
    session.activate()
    session.pause()
    assert session.is_paused
    session.resume()
    assert session.is_active


def test_arm_shift_ignored_when_inactive():
    session = TypingSession()
    session.arm_shift()
    assert session.shift_oneshot_armed is False
