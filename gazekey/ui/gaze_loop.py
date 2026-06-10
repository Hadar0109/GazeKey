"""Gaze eye-data dispatch: calibration, preview, benchmark, dormant typing (T049)."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from gazekey.features import FeatureExtractor
from gazekey.future import score_keys
from gazekey.mapping.typing_candidate import (
    INTENT_CROSS_ROW_PENALTY,
    INTENT_ROW_STICKINESS,
    INTENT_SIGMA_PX,
    INTENT_SIGMA_Y_PX,
)
from gazekey.ui.mapper_runtime import MapperRuntime

if TYPE_CHECKING:
    from gazekey.ui.virtual_keyboard import VirtualKeyboard


class GazeLoopController:
    """Routes per-frame eye data to calibration, preview, benchmark, or typing paths."""

    def __init__(self, host: VirtualKeyboard) -> None:
        self._host = host
        self._last_tick_time = time.perf_counter()

    def on_eye_data_main_thread(self, eye_data) -> None:
        """Main-thread handler for eye data (via TrackingBridge signal)."""
        h = self._host
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if (
            h.tracking_manager
            and h.camera_preview_window
            and not h._is_calibrating
        ):
            frame = h.tracking_manager.get_latest_frame()
            if frame is not None:
                h.camera_preview_window.update_frame(frame)

        if h.tracking_manager and not h._is_calibrating and h._gaze_mapper_v2 is not None:
            h._ensure_camera_preview(show=True)

        if h.tracking_manager:
            stats = h.tracking_manager.get_statistics()
            detection_rate = stats["detection_rate"]

            if eye_data.face_detected:
                if eye_data.left_iris_center and eye_data.right_iris_center:
                    status = f"📷 Connected ✓ | 👁 Eyes | {detection_rate}"
                    color = "#10B981"
                else:
                    status = f"📷 Connected ✓ | 👤 Face Only | {detection_rate}"
                    color = "#FBBF24"
            else:
                status = f"📷 Connected ✓ | No Face | {detection_rate}"
                color = "#F59E0B"

            if h._gaze_mapper_v2 is not None and not h._is_calibrating:
                status = f"📷 Gaze active | {detection_rate}"

            h.camera_status_label.setText(status)
            h.camera_status_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    padding: 5px;
                    font-weight: bold;
                }}
            """)

        if h._is_calibrating and h._calibration_overlay is not None:
            self._process_calibration_eye_data(eye_data, dt)
            return

        if h._keyboard_accuracy_active():
            try:
                h._process_keyboard_accuracy_debug(eye_data)
            except Exception as e:
                h._log_verbose(f"[key_accuracy] frame handler failed: {e}")
            return

        if self.gaze_preview_active():
            h._gaze_typing_controller.set_enabled(False)
            self.process_gaze_preview(eye_data, dt)
            return

        active = self.gaze_typing_active()
        h._gaze_typing_controller.set_enabled(active)
        if active:
            self.process_gaze_typing(eye_data, dt)
        else:
            h._gaze_smoother.reset()
            h._feature_smoother.reset()

    def gaze_preview_active(self) -> bool:
        h = self._host
        return (
            h.is_expanded
            and not h._is_calibrating
            and h._gaze_mapper_v2 is not None
            and h._preview_mode
            and not h._keyboard_accuracy_active()
        )

    def gaze_typing_active(self) -> bool:
        # MVP (FR-021): dwell/intent/selection disabled; preview is the validation surface.
        return False

    def _process_calibration_eye_data(self, eye_data, dt: float) -> None:
        h = self._host
        now_ms = int(time.time() * 1000)
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        if h._calib2_enable_v_ema and features.avg_v is not None:
            if h._calib2_v_ema is None:
                h._calib2_v_ema = float(features.avg_v)
            else:
                a = float(h._calib2_v_alpha)
                h._calib2_v_ema = (1.0 - a) * float(h._calib2_v_ema) + a * float(features.avg_v)
            features = MapperRuntime.with_avg(
                features, avg_h=features.avg_h, avg_v=float(h._calib2_v_ema)
            )
            if h._verbose and now_ms - h._last_calib2_log_ms >= 250:
                h._log_verbose(f"[calib2] v_ema raw_v={features.avg_v} ema_v={h._calib2_v_ema}")
        if h._calibration_v2_session is not None and h._verbose:
            if now_ms - h._last_calib2_log_ms >= 250:
                h._last_calib2_log_ms = now_ms
                idx = int(h._calibration_v2_session.target_index)
                samples_used = h._calibration_v2_session.samples_used_for_target_mean(idx)
                means_count = h._calibration_v2_session.target_means_count()
                mean_ready = h._calibration_v2_session.target_mean_ready(idx)
                gate_dbg = h._calibration_v2_session.gate.debug_metrics()
                h._log_verbose(
                    "[calib2] "
                    f"t={idx}/{len(h._calibration_v2_session.targets)} "
                    f"window_size={gate_dbg['window_len']} "
                    f"samples_used_for_target_mean={samples_used} "
                    f"target_mean_ready={mean_ready} "
                    f"target_means_count={means_count} "
                    f"state={gate_dbg['state']} "
                    f"avg_h={features.avg_h} avg_v={features.avg_v} "
                    f"std=({gate_dbg['std_h']:.3f},{gate_dbg['std_v']:.3f}) "
                    f"lock_ms={gate_dbg['lock_on_ms']:.0f} "
                    f"win_ms={gate_dbg['window_ms']:.0f} "
                    f"collect_ms={gate_dbg['elapsed_collect_ms']:.0f} "
                    f"reason={h._calibration_v2_session.last_reject_reason}"
                )
        h._calibration_overlay.add_features_dt(features, dt_ms=dt * 1000.0)

    def process_gaze_preview(self, eye_data, dt: float) -> None:
        """Read-only gaze dot — no intent, selection, dwell, or text buffer updates (FR-008)."""
        h = self._host
        now_ms = int(time.time() * 1000)
        xy = h._preview_mapped_screen_xy(eye_data, now_ms=now_ms)
        if xy is None:
            h._clear_v2_focus()
            h._hide_preview_dot()
            return

        mapped_x, mapped_y = xy
        raw_global = None
        dbg_label = ""
        if h._rt2_debug and h._gaze_mapper_v2 is not None:
            gaze_x, gaze_y, _pre = h._map_gaze_screen_xy(eye_data, now_ms=now_ms)
            dbg_label = (
                f"mapper={getattr(h._gaze_mapper_v2, 'mapper_type', '?')} "
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
        h._gaze_typing_controller.tick(None, None, dt)

    def process_gaze_typing(self, eye_data, dt: float) -> None:
        """Dormant path: intent → selection → activation (disabled in MVP; preserved for T052)."""
        h = self._host
        now_ms = int(time.time() * 1000)
        mapped_x, mapped_y, raw_global = h._map_gaze_screen_xy(eye_data, now_ms=now_ms)
        if mapped_x is None or mapped_y is None:
            h._clear_v2_focus()
            h._gaze_typing_controller.tick(None, None, dt)
            return

        best_id = None
        best_conf = 0.0
        second_id = None
        second_conf = 0.0
        best_row_index = None
        if mapped_x is not None and mapped_y is not None and h._intent_keys:
            scored = score_keys(
                keys=h._intent_keys,
                gaze_x=mapped_x,
                gaze_y=mapped_y,
                sigma_px=INTENT_SIGMA_PX,
                sigma_y_px=INTENT_SIGMA_Y_PX,
                focused_key_id=h._selection_policy._focused,
                row_stickiness=INTENT_ROW_STICKINESS,
                cross_row_penalty=INTENT_CROSS_ROW_PENALTY,
            )
            if scored:
                best_id = scored[0].key_id
                best_conf = float(scored[0].probability)
                for k in h._intent_keys:
                    if k.key_id == best_id:
                        best_row_index = int(k.row_index)
                        break
            if len(scored) >= 2:
                second_id = scored[1].key_id
                second_conf = float(scored[1].probability)

        velocity_px_s = None
        if mapped_x is not None and mapped_y is not None:
            if h._last_mapped_x is not None and h._last_mapped_y is not None and h._last_mapped_t is not None:
                dt_s = max(1e-6, (now_ms - h._last_mapped_t) / 1000.0)
                dx = float(mapped_x - h._last_mapped_x)
                dy = float(mapped_y - h._last_mapped_y)
                velocity_px_s = (dx * dx + dy * dy) ** 0.5 / dt_s
            h._last_mapped_x = float(mapped_x)
            h._last_mapped_y = float(mapped_y)
            h._last_mapped_t = now_ms

        state = h._selection_policy.update(
            timestamp_ms=now_ms,
            best_key_id=best_id,
            best_confidence=float(best_conf),
            second_key_id=second_id,
            second_confidence=float(second_conf),
            velocity_px_s=velocity_px_s,
            dt_s=float(dt),
            best_row_index=best_row_index,
        )

        chosen = state.focused_key_id
        if h._rt2_debug and h._rt2_debug_selection:
            h._log_verbose(
                f"[rt2] best={best_id} p={best_conf:.2f} chosen={chosen} "
                f"dwell={state.progress:.2f} act={state.should_activate}"
            )
        h._apply_v2_focus(chosen, progress=float(state.progress))
        if state.should_activate and chosen is not None:
            row = h._keys_by_id.get(chosen)
            if row is not None:
                h._on_gaze_activate_key(row.button)

        h._log_runtime_row(
            eye_data,
            mapped_x=mapped_x,
            mapped_y=mapped_y,
            row_name="",
            row_confidence=None,
        )
