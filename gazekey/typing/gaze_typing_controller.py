"""Orchestrate gaze hit testing, dwell selection, and key focus feedback."""

from typing import Callable, Optional

from PySide6.QtWidgets import QPushButton, QWidget

from gazekey.typing.dwell_selector import DwellSelector
from gazekey.typing.key_hit_tester import KeyHitTester


class GazeTypingController:
    def __init__(
        self,
        keyboard_root: QWidget,
        on_focus_key: Callable[[Optional[QPushButton], float], None],
        on_activate_key: Callable[[QPushButton], None],
        dwell_selector: Optional[DwellSelector] = None,
    ) -> None:
        self._hit_tester = KeyHitTester(keyboard_root)
        self._dwell = dwell_selector or DwellSelector()
        self._on_focus_key = on_focus_key
        self._on_activate_key = on_activate_key
        self._enabled = True
        self._focused_button: Optional[QPushButton] = None

    def set_enabled(self, enabled: bool) -> None:
        if self._enabled and not enabled:
            self.clear_focus()
        self._enabled = enabled

    def tick(
        self,
        screen_x: Optional[float],
        screen_y: Optional[float],
        dt: float,
    ) -> None:
        if not self._enabled:
            return

        self._hit_tester.refresh()

        if screen_x is None or screen_y is None:
            state = self._dwell.update(None, dt)
            self._update_focus(None, state.progress)
            return

        button = self._hit_tester.hit_test(screen_x, screen_y)
        target_id = id(button) if button is not None else None

        state = self._dwell.update(target_id, dt)
        self._update_focus(button, state.progress)

        if state.should_activate and button is not None:
            self._on_activate_key(button)

    def clear_focus(self) -> None:
        self._dwell.reset()
        self._update_focus(None, 0.0)

    def _update_focus(
        self,
        button: Optional[QPushButton],
        progress: float,
    ) -> None:
        if button is self._focused_button and button is not None:
            self._on_focus_key(button, progress)
            return
        self._on_focus_key(self._focused_button, 0.0)
        self._focused_button = button
        self._on_focus_key(button, progress)
