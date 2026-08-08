"""Unit tests for DwellEngine (contracts/dwell-selection.md)."""

from __future__ import annotations

from gazekey.typing.dwell_engine import (
    DWELL_SEC,
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
    )


def test_progress_reaches_fire_at_dwell_sec():
    eng = _engine()
    # Almost complete
    r = eng.update("key_a", DWELL_SEC - 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.phase is DwellPhase.PROGRESSING
    assert 0.9 < r.progress_01 < 1.0

    r = eng.update("key_a", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True
    assert r.fired_key_id == "key_a"
    assert r.phase is DwellPhase.FIRED_LOCK
    assert r.progress_01 == 1.0


def test_leave_before_completion_cancels():
    eng = _engine()
    eng.update("key_a", 0.4, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_b", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.progress_01 < 0.2
    assert r.target_key_id == "key_b"


def test_same_key_lock_until_confirmed_leave():
    eng = _engine()
    r = eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True

    # Still on same key — locked, no re-fire
    for _ in range(5):
        r = eng.update("key_a", 0.1, gaze_valid=True, dwell_enabled=True)
        assert r.fired is False
        assert r.phase is DwellPhase.FIRED_LOCK

    # Leave for fewer than 5 frames — still locked
    for _ in range(LEAVE_CONFIRM_FRAMES - 1):
        r = eng.update(None, 0.01, gaze_valid=True, dwell_enabled=True)
        assert eng.locked_key_id == "key_a"

    # 5th off-key frame clears lock
    r = eng.update(None, 0.01, gaze_valid=True, dwell_enabled=True)
    assert eng.locked_key_id is None


def test_rearm_after_five_frame_leave():
    eng = _engine()
    eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    # Drain cooldown while leaving
    for _ in range(LEAVE_CONFIRM_FRAMES):
        eng.update(None, POST_ACTIVATION_COOLDOWN_SEC, gaze_valid=True, dwell_enabled=True)
    assert eng.locked_key_id is None

    r = eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    assert r.fired is True
    assert r.fired_key_id == "key_a"


def test_global_cooldown_blocks_progress():
    eng = _engine()
    eng.update("key_a", DWELL_SEC, gaze_valid=True, dwell_enabled=True)
    # Clear same-key lock with tiny dt so most of the 0.20 s cooldown remains.
    for _ in range(LEAVE_CONFIRM_FRAMES):
        eng.update(None, 0.001, gaze_valid=True, dwell_enabled=True)
    assert eng.locked_key_id is None

    r = eng.update("key_b", 0.05, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.in_cooldown is True
    assert r.progress_01 == 0.0

    # Finish cooldown, then dwell on another key.
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


def test_tracking_loss_cancels_without_key_action():
    eng = _engine()
    eng.update("key_a", 0.8, gaze_valid=True, dwell_enabled=True)
    r = eng.update("key_a", 0.2, gaze_valid=False, dwell_enabled=True)
    assert r.fired is False
    assert r.progress_01 == 0.0
    assert r.fired_key_id is None

    # Recovery does not inherit prior progress
    r = eng.update("key_a", 0.1, gaze_valid=True, dwell_enabled=True)
    assert r.fired is False
    assert r.progress_01 < 0.2
