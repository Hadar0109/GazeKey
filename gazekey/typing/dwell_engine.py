"""Reliability-first dwell engine (contracts/dwell-selection.md)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


DWELL_SEC = 0.9
POST_ACTIVATION_COOLDOWN_SEC = 0.20
LEAVE_CONFIRM_FRAMES = 5
KEY_SWITCH_CONFIRM_SEC = 0.25


class DwellPhase(str, Enum):
    IDLE = "idle"
    PROGRESSING = "progressing"
    SWITCH_PENDING = "switch_pending"
    FIRED_LOCK = "fired_lock"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class DwellFrameResult:
    """Per-frame dwell observation for UI + runtime completion handling."""

    phase: DwellPhase
    target_key_id: Optional[str]
    progress_01: float
    frames_off_target: int
    fired: bool
    fired_key_id: Optional[str]
    in_cooldown: bool
    pending_key_id: Optional[str] = None


class DwellEngine:
    """
    Accumulate dwell on a stable active key; fire once; lock until confirmed leave.

    Mid-dwell key changes require ``key_switch_confirm_sec`` continuous confirmation.
    Tracking/mapped-gaze loss cancels immediately (no switch grace) and never fires.
    """

    def __init__(
        self,
        *,
        dwell_sec: float = DWELL_SEC,
        post_activation_cooldown_sec: float = POST_ACTIVATION_COOLDOWN_SEC,
        leave_confirm_frames: int = LEAVE_CONFIRM_FRAMES,
        key_switch_confirm_sec: float = KEY_SWITCH_CONFIRM_SEC,
    ) -> None:
        self.dwell_sec = float(dwell_sec)
        self.post_activation_cooldown_sec = float(post_activation_cooldown_sec)
        self.leave_confirm_frames = int(leave_confirm_frames)
        self.key_switch_confirm_sec = float(key_switch_confirm_sec)
        self._elapsed = 0.0
        self._target_key_id: Optional[str] = None
        self._phase = DwellPhase.IDLE
        self._locked_key_id: Optional[str] = None
        self._frames_off_target = 0
        self._cooldown_remaining = 0.0
        self._pending_key_id: Optional[str] = None
        self._pending_elapsed = 0.0
        self._away_elapsed = 0.0

    @property
    def phase(self) -> DwellPhase:
        return self._phase

    @property
    def progress_01(self) -> float:
        if self.dwell_sec <= 0:
            return 0.0
        return max(0.0, min(1.0, self._elapsed / self.dwell_sec))

    @property
    def locked_key_id(self) -> Optional[str]:
        return self._locked_key_id

    def reset(self) -> None:
        """Clear dwell progress, pending switch, and lock (session reset / recalibration)."""
        self._elapsed = 0.0
        self._target_key_id = None
        self._phase = DwellPhase.IDLE
        self._locked_key_id = None
        self._frames_off_target = 0
        self._cooldown_remaining = 0.0
        self._clear_pending()

    def cancel_progress(self) -> None:
        """Cancel in-progress dwell without clearing same-key lock or cooldown."""
        self._elapsed = 0.0
        self._target_key_id = None
        self._clear_pending()
        if self._locked_key_id is not None:
            self._phase = DwellPhase.FIRED_LOCK
        else:
            self._phase = DwellPhase.CANCELLED

    def begin_cooldown(self) -> None:
        """Start global post-activation cooldown (mouse Pause/Resume / non-dwell path)."""
        self._cooldown_remaining = self.post_activation_cooldown_sec
        self._elapsed = 0.0
        self._clear_pending()

    def _clear_pending(self) -> None:
        self._pending_key_id = None
        self._pending_elapsed = 0.0
        self._away_elapsed = 0.0

    def _result(
        self,
        *,
        fired: bool = False,
        fired_key_id: Optional[str] = None,
        in_cooldown: bool,
        report_target: Optional[str] = None,
    ) -> DwellFrameResult:
        target = self._target_key_id if report_target is None else report_target
        return DwellFrameResult(
            phase=self._phase,
            target_key_id=target,
            progress_01=self.progress_01,
            frames_off_target=self._frames_off_target,
            fired=fired,
            fired_key_id=fired_key_id,
            in_cooldown=in_cooldown,
            pending_key_id=self._pending_key_id,
        )

    def update(
        self,
        target_key_id: Optional[str],
        dt: float,
        *,
        gaze_valid: bool,
        dwell_enabled: bool = True,
    ) -> DwellFrameResult:
        """
        Advance dwell by one frame.

        ``gaze_valid=False`` cancels immediately (no key-switch grace).
        ``dwell_enabled=False`` cancels progress; post-fire lock leave still advances.
        Mid-dwell hit-test changes use ``key_switch_confirm_sec`` hysteresis.
        """
        dt = max(0.0, float(dt))
        fired = False
        fired_key_id: Optional[str] = None

        if self._cooldown_remaining > 0.0:
            if dt <= self._cooldown_remaining:
                self._cooldown_remaining -= dt
                dt = 0.0
            else:
                dt -= self._cooldown_remaining
                self._cooldown_remaining = 0.0

        in_cooldown = self._cooldown_remaining > 0.0
        effective_target = target_key_id if gaze_valid else None

        # Same-key lock leave runs even when dwell is disabled (paused off-key).
        if self._locked_key_id is not None:
            self._clear_pending()
            if effective_target == self._locked_key_id:
                self._frames_off_target = 0
                self._phase = DwellPhase.FIRED_LOCK
                self._elapsed = 0.0
                self._target_key_id = effective_target
                return self._result(in_cooldown=in_cooldown, report_target=effective_target)
            self._frames_off_target += 1
            if self._frames_off_target >= self.leave_confirm_frames:
                self._locked_key_id = None
                self._frames_off_target = 0
                self._phase = DwellPhase.IDLE
            else:
                self._phase = DwellPhase.FIRED_LOCK
                self._elapsed = 0.0
                self._target_key_id = None
                return self._result(in_cooldown=in_cooldown, report_target=None)

        # Tracking / mapped-gaze loss: immediate cancel (not part of switch grace).
        if not gaze_valid:
            self.cancel_progress()
            return self._result(in_cooldown=in_cooldown, report_target=None)

        if not dwell_enabled:
            self.cancel_progress()
            return self._result(in_cooldown=in_cooldown, report_target=None)

        # No active dwell yet — adopt first key immediately (cold start).
        if self._target_key_id is None:
            self._clear_pending()
            if effective_target is None:
                self._phase = DwellPhase.IDLE
                return self._result(in_cooldown=in_cooldown, report_target=None)
            self._target_key_id = effective_target
            self._elapsed = 0.0
            self._phase = DwellPhase.PROGRESSING
            # Fall through to accumulate this frame's dt on the new key.

        # On active key: resume / clear pending and accumulate.
        if effective_target == self._target_key_id:
            self._clear_pending()
            if in_cooldown or dt <= 0.0:
                if in_cooldown:
                    self._elapsed = 0.0
                    self._phase = DwellPhase.IDLE
                else:
                    self._phase = DwellPhase.PROGRESSING
                return DwellFrameResult(
                    phase=self._phase,
                    target_key_id=effective_target,
                    progress_01=0.0 if in_cooldown else self.progress_01,
                    frames_off_target=self._frames_off_target,
                    fired=False,
                    fired_key_id=None,
                    in_cooldown=in_cooldown,
                    pending_key_id=None,
                )

            self._elapsed += dt
            self._phase = DwellPhase.PROGRESSING
            progress = self.progress_01
            if self._elapsed >= self.dwell_sec:
                fired = True
                fired_key_id = self._target_key_id
                self._locked_key_id = self._target_key_id
                self._frames_off_target = 0
                self._elapsed = 0.0
                self._cooldown_remaining = self.post_activation_cooldown_sec
                self._phase = DwellPhase.FIRED_LOCK
                self._clear_pending()
                return DwellFrameResult(
                    phase=self._phase,
                    target_key_id=fired_key_id,
                    progress_01=1.0,
                    frames_off_target=0,
                    fired=True,
                    fired_key_id=fired_key_id,
                    in_cooldown=True,
                    pending_key_id=None,
                )
            return DwellFrameResult(
                phase=self._phase,
                target_key_id=self._target_key_id,
                progress_01=progress,
                frames_off_target=self._frames_off_target,
                fired=False,
                fired_key_id=None,
                in_cooldown=False,
                pending_key_id=None,
            )

        # Away from active key: freeze progress; confirm switch or cancel.
        self._away_elapsed += dt
        if effective_target == self._pending_key_id:
            self._pending_elapsed += dt
        else:
            self._pending_key_id = effective_target
            self._pending_elapsed = dt

        # Confirmed switch to one continuous different key.
        if (
            effective_target is not None
            and self._pending_elapsed >= self.key_switch_confirm_sec
        ):
            self._target_key_id = effective_target
            self._elapsed = 0.0
            self._clear_pending()
            self._phase = DwellPhase.PROGRESSING
            if in_cooldown or dt <= 0.0:
                return self._result(in_cooldown=in_cooldown, report_target=effective_target)
            # Start new dwell from zero; do not apply this frame's full dt as
            # confirmation time already consumed the away interval.
            return self._result(in_cooldown=False, report_target=effective_target)

        # Confirmed cancel: continuous off-key, or away without a stable new key.
        if self._away_elapsed >= self.key_switch_confirm_sec:
            self.cancel_progress()
            return self._result(in_cooldown=in_cooldown, report_target=None)

        # Pending: keep visual/progress on the active key (frozen).
        self._phase = DwellPhase.SWITCH_PENDING
        return DwellFrameResult(
            phase=self._phase,
            target_key_id=self._target_key_id,
            progress_01=self.progress_01,
            frames_off_target=self._frames_off_target,
            fired=False,
            fired_key_id=None,
            in_cooldown=in_cooldown,
            pending_key_id=self._pending_key_id,
        )
