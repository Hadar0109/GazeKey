"""GazeSample dispatch: official GazeFollower → dwell → OS typing."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from gazekey.typing.gaze_typing_runtime import MappedGazePoint

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class GazeLoopController:
    """Routes GazeSample frames to product typing. No legacy mapper/tracking."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._last_tick_time = time.perf_counter()

    def on_gaze_sample(self, sample) -> None:
        """GazeSample → MappedGazePoint → live QRect hit-test → dwell.

        Production GazeFollower path. Does not call the legacy gaze stack
        or extra smoothing after official HeuristicFilter.
        """
        h = self._host
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if h._devtools.benchmark_active():
            handler = getattr(h._devtools, "process_benchmark_gaze_sample", None)
            if callable(handler):
                try:
                    handler(sample)
                except Exception as e:
                    h._log_verbose(f"[benchmark] GazeSample handler failed: {e}")
            return

        h._ensure_typing_auto_started()
        runtime = getattr(h, "_typing_runtime", None)
        if runtime is None or h._is_calibrating or not self.gaze_typing_active():
            return

        gaze = MappedGazePoint.from_gaze_sample(sample)
        layout_keys = getattr(h, "_layout_keys", None) or []
        if not layout_keys:
            try:
                h._keyboard_layout_builder.export_keyboard_layout()
                layout_keys = getattr(h, "_layout_keys", None) or []
            except Exception:
                layout_keys = []

        frame_result = runtime.on_mapped_gaze(gaze, dt, layout_keys)
        h._update_dwell_visuals(frame_result)

    def gaze_typing_active(self) -> bool:
        """True when product typing should consume mapped gaze (active or paused)."""
        h = self._host
        runtime = getattr(h, "_typing_runtime", None)
        if runtime is None:
            return False
        return (
            h.is_expanded
            and not h._is_calibrating
            and h._calibration_usable()
            and not h._devtools.benchmark_active()
            and not runtime.session.is_inactive
            and runtime.os_inject_enabled
        )
