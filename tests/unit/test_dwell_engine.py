"""Unit tests for DwellEngine (contracts/dwell-selection.md)."""

from __future__ import annotations

from gazekey.typing.dwell_engine import (
    DWELL_SEC,
    KEY_SWITCH_CONFIRM_SEC,
    LEAVE_CONFIRM_FRAMES,
    POST_ACTIVATION_COOLDOWN_SEC,
    DwellEngine,
    DwellPhase,
)


def _engine() -> DwellEngine:
    return DwellEngine(
        dwell_sec=DWELL_SEC,
        post_activation_cooldown_sec=POST_ACTIVATION_COOLDOWN_SEC,
        leave_confirm_frames=LEAVE_CONFIRM_FRAMES,
        key_switch_confirm_sec=KEY_SWITCH_CONFIRM_SEC,
    )


def test_progress_reaches_fire_at_dwell_sec():
    eng = _engine()
    r = eng.update("key_a", DWELL_SEC - 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.phase is DwellPhase.PROGRESSING
    assert 0.9 < r.progress_01 < 1.0

    r = eng.update("key_a", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True
    assert r.fired_key_id == "key_a"
    assert r.phase is DwellPhase.FIRED_LOCK
    assert r.progress_01 == 1.0


def test_brief_other_key_does_not_switch_or_cancel():
    eng = _engine()
    eng.update("key_a", 0.4, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_b", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.phase is DwellPhase.SWITCH_PENDING
    assert r.target_key_id == "key_a"
    assert abs(r.progress_01 - (0.4 / DWELL_SEC)) < 1e-6
    assert r.pending_key_id == "key_b"


def test_return_before_switch_confirm_resumes_progress():
    eng = _engine()
    eng.update("key_a", 0.4, gaze_valid=True, dwell_enabled=True)
    eng.update("key_b", 0.10, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_a", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.phase is DwellPhase.PROGRESSING
    assert r.target_key_id == "key_a"
    assert r.pending_key_id is None
    # Resumed prior 0.4s plus this frame's 0.05s
    assert abs(r.progress_01 - (0.45 / DWELL_SEC)) < 1e-6


def test_confirmed_switch_resets_dwell_on_new_key():
    eng = _engine()
    eng.update("key_a", 0.4, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_b", KEY_SWITCH_CONFIRM_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.target_key_id == "key_b"
    assert r.phase is DwellPhase.PROGRESSING
    assert r.progress_01 == 0.0
    assert r.pending_key_id is None

    r = eng.update("key_b", 0.1, gaze_valid=True, dwell_enabled=True)
    assert abs(r.progress_01 - (0.1 / DWELL_SEC)) < 1e-6


def test_confirmed_off_key_cancels_without_key_action():
    eng = _engine()
    eng.update("key_a", 0.4, gaze_valid=True, dwell_enabled=True)
    r = eng.update(None, KEY_SWITCH_CONFIRM_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.fired_key_id is None
    assert r.progress_01 == 0.0
    assert r.phase is DwellPhase.CANCELLED


def test_wandering_keys_cancels_frozen_progress():
    """Away 0.25s without any single key held continuously → cancel."""
    eng = _engine()
    eng.update("key_a", 0.5, gaze_valid=True, dwell_enabled=True)
    eng.update("key_b", 0.10, gaze_valid=True, dwell_enabled=True)
    eng.update("key_c", 0.10, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_b", 0.05, gaze_valid=True, dwell_enabled=True)
    # away_elapsed = 0.25 with no candidate held for 0.25s
    assert r.fired is False
    assert r.progress_01 == 0.0
    assert r.phase is DwellPhase.CANCELLED


def test_same_key_lock_until_confirmed_leave():
    eng = _engine()
    r = eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True

    for _ in range(5):
        r = eng.update("key_a", 0.1, gaze_valid=True, dwell_enabled=True)
        assert r.fired is False
        assert r.phase is DwellPhase.FIRED_LOCK

    for _ in range(LEAVE_CONFIRM_FRAMES - 1):
        r = eng.update(None, 0.01, gaze_valid=True, dwell_enabled=True)
        assert eng.locked_key_id == "key_a"

    r = eng.update(None, 0.01, gaze_valid=True, dwell_enabled=True)
    assert eng.locked_key_id is None


def test_rearm_after_five_frame_leave():
    eng = _engine()
    eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    for _ in range(LEAVE_CONFIRM_FRAMES):
        eng.update(None, POST_ACTIVATION_COOLDOWN_SEC, gaze_valid=True, dwell_enabled=True)
    assert eng.locked_key_id is None

    r = eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True
    assert r.fired_key_id == "key_a"


def test_global_cooldown_blocks_progress():
    eng = _engine()
    eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    for _ in range(LEAVE_CONFIRM_FRAMES):
        eng.update(None, 0.001, gaze_valid=True, dwell_enabled=True)
    assert eng.locked_key_id is None

    r = eng.update("key_b", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.in_cooldown is True
    assert r.progress_01 == 0.0

    eng.update("key_b", POST_ACTIVATION_COOLDOWN_SEC, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_b", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True


def test_pause_drop_disables_dwell():
    eng = _engine()
    eng.update("key_a", 0.5, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_a", 0.1, gaze_valid=True, dwell_enabled=False)
    assert r.fired is False
    assert r.progress_01 == 0.0
    assert r.phase in (DwellPhase.CANCELLED, DwellPhase.IDLE, DwellPhase.FIRED_LOCK)


def test_tracking_loss_cancels_immediately_without_grace():
    eng = _engine()
    eng.update("key_a", 0.8, gaze_valid=True, dwell_enabled=True)
    # Single invalid frame — no 0.25 s grace
    r = eng.update("key_a", 0.01, gaze_valid=False, dwell_enabled=True)
    assert r.fired is False
    assert r.progress_01 == 0.0
    assert r.fired_key_id is None
    assert r.phase is DwellPhase.CANCELLED

    r = eng.update("key_a", 0.1, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.progress_01 < 0.2
