"""Reliability-first dwell engine (contracts/dwell-selection.md)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


DWELL_SEC = 0.9
POST_ACTIVATION_COOLDOWN_SEC = 0.20
LEAVE_CONFIRM_FRAMES = 5


class DwellPhase(str, Enum):
    IDLE = "idle"
    PROGRESSING = "progressing"
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


class DwellEngine:
    """
    Accumulate dwell on a stable target_key_id; fire once; lock until confirmed leave.

    Tracking/mapped-gaze loss cancels progress and never fires.
    When ``dwell_enabled`` is False (e.g. paused OS keys / inactive), progress is
    dropped and no fire occurs.
    """

    def __init__(
        self,
        *,
        dwell_sec: float = DWELL_SEC,
        post_activation_cooldown_sec: float = POST_ACTIVATION_COOLDOWN_SEC,
        leave_confirm_frames: int = LEAVE_CONFIRM_FRAMES,
    ) -> None:
        self.dwell_sec = float(dwell_sec)
        self.post_activation_cooldown_sec = float(post_activation_cooldown_sec)
        self.leave_confirm_frames = int(leave_confirm_frames)
        self._elapsed = 0.0
        self._target_key_id: Optional[str] = None
        self._phase = DwellPhase.IDLE
        self._locked_key_id: Optional[str] = None
        self._frames_off_target = 0
        self._cooldown_remaining = 0.0

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
        """Clear dwell progress and lock (session reset / recalibration)."""
        self._elapsed = 0.0
        self._target_key_id = None
        self._phase = DwellPhase.IDLE
        self._locked_key_id = None
        self._frames_off_target = 0
        self._cooldown_remaining = 0.0

    def cancel_progress(self) -> None:
        """Cancel in-progress dwell without clearing same-key lock or cooldown."""
        self._elapsed = 0.0
        self._target_key_id = None
        if self._locked_key_id is not None:
            self._phase = DwellPhase.FIRED_LOCK
        else:
            self._phase = DwellPhase.CANCELLED

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

        ``gaze_valid=False`` or ``dwell_enabled=False`` cancels progress and never fires.
        """
        dt = max(0.0, float(dt))
        fired = False
        fired_key_id: Optional[str] = None

        # Consume cooldown before any dwell progress; leftover dt may accumulate.
        if self._cooldown_remaining > 0.0:
            if dt <= self._cooldown_remaining:
                self._cooldown_remaining -= dt
                dt = 0.0
            else:
                dt -= self._cooldown_remaining
                self._cooldown_remaining = 0.0

        in_cooldown = self._cooldown_remaining > 0.0

        if not gaze_valid or not dwell_enabled:
            self.cancel_progress()
            return DwellFrameResult(
                phase=self._phase,
                target_key_id=None,
                progress_01=0.0,
                frames_off_target=self._frames_off_target,
                fired=False,
                fired_key_id=None,
                in_cooldown=in_cooldown,
            )

        # Same-key lock: require confirmed leave before re-arming the locked key.
        if self._locked_key_id is not None:
            if target_key_id == self._locked_key_id:
                self._frames_off_target = 0
                self._phase = DwellPhase.FIRED_LOCK
                self._elapsed = 0.0
                self._target_key_id = target_key_id
                return DwellFrameResult(
                    phase=self._phase,
                    target_key_id=target_key_id,
                    progress_01=0.0,
                    frames_off_target=self._frames_off_target,
                    fired=False,
                    fired_key_id=None,
                    in_cooldown=in_cooldown,
                )
            self._frames_off_target += 1
            if self._frames_off_target >= self.leave_confirm_frames:
                self._locked_key_id = None
                self._frames_off_target = 0
                self._phase = DwellPhase.IDLE
            else:
                self._phase = DwellPhase.FIRED_LOCK
                self._elapsed = 0.0
                self._target_key_id = target_key_id
                return DwellFrameResult(
                    phase=self._phase,
                    target_key_id=target_key_id,
                    progress_01=0.0,
                    frames_off_target=self._frames_off_target,
                    fired=False,
                    fired_key_id=None,
                    in_cooldown=in_cooldown,
                )

        if target_key_id is None:
            if self._elapsed > 0.0 or self._target_key_id is not None:
                self.cancel_progress()
            else:
                self._phase = DwellPhase.IDLE
            return DwellFrameResult(
                phase=self._phase,
                target_key_id=None,
                progress_01=0.0,
                frames_off_target=self._frames_off_target,
                fired=False,
                fired_key_id=None,
                in_cooldown=in_cooldown,
            )

        if target_key_id != self._target_key_id:
            self._target_key_id = target_key_id
            self._elapsed = 0.0
            self._phase = DwellPhase.PROGRESSING

        if in_cooldown or dt <= 0.0:
            # Still tracking target, but gated by cooldown (no progress this frame).
            if in_cooldown:
                self._elapsed = 0.0
            return DwellFrameResult(
                phase=DwellPhase.IDLE if in_cooldown else self._phase,
                target_key_id=target_key_id,
                progress_01=0.0 if in_cooldown else self.progress_01,
                frames_off_target=self._frames_off_target,
                fired=False,
                fired_key_id=None,
                in_cooldown=in_cooldown,
            )

        self._elapsed += dt
        self._phase = DwellPhase.PROGRESSING
        progress = self.progress_01

        if self._elapsed >= self.dwell_sec:
            fired = True
            fired_key_id = target_key_id
            self._locked_key_id = target_key_id
            self._frames_off_target = 0
            self._elapsed = 0.0
            self._cooldown_remaining = self.post_activation_cooldown_sec
            self._phase = DwellPhase.FIRED_LOCK
            progress = 1.0

        return DwellFrameResult(
            phase=self._phase,
            target_key_id=target_key_id,
            progress_01=progress,
            frames_off_target=self._frames_off_target,
            fired=fired,
            fired_key_id=fired_key_id,
            in_cooldown=self._cooldown_remaining > 0.0,
        )
