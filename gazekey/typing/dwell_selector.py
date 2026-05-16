"""Dwell-time key selection state machine."""

from dataclasses import dataclass
from typing import Optional

DWELL_DURATION_SEC = 1.25
GLOBAL_COOLDOWN_SEC = 0.25
MISS_FRAMES_TO_RESET = 5


@dataclass
class DwellState:
    target_id: Optional[int]
    progress: float
    should_activate: bool


class DwellSelector:
    """
    Tracks dwell on a single key id.

    After activation, the same key cannot fire again until gaze leaves it.
    Brief tracking dropouts do not reset dwell progress.
    A short global cooldown blocks accidental double-fires.
    """

    def __init__(
        self,
        dwell_duration_sec: float = DWELL_DURATION_SEC,
        global_cooldown_sec: float = GLOBAL_COOLDOWN_SEC,
        miss_frames_to_reset: int = MISS_FRAMES_TO_RESET,
    ) -> None:
        self._dwell_duration = dwell_duration_sec
        self._global_cooldown = global_cooldown_sec
        self._miss_threshold = miss_frames_to_reset
        self._current_id: Optional[int] = None
        self._elapsed = 0.0
        self._last_progress = 0.0
        self._cooldown_remaining = 0.0
        self._locked_key_id: Optional[int] = None
        self._miss_frames = 0

    def update(self, target_id: Optional[int], dt: float) -> DwellState:
        self._cooldown_remaining = max(0.0, self._cooldown_remaining - dt)

        if target_id is None:
            self._miss_frames += 1
            if self._miss_frames >= self._miss_threshold:
                self._current_id = None
                self._elapsed = 0.0
                self._last_progress = 0.0
                self._locked_key_id = None
            return DwellState(self._current_id, self._last_progress, False)

        self._miss_frames = 0

        if self._locked_key_id is not None and target_id != self._locked_key_id:
            self._locked_key_id = None

        if self._locked_key_id is not None and target_id == self._locked_key_id:
            return DwellState(target_id, 0.0, False)

        if target_id != self._current_id:
            self._current_id = target_id
            self._elapsed = 0.0
            self._last_progress = 0.0

        progress = 0.0
        should_activate = False

        if self._cooldown_remaining <= 0.0:
            self._elapsed += dt
            progress = min(1.0, self._elapsed / self._dwell_duration)
            if progress >= 1.0 - 1e-9:
                should_activate = True
                self._locked_key_id = target_id
                self._elapsed = 0.0
                progress = 1.0
                self._cooldown_remaining = self._global_cooldown

        self._last_progress = progress
        return DwellState(target_id, progress, should_activate)

    def reset(self) -> None:
        self._current_id = None
        self._elapsed = 0.0
        self._last_progress = 0.0
        self._cooldown_remaining = 0.0
        self._locked_key_id = None
        self._miss_frames = 0
