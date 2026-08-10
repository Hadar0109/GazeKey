"""Gaze typing runtime — MappedGazePoint → hit-test → dwell → KeyAction.

Single key-detection path: existing ``hit_test_layout_keys`` / layout geometry.
Does not change keyboard geometry or mapping behavior.
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
    is_calibrate_action,
    is_os_bound_action,
    is_pause_resume_action,
    is_shift_action,
    is_suggestion_action,
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
    system_toggled: bool = False
    suggestion_accepted: bool = False
    calibrate_requested: bool = False


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
        on_session_ui_sync: Optional[Callable[[], None]] = None,
        on_suggestion_accept: Optional[Callable[[str, KeyActionSource], None]] = None,
        on_calibrate: Optional[Callable[[], None]] = None,
    ) -> None:
        self.session = session
        self.dwell = dwell
        self.dispatcher = dispatcher
        self._clock = clock
        self._on_session_ui_sync = on_session_ui_sync
        self._on_suggestion_accept = on_suggestion_accept
        self._on_calibrate = on_calibrate
        self._last_dwell: Optional[DwellFrameResult] = None
        # Hard gate: False during calibration fixation (T045).
        self.os_inject_enabled = True

    @property
    def last_dwell(self) -> Optional[DwellFrameResult]:
        return self._last_dwell

    def reset(self) -> None:
        """Clear dwell + session (recalib / mapping reset)."""
        self.dwell.reset()
        self.session.reset()
        self._sync_ui()

    def set_os_inject_enabled(self, enabled: bool) -> None:
        """Disable OS inject during calibration; cancel in-flight dwell."""
        self.os_inject_enabled = bool(enabled)
        if not self.os_inject_enabled:
            self.dwell.cancel_progress()

    def on_mapped_gaze(
        self,
        gaze: MappedGazePoint,
        dt: float,
        layout_keys: Sequence,
    ) -> GazeTypingFrameResult:
        """
        Process one mapped-gaze frame.

        When ``gaze.valid`` is False, cancels dwell progress and emits no KeyAction.
        When ``os_inject_enabled`` is False (calibration), never publishes OS actions.
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
            gaze_valid=gaze.valid and self.os_inject_enabled,
            dwell_enabled=dwell_enabled and self.os_inject_enabled,
        )
        self._last_dwell = dwell_result

        published: Optional[KeyAction] = None
        system_toggled = False
        suggestion_accepted = False
        calibrate_requested = False
        if (
            self.os_inject_enabled
            and dwell_result.fired
            and dwell_result.fired_key_id is not None
        ):
            action_str = key_action
            if action_str is None and layout_keys:
                action_str = self._action_for_key_id(layout_keys, dwell_result.fired_key_id)
            if action_str is not None:
                published, system_toggled, suggestion_accepted, calibrate_requested = (
                    self._handle_activation(
                        key_id=dwell_result.fired_key_id,
                        action=action_str,
                        source=KeyActionSource.DWELL,
                        apply_mouse_cooldown=False,
                    )
                )

        return GazeTypingFrameResult(
            target_key_id=target_key_id,
            dwell=dwell_result,
            published=published,
            system_toggled=system_toggled,
            suggestion_accepted=suggestion_accepted,
            calibrate_requested=calibrate_requested,
        )

    def on_mouse_key(
        self,
        *,
        key_id: str,
        action: str,
    ) -> Optional[KeyAction]:
        """Optional mouse path — same KeyAction / system-control handling as dwell."""
        if not self.os_inject_enabled:
            return None
        published, _system, _suggestion, _calibrate = self._handle_activation(
            key_id=key_id,
            action=action,
            source=KeyActionSource.MOUSE,
            apply_mouse_cooldown=True,
        )
        return published

    def cancel_dwell(self) -> None:
        """Cancel in-progress dwell (e.g. prefix_epoch changed mid-dwell)."""
        self.dwell.cancel_progress()

    def _dwell_enabled_for_action(self, action: Optional[str]) -> bool:
        state = self.session.state
        if state is TypingSessionState.INACTIVE:
            # Recovery: Calibrate remains dwellable so Recalibrate can restart calib.
            return bool(action) and is_calibrate_action(action)
        if state is TypingSessionState.ACTIVE:
            return True
        # paused: Pause/Resume or Calibrate
        if action is None:
            return False
        return is_pause_resume_action(action) or is_calibrate_action(action)

    def _handle_activation(
        self,
        *,
        key_id: str,
        action: str,
        source: KeyActionSource,
        apply_mouse_cooldown: bool,
    ) -> tuple[Optional[KeyAction], bool, bool, bool]:
        if is_calibrate_action(action) or is_calibrate_action(key_id):
            if self._on_calibrate is not None:
                self._on_calibrate()
            if apply_mouse_cooldown:
                self.dwell.begin_cooldown()
            return None, False, False, True

        if is_pause_resume_action(action):
            toggled = self._toggle_pause_resume()
            if toggled and apply_mouse_cooldown:
                self.dwell.begin_cooldown()
            if toggled:
                self._sync_ui()
            return None, toggled, False, False

        if is_suggestion_action(action) or is_suggestion_action(key_id):
            if not self.session.is_active:
                return None, False, False, False
            if self._on_suggestion_accept is not None:
                self._on_suggestion_accept(key_id if is_suggestion_action(key_id) else action, source)
            if apply_mouse_cooldown:
                self.dwell.begin_cooldown()
            return None, False, True, False

        if is_shift_action(action):
            if self.session.is_active:
                self.session.arm_shift()
                if apply_mouse_cooldown:
                    self.dwell.begin_cooldown()
                self._sync_ui()
            return None, False, False, False

        if not is_os_bound_action(action):
            return None, False, False, False

        if not self.session.is_active:
            return None, False, False, False

        shift_armed = self.session.shift_oneshot_armed
        key_action = builds_os_key_action(
            action,
            key_id=key_id,
            source=source,
            timestamp=float(self._clock()),
            shift_armed=shift_armed,
        )
        if key_action is None:
            return None, False, False, False

        if role_for_action(action) is KeyRole.LETTER:
            self.session.consume_shift_for_letter()
            self._sync_ui()

        if apply_mouse_cooldown:
            self.dwell.begin_cooldown()

        self.dispatcher.publish(key_action)
        return key_action, False, False, False

    def _toggle_pause_resume(self) -> bool:
        if self.session.is_active:
            self.session.pause()
            self.dwell.cancel_progress()
            return True
        if self.session.is_paused:
            self.session.resume()
            return True
        return False

    def _sync_ui(self) -> None:
        if self._on_session_ui_sync is not None:
            self._on_session_ui_sync()

    @staticmethod
    def _action_for_key_id(layout_keys: Sequence, key_id: str) -> Optional[str]:
        for key in layout_keys:
            if str(getattr(key, "key_id")) == key_id:
                return str(getattr(key, "key_action"))
        return None
