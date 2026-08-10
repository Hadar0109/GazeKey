"""Gaze eye-data dispatch: calibration, typing, and read-only preview."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from gazekey.features import FeatureExtractor
from gazekey.runtime.mapper_runtime import MapperRuntime
from gazekey.typing.gaze_typing_runtime import MappedGazePoint

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class GazeLoopController:
    """Routes per-frame eye data to calibration, product typing, or preview."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._last_tick_time = time.perf_counter()

    def on_eye_data_main_thread(self, eye_data) -> None:
        h = self._host
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        calib_camera = h._camera_preview_during_calib and h._is_calibrating
        if h.tracking_manager and h.camera_preview_window and (not h._is_calibrating or calib_camera):
            frame = h.tracking_manager.get_latest_frame()
            if frame is not None:
                h.camera_preview_window.update_frame(frame)

        if calib_camera:
            h._ensure_camera_preview(show=True)

        if h.tracking_manager and not h._is_calibrating and h._gaze_mapper is not None:
            h._ensure_camera_preview(show=True)

        # Gaze-status chrome removed from product UI (003 / FR-008); no camera_status_label updates.

        # T045: calibration fixation path never reaches typing / OS inject.
        if h._is_calibrating and h._calibration_overlay is not None:
            runtime = getattr(h, "_typing_runtime", None)
            if runtime is not None:
                runtime.set_os_inject_enabled(False)
            overlay = getattr(h, "_dwell_overlay", None)
            if overlay is not None:
                overlay.clear()
            self._process_calibration_eye_data(eye_data, dt)
            return

        if h._devtools.benchmark_active():
            try:
                h._devtools.process_benchmark_eye_data(eye_data)
            except Exception as e:
                h._log_verbose(f"[benchmark] frame handler failed: {e}")
            return

        # T042: auto-start typing when a usable mapper/mapped-gaze state exists.
        h._ensure_typing_auto_started()

        if self.gaze_typing_active():
            self.process_gaze_typing(eye_data, dt)
            return

        if self.gaze_preview_active():
            self.process_gaze_preview(eye_data, dt)

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

    def gaze_preview_active(self) -> bool:
        h = self._host
        return (
            h.is_expanded
            and not h._is_calibrating
            and h._gaze_mapper is not None
            and h._preview_mode
            and not h._devtools.benchmark_active()
        )

    def _process_calibration_eye_data(self, eye_data, dt: float) -> None:
        h = self._host
        now_ms = int(time.time() * 1000)
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        if h._calib_v_ema_enabled and features.avg_v is not None:
            if h._calib_v_ema is None:
                h._calib_v_ema = float(features.avg_v)
            else:
                a = float(h._calib_v_alpha)
                h._calib_v_ema = (1.0 - a) * float(h._calib_v_ema) + a * float(features.avg_v)
            features = MapperRuntime.with_avg(
                features, avg_h=features.avg_h, avg_v=float(h._calib_v_ema)
            )
        h._calibration_overlay.add_features_dt(features, dt_ms=dt * 1000.0)

    def process_gaze_typing(self, eye_data, dt: float) -> None:
        """MappedGazePoint → layout hit-test → dwell → KeyAction (T041 path only)."""
        h = self._host
        runtime = getattr(h, "_typing_runtime", None)
        if runtime is None or h._is_calibrating or not runtime.os_inject_enabled:
            return

        now_ms = int(time.time() * 1000)
        xy = h._preview_mapped_screen_xy(eye_data, now_ms=now_ms)
        if xy is None:
            gaze = MappedGazePoint(x=0.0, y=0.0, valid=False)
        else:
            gaze = MappedGazePoint(x=float(xy[0]), y=float(xy[1]), valid=True)

        layout_keys = getattr(h, "_layout_keys", None) or []
        if not layout_keys:
            try:
                h._keyboard_layout_builder.export_keyboard_layout()
                layout_keys = getattr(h, "_layout_keys", None) or []
            except Exception:
                layout_keys = []

        frame_result = runtime.on_mapped_gaze(gaze, dt, layout_keys)
        h._update_dwell_visuals(frame_result)

        # Tools preview overlay may still show the mapped point; product typing
        # does not require preview mode.
        if h._preview_mode:
            if gaze.valid:
                h._update_gaze_preview_dot(gaze.x, gaze.y)
            else:
                h._hide_preview_dot()

    def process_gaze_preview(self, eye_data, dt: float) -> None:
        """Read-only gaze dot — no typing or text buffer updates."""
        del dt
        h = self._host
        now_ms = int(time.time() * 1000)
        xy = h._preview_mapped_screen_xy(eye_data, now_ms=now_ms)
        if xy is None:
            h._hide_preview_dot()
            return
        mapped_x, mapped_y = xy
        raw_global = None
        dbg_label = ""
        if h._rt2_debug and h._gaze_mapper is not None:
            gaze_x, gaze_y, _pre = h._map_gaze_screen_xy(eye_data, now_ms=now_ms)
            dbg_label = (
                f"mapper={getattr(h._gaze_mapper, 'mapper_type', '?')} "
                f"mapped=({mapped_x:.0f},{mapped_y:.0f})"
            )
            if gaze_x is not None and gaze_y is not None:
                raw_global = (float(gaze_x), float(gaze_y))
                dbg_label += f" gaze_smooth=({gaze_x:.0f},{gaze_y:.0f})"
        h._update_gaze_preview_dot(
            mapped_x,
            mapped_y,
            label=dbg_label,
            raw_global=raw_global,
            show_raw=bool(h._rt2_debug and raw_global is not None),
        )
