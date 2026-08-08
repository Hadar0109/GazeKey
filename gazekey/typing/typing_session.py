"""TypingSession — inactive/active/paused + Shift oneshot arm/clear rules."""

from __future__ import annotations

from enum import Enum


class TypingSessionState(str, Enum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"


class TypingSession:
    """In-process typing session state for the product keyboard path."""

    def __init__(self) -> None:
        self._state = TypingSessionState.INACTIVE
        self._shift_oneshot_armed = False

    @property
    def state(self) -> TypingSessionState:
        return self._state

    @property
    def shift_oneshot_armed(self) -> bool:
        return self._shift_oneshot_armed

    @property
    def is_active(self) -> bool:
        return self._state is TypingSessionState.ACTIVE

    @property
    def is_paused(self) -> bool:
        return self._state is TypingSessionState.PAUSED

    @property
    def is_inactive(self) -> bool:
        return self._state is TypingSessionState.INACTIVE

    def activate(self) -> None:
        """inactive/paused → active when a usable mapper/mapped-gaze is available."""
        self._state = TypingSessionState.ACTIVE

    def pause(self) -> None:
        """active → paused; clears pending Shift (FR clear rules)."""
        if self._state is TypingSessionState.ACTIVE:
            self._state = TypingSessionState.PAUSED
        self.clear_shift()

    def resume(self) -> None:
        """paused → active."""
        if self._state is TypingSessionState.PAUSED:
            self._state = TypingSessionState.ACTIVE

    def reset(self) -> None:
        """Recalibration / mapping-session reset → inactive; clear Shift."""
        self._state = TypingSessionState.INACTIVE
        self.clear_shift()

    def on_recalibration(self) -> None:
        """Typing session reset on recalibration paths."""
        self.reset()

    def on_mapping_session_reset(self) -> None:
        """Mapper cleared / failed gate / new session."""
        self.reset()

    def on_tracking_terminated(self) -> None:
        """Tracking/mapping session termination or teardown."""
        self.reset()

    def arm_shift(self) -> None:
        """Arm one-shot Shift for the next letter (no OS KeyAction)."""
        if self._state is TypingSessionState.ACTIVE:
            self._shift_oneshot_armed = True

    def clear_shift(self) -> None:
        self._shift_oneshot_armed = False

    def consume_shift_for_letter(self) -> bool:
        """
        Consume one-shot Shift for a letter KeyAction.

        Returns True if Shift was armed (caller should uppercase), then clears.
        """
        armed = self._shift_oneshot_armed
        self._shift_oneshot_armed = False
        return armed
