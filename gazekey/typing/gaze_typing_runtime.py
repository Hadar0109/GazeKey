"""Gaze typing runtime — MappedGazePoint → hit-test → dwell → KeyAction.

Single key-detection path: existing ``hit_test_layout_keys`` / layout geometry.
Does not change keyboard geometry or mapping behavior. Gaze-loop auto-start
wiring is T042; this module is the callable typing path for that wiring.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from gazekey.typing.action_dispatcher import ActionDispatcher
from gazekey.typing.dwell_engine import DwellEngine, DwellFrameResult
from gazekey.typing.key_action import KeyAction, KeyActionSource
from gazekey.typing.key_hit_tester import hit_test_layout_keys
from gazekey.typing.key_semantics import (
    builds_os_key_action,
    is_os_bound_action,
    is_shift_action,
    role_for_action,
    KeyRole,
)
from gazekey.typing.typing_session import TypingSession, TypingSessionState


@dataclass(frozen=True)
class MappedGazePoint:
    """Mapped screen gaze after predict + smooth (data-model)."""

    x: float
    y: float
    valid: bool


@dataclass(frozen=True)
class GazeTypingFrameResult:
    """Per-frame typing observation (for UI dwell feedback — visuals in T047)."""

    target_key_id: Optional[str]
    dwell: DwellFrameResult
    published: Optional[KeyAction] = None


class GazeTypingRuntime:
    """
    Wire mapped gaze through layout hit-test and dwell into ActionDispatcher.

    Hit-test uses ``hit_test_layout_keys`` on the current layout geometry snapshot
    (same SoT as the product keyboard). No parallel key-detection path.
    """

    def __init__(
        self,
        session: TypingSession,
        dwell: DwellEngine,
        dispatcher: ActionDispatcher,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.session = session
        self.dwell = dwell
        self.dispatcher = dispatcher
        self._clock = clock
        self._last_dwell: Optional[DwellFrameResult] = None

    @property
    def last_dwell(self) -> Optional[DwellFrameResult]:
        return self._last_dwell

    def reset(self) -> None:
        """Clear dwell + session (recalib / mapping reset)."""
        self.dwell.reset()
        self.session.reset()

    def on_mapped_gaze(
        self,
        gaze: MappedGazePoint,
        dt: float,
        layout_keys: Sequence,
    ) -> GazeTypingFrameResult:
        """
        Process one mapped-gaze frame.

        When ``gaze.valid`` is False, cancels dwell progress and emits no KeyAction.
        """
        target_key_id: Optional[str] = None
        key_action: Optional[str] = None

        if gaze.valid and layout_keys:
            idx = hit_test_layout_keys(layout_keys, gaze.x, gaze.y)
            if idx is not None:
                key = layout_keys[idx]
                target_key_id = str(getattr(key, "key_id"))
                key_action = str(getattr(key, "key_action"))

        dwell_enabled = self._dwell_enabled_for_action(key_action)
        dwell_result = self.dwell.update(
            target_key_id,
            dt,
            gaze_valid=gaze.valid,
            dwell_enabled=dwell_enabled,
        )
        self._last_dwell = dwell_result

        published: Optional[KeyAction] = None
        if dwell_result.fired and dwell_result.fired_key_id is not None:
            action_str = key_action
            if action_str is None and layout_keys:
                action_str = self._action_for_key_id(layout_keys, dwell_result.fired_key_id)
            if action_str is not None:
                published = self._handle_activation(
                    key_id=dwell_result.fired_key_id,
                    action=action_str,
                    source=KeyActionSource.DWELL,
                )

        return GazeTypingFrameResult(
            target_key_id=target_key_id,
            dwell=dwell_result,
            published=published,
        )

    def on_mouse_key(
        self,
        *,
        key_id: str,
        action: str,
    ) -> Optional[KeyAction]:
        """Optional mouse path — same KeyAction completion handling as dwell."""
        if self.session.state is not TypingSessionState.ACTIVE:
            # Pause/Resume mouse handling arrives in T043; OS keys ignored when not active.
            if is_shift_action(action) or is_os_bound_action(action):
                return None
            return None
        return self._handle_activation(
            key_id=key_id,
            action=action,
            source=KeyActionSource.MOUSE,
        )

    def _dwell_enabled_for_action(self, action: Optional[str]) -> bool:
        state = self.session.state
        if state is TypingSessionState.INACTIVE:
            return False
        if state is TypingSessionState.ACTIVE:
            return True
        # paused: drop OS-key / Shift dwell; system controls (T043) can re-enable later
        if action is None:
            return False
        role = role_for_action(action)
        return role not in {
            KeyRole.LETTER,
            KeyRole.SPACE,
            KeyRole.BACKSPACE,
            KeyRole.ENTER,
            KeyRole.SHIFT_ONESHOT,
            KeyRole.NON_OS,
        }

    def _handle_activation(
        self,
        *,
        key_id: str,
        action: str,
        source: KeyActionSource,
    ) -> Optional[KeyAction]:
        if is_shift_action(action):
            if self.session.is_active:
                self.session.arm_shift()
            return None

        if not is_os_bound_action(action):
            return None

        if not self.session.is_active:
            return None

        shift_armed = self.session.shift_oneshot_armed
        key_action = builds_os_key_action(
            action,
            key_id=key_id,
            source=source,
            timestamp=float(self._clock()),
            shift_armed=shift_armed,
        )
        if key_action is None:
            return None

        if role_for_action(action) is KeyRole.LETTER:
            self.session.consume_shift_for_letter()

        self.dispatcher.publish(key_action)
        return key_action

    @staticmethod
    def _action_for_key_id(layout_keys: Sequence, key_id: str) -> Optional[str]:
        for key in layout_keys:
            if str(getattr(key, "key_id")) == key_id:
                return str(getattr(key, "key_action"))
        return None
