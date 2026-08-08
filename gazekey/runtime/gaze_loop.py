"""Gaze eye-data dispatch: calibration and read-only preview."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from gazekey.features import FeatureExtractor
from gazekey.runtime.mapper_runtime import MapperRuntime

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class GazeLoopController:
    """Routes per-frame eye data to calibration or read-only preview."""

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

        if h.tracking_manager:
            stats = h.tracking_manager.get_statistics()
            detection_rate = stats["detection_rate"]
            if eye_data.face_detected and eye_data.left_iris_center and eye_data.right_iris_center:
                status = f"📷 Connected ✓ | 👁 Eyes | {detection_rate}"
                color = "#10B981"
            elif eye_data.face_detected:
                status = f"📷 Connected ✓ | 👤 Face Only | {detection_rate}"
                color = "#FBBF24"
            else:
                status = f"📷 Connected ✓ | No Face | {detection_rate}"
                color = "#F59E0B"
            if h._gaze_mapper is not None and not h._is_calibrating:
                status = f"📷 Gaze active | {detection_rate}"
            h.camera_status_label.setText(status)
            h.camera_status_label.setStyleSheet(
                f"QLabel {{ color: {color}; padding: 5px; font-weight: bold; }}"
            )

        if h._is_calibrating and h._calibration_overlay is not None:
            self._process_calibration_eye_data(eye_data, dt)
            return

        if h._devtools.benchmark_active():
            try:
                h._devtools.process_benchmark_eye_data(eye_data)
            except Exception as e:
                h._log_verbose(f"[benchmark] frame handler failed: {e}")
            return

        if self.gaze_preview_active():
            self.process_gaze_preview(eye_data, dt)

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

    def process_gaze_preview(self, eye_data, dt: float) -> None:
        """Read-only gaze dot — no typing, intent, selection, or text buffer updates."""
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
