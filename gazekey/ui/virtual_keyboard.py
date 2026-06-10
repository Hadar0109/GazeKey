"""
Virtual keyboard overlay — thin orchestrator wiring UI controllers (T051).
"""

from typing import Optional, Tuple

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer
from gazekey.ui.camera_preview_window import CameraPreviewWindow
from gazekey.ui.calibration_controller import CalibrationController
from gazekey.ui.calibration_finish import CalibrationFinishController
from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.ui.gaze_preview import GazePreviewController
from gazekey.ui.gaze_typing_support import GazeTypingSupport
from gazekey.ui.keyboard_layout import KeyboardLayoutBuilder
from gazekey.ui.benchmark_controller import BenchmarkController
from gazekey.ui.mapper_runtime import MapperRuntime
from gazekey.ui.gaze_loop import GazeLoopController
from gazekey.ui.tracking_controller import TrackingController
from gazekey.ui.env_flags import EnvFlags, dev_benchmark_enabled
from gazekey.evaluation.run_summary import RunSummaryWriter
from gazekey.mvp_log import mvp_log
from gazekey.tracking import TrackingBridge
from gazekey.calibration2.session import CalibrationV2Session
from gazekey.mapping.ridge import MapperCandidateReport
from gazekey.features import FeatureExtractor
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperPrediction
from gazekey.layout import KeyboardLayoutCsvExporter
from gazekey.calibration2.fixation_gate import FixationGateConfig
from gazekey.mapping.typing_candidate import (
    CALIB_HEAD_DRIFT_EYE_H,
    CALIB_HEAD_DRIFT_FACE_XY,
    CALIBRATION_MODE,
    FEATURE_SMOOTHER_ALPHA,
    GAZE_SMOOTHER_ALPHA,
    SELECTION_CROSS_ROW_MIN_SWITCH_MS,
    SELECTION_CROSS_ROW_SWITCH_MARGIN,
    SELECTION_MIN_SWITCH_MS,
    SELECTION_SWITCH_MARGIN,
)
from gazekey.future import GazeTypingController, SelectionPolicy
from gazekey.typing import TextBufferController, action_from_button
from gazekey.typing.gaze_smoother import GazeSmoother
from gazekey.features.feature_smoother import PcaFeatureSmoother


class VirtualKeyboard(QWidget):
    """Transparent, always-on-top virtual keyboard — wires controllers, owns window lifecycle."""

    def _log_verbose(self, message: str) -> None:
        mvp_log(message)

    def __init__(self):
        super().__init__()
        self.shift_active = False
        self.letter_keys = {}  # Store references to letter buttons for shift toggle
        self.is_expanded = True  # Track zoom state
        self.current_layout = 'letters'  # Track current layout: 'letters' or 'symbols'
        self.tracking_manager = None
        self.camera_preview_window = None
        self._tracking_bridge = TrackingBridge()
        self._tracking_bridge.eye_data_received.connect(self._on_eye_data_main_thread)
        self._mapper_runtime = MapperRuntime(self)
        self._gaze_loop = GazeLoopController(self)
        self._tracking_controller = TrackingController(self)
        self._calibration_finish = CalibrationFinishController(self)
        self._gaze_typing_support = GazeTypingSupport(self)
        self._calibration_controller = CalibrationController()
        self._run_summary_writer = RunSummaryWriter()
        self._calibration_overlay: CalibrationOverlay | None = None
        self._calibration_v2_session: CalibrationV2Session | None = None
        self._is_calibrating = False
        self._needs_first_calibration = False
        self._locked_frame_size = None
        self._gaze_focused_button = None
        self._gaze_smoother = GazeSmoother(alpha=GAZE_SMOOTHER_ALPHA)
        self._feature_smoother = PcaFeatureSmoother(alpha=FEATURE_SMOOTHER_ALPHA)
        self._gaze_bias_x = 0.0
        self._gaze_bias_y = 0.0
        self._intent_keys = []
        self._keys_by_id = {}
        env_flags = EnvFlags.load()
        # Debug mode: chosen must equal best every frame.
        self._selection_policy = SelectionPolicy(
            debug_follow_best=env_flags.selection_debug,
            switch_margin=SELECTION_SWITCH_MARGIN,
            cross_row_switch_margin=SELECTION_CROSS_ROW_SWITCH_MARGIN,
            min_switch_ms=SELECTION_MIN_SWITCH_MS,
            cross_row_min_switch_ms=SELECTION_CROSS_ROW_MIN_SWITCH_MS,
        )
        self._layout_exporter = KeyboardLayoutCsvExporter()
        self._layout_version = ""
        self._layout_export_pending = False
        self._verbose = env_flags.verbose
        self._last_runtime_log_ms = 0
        self._last_mapped_x = None
        self._last_mapped_y = None
        self._last_mapped_t = None
        self._last_v2_pred_x = None
        self._last_v2_pred_y = None
        self._last_v2_pred_t = None
        self._last_v2_focused_key_id = None
        self._last_calib2_log_ms = 0
        self._preview_mode = False
        self._gaze_preview: GazePreviewController | None = None
        self._calib2_mode = CALIBRATION_MODE
        # Persisted "what are we using right now?" runtime labels.
        # - mapper_mode: which calibration target set / session mode we ran (e.g. "row_aware", "precision13")
        # - active_mapper: which mapper implementation we chose after fitting (e.g. "pca_ridge", "row_aware")
        self._mapper_mode: str = ""
        self._active_mapper: str = ""
        self._calib2_v_ema = None
        self._calib2_v_alpha = 0.35
        self._calib2_enable_v_ema = False
        # Phase 9 cleanup (T038, FR-007): the active path is frozen to the PCA4 ridge mapper
        # (see gazekey/mapping/typing_candidate.ACTIVE_MAPPER). The old runtime mapper-selection
        # toggles (_use_ridge_mapper / _row_aware_mapping) are removed so no experimental mapper
        # can be selected at runtime. Variant code in ridge.py is removed in Phase 10 (T043).
        # Verbose detail: GAZEKEY_VERBOSE=1 (legacy per-flag env vars still honored).
        self._rt2_debug = env_flags.rt2_debug
        self._rt2_debug_pred = env_flags.rt2_debug_pred
        self._rt2_debug_selection = env_flags.rt2_debug_selection
        self._calib_debug = env_flags.calib_debug
        self._keyboard_accuracy_debug = env_flags.keyboard_accuracy_debug
        # Phase 9 cleanup (T038, FR-007): multi-mapper comparison is an experimental
        # selection path and must stay out of the active/verbose user flow. Gate it behind
        # the explicit debug-only flag only — GAZEKEY_VERBOSE (user clarity) must not trigger it.
        self._keyboard_accuracy_compare = env_flags.keyboard_accuracy_compare
        self._last_mapper_candidate_reports: tuple[MapperCandidateReport, ...] = ()
        self._last_calib_samples = []
        self._benchmark_controller = BenchmarkController(self)
        self._last_raw_mapped_x: float | None = None
        self._last_raw_mapped_y: float | None = None
        # Runtime prediction safety.
        self._rt2_clamp_to_screen = True
        self._rt2_min_quality = 0.10
        self._row_aware_row_names = [
            "control",
            "suggestions",
            "letters1",
            "letters2",
            "letters3",
            "actions",
        ]
        self._row_aware_row_rects = {}
        self._key_semantic_row = {}
        self._keyboard_layout_builder = KeyboardLayoutBuilder(self)
        self.init_ui()
        self._text_buffer = TextBufferController(self.text_display)
        self._gaze_preview = GazePreviewController(self.keyboard_widget)
        self._gaze_typing_controller = GazeTypingController(
            self.main_content_widget,
            on_focus_key=self._on_gaze_focus_key,
            on_activate_key=self._on_gaze_activate_key,
        )
        self._keyboard_layout_builder.schedule_layout_export()
        self._init_calibration_on_startup()

    def init_ui(self):
        """Initialize the user interface (delegates to KeyboardLayoutBuilder, T046)."""
        self._keyboard_layout_builder.init_ui()

    @property
    def _gaze_mapper_v2(self):
        runtime = getattr(self, "_mapper_runtime", None)
        if runtime is None:
            return self.__dict__.get("_gaze_mapper_v2")
        return runtime.model

    @_gaze_mapper_v2.setter
    def _gaze_mapper_v2(self, value) -> None:
        runtime = getattr(self, "_mapper_runtime", None)
        if runtime is None:
            self.__dict__["_gaze_mapper_v2"] = value
        else:
            runtime.model = value

    @property
    def _mapper_store(self):
        runtime = getattr(self, "_mapper_runtime", None)
        if runtime is None:
            return self.__dict__.get("_mapper_store")
        return runtime.store

    @_mapper_store.setter
    def _mapper_store(self, value) -> None:
        runtime = getattr(self, "_mapper_runtime", None)
        if runtime is None:
            self.__dict__["_mapper_store"] = value
        else:
            runtime._store = value

    @property
    def _keyboard_accuracy_session(self):
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is None:
            return self.__dict__.get("_keyboard_accuracy_session")
        return ctrl.session

    @_keyboard_accuracy_session.setter
    def _keyboard_accuracy_session(self, value) -> None:
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is None:
            self.__dict__["_keyboard_accuracy_session"] = value
        else:
            ctrl.session = value

    @property
    def _benchmark_mvp_run(self) -> bool:
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is None:
            return bool(self.__dict__.get("_benchmark_mvp_run", False))
        return ctrl.mvp_run

    @_benchmark_mvp_run.setter
    def _benchmark_mvp_run(self, value: bool) -> None:
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is None:
            self.__dict__["_benchmark_mvp_run"] = bool(value)
        else:
            ctrl.mvp_run = bool(value)

    @property
    def _keyboard_accuracy_banner(self):
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is None:
            return self.__dict__.get("_keyboard_accuracy_banner")
        return ctrl.banner

    def _calibration_usable(self) -> bool:
        runtime = getattr(self, "_mapper_runtime", None)
        if runtime is None:
            return self.__dict__.get("_gaze_mapper_v2") is not None
        return runtime.usable()

    def _set_post_calibration_controls(self, enabled: bool) -> None:
        if hasattr(self, "preview_btn"):
            self.preview_btn.setEnabled(enabled and not self._keyboard_accuracy_active())

    @staticmethod
    def _dev_benchmark_enabled() -> bool:
        return dev_benchmark_enabled()

    def _maybe_start_dev_benchmark(self) -> None:
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is not None:
            ctrl.maybe_start_dev_benchmark()
            return
        if not self._dev_benchmark_enabled():
            return
        if not self._calibration_usable():
            self._log_verbose("[benchmark] dev auto-start blocked — calibration not usable")
            return
        if self._is_calibrating:
            self._log_verbose("[benchmark] dev auto-start blocked — calibration in progress")
            return
        if self._keyboard_accuracy_active():
            self._log_verbose("[benchmark] dev auto-start blocked — another run active")
            return
        if not self._preview_mode:
            self._log_verbose("[benchmark] dev auto-start blocked — preview not ready")
            return
        self._start_mvp_benchmark()

    def on_preview_clicked(self) -> None:
        if not self._calibration_usable():
            self._log_verbose("[preview] blocked — calibration required before preview (CQ-2)")
            return
        if self._is_calibrating or self._keyboard_accuracy_active():
            return
        self._preview_mode = not bool(self._preview_mode)
        if hasattr(self, "preview_btn"):
            self.preview_btn.setProperty("active", "true" if self._preview_mode else "false")
            self.preview_btn.style().unpolish(self.preview_btn)
            self.preview_btn.style().polish(self.preview_btn)
            self.preview_btn.update()
        if not self._preview_mode:
            self._hide_preview_dot()
            self._clear_v2_focus()

    def _hide_preview_dot(self) -> None:
        if self._gaze_preview is not None:
            self._gaze_preview.hide()

    def _reset_preview_overlay(self) -> None:
        """Clear benchmark/debug gaze state; single mapped dot on next frame."""
        if self._gaze_preview is not None:
            self._gaze_preview.clear_gaze()

    def _preview_mapped_screen_xy(self, eye_data, *, now_ms: int) -> Optional[Tuple[float, float]]:
        """Mapped point for preview — same path as benchmark hit testing (PCA4 + feature smooth)."""
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        return self._key_accuracy_predict_screen_xy(features)

    def _update_gaze_preview_dot(
        self,
        screen_x: float,
        screen_y: float,
        *,
        label: str = "",
        raw_global: Tuple[float, float] | None = None,
        show_raw: bool = False,
    ) -> None:
        """Show mapped gaze on the keyboard (read-only preview overlay)."""
        if self._gaze_preview is None:
            self._gaze_preview = GazePreviewController(self.keyboard_widget)
        self._gaze_preview.show_gaze(
            screen_x,
            screen_y,
            label=label if self._rt2_debug else "",
            raw_global=raw_global,
            show_raw=show_raw and self._rt2_debug,
        )

    def on_suggestion_clicked(self, suggestion):
        """Handle suggestion button click (placeholder for future auto-complete)"""
        # T037: buttons are disabled in MVP; guard in case a signal fires anyway.
        if not getattr(self, "suggestion_buttons", None):
            return
        self._log_verbose(f"Suggestion clicked: {suggestion} - TODO: Insert word into text")

    def on_key_pressed(self, key):
        """Handle key press from mouse or gaze dwell."""
        if self._is_calibrating or self._keyboard_accuracy_active():
            return
        if key == "SHIFT":
            return
        self._text_buffer.apply_key(key, shift_active=self.shift_active)
        self._log_verbose(f"Key pressed: {key}")
    
    def on_calibrate_clicked(self):
        """Rerun full calibration v2 from scratch."""
        self._gaze_mapper_v2 = None
        self._calibration_v2_session = None
        self._calibration_controller.reset()
        self._set_post_calibration_controls(False)
        self._reset_calibrate_button_style()
        if not self._ensure_tracking_started():
            return
        self._start_calibration()

    def _reset_calibrate_button_style(self) -> None:
        self.calibrate_btn.setText("👁 CALIBRATE")
        if getattr(self, "_calibrate_btn_style_default", None):
            self.calibrate_btn.setStyleSheet(self._calibrate_btn_style_default)

    def _show_recalibrate_prompt(self, status_message: str) -> None:
        """Highlight RECALIBRATE after failed quality gates."""
        self.calibrate_btn.setText("👁 RECALIBRATE")
        self.calibrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #E63946;
                color: white;
                border: 2px solid #FBBF24;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F04A57;
            }
        """)
        self.camera_status_label.setText(f"📷 {status_message}")
        self.camera_status_label.setStyleSheet("""
            QLabel {
                color: #E63946;
                padding: 5px;
                font-weight: bold;
            }
        """)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._needs_first_calibration:
            self._needs_first_calibration = False
            QTimer.singleShot(0, self._start_calibration_if_needed)

    def on_app_started(self) -> None:
        """Called from main() after show(); backup for first-run calibration."""
        if self._gaze_mapper_v2 is None and not self._is_calibrating:
            if self._needs_first_calibration:
                self._needs_first_calibration = False
                QTimer.singleShot(0, self._start_calibration_if_needed)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._keyboard_layout_builder.update_responsive_sizes()
        if self._gaze_preview is not None:
            self._gaze_preview.resize_to_keyboard()
        self._benchmark_controller.update_banner_geometry()
        if self._gaze_mapper_v2 is not None:
            self._gaze_typing_controller.mark_keyboard_dirty()
        self._keyboard_layout_builder.schedule_layout_export()

    def _init_calibration_on_startup(self) -> None:
        """Always calibrate on launch; calibration_v2.json is saved for inspection only."""
        self._needs_first_calibration = True
        self._log_verbose("[calib2] calibration on launch (calibration_v2.json is not loaded).")

    def _start_calibration_if_needed(self) -> None:
        if self._gaze_mapper_v2 is not None or self._is_calibrating:
            return
        if not self._ensure_tracking_started():
            return
        self._start_calibration()

    def _ensure_tracking_started(self) -> bool:
        return self._tracking_controller.ensure_started()

    def _get_frame_size(self) -> tuple[int, int]:
        return self._tracking_controller.get_frame_size()

    def _lock_frame_size_for_calibration(self) -> tuple[int, int]:
        return self._tracking_controller.lock_frame_size_for_calibration()

    def _start_calibration(self) -> None:
        self._gaze_typing_controller.clear_focus()
        self._selection_policy.reset()
        # During calibration we want ONLY the calibration overlay visible (no runtime preview dot).
        self._preview_mode = False
        try:
            if hasattr(self, "preview_btn"):
                self.preview_btn.setProperty("active", "false")
                self.preview_btn.style().unpolish(self.preview_btn)
                self.preview_btn.style().polish(self.preview_btn)
                self.preview_btn.update()
        except Exception:
            pass
        try:
            self._hide_preview_dot()
        except Exception:
            pass
        self._set_camera_preview_blocked(True)
        if not self._ensure_tracking_started():
            self._set_camera_preview_blocked(False)
            return

        _frame_w, _frame_h = self._lock_frame_size_for_calibration()
        try:
            self._keyboard_layout_builder.export_keyboard_layout()
        except Exception:
            pass

        if self._calibration_overlay is not None:
            self._calibration_overlay.close()
            self._calibration_overlay = None

        self._is_calibrating = True
        self._calib2_v_ema = None
        self._calibration_finish.reset_debug_csvs()

        ctx = self._calibration_controller.start(
            keyboard_widget=self.keyboard_widget,
            on_finished=self._on_calibration_finished,
            gate_cfg=FixationGateConfig(
                max_head_drift_face_xy=CALIB_HEAD_DRIFT_FACE_XY,
                max_head_drift_eye_h=CALIB_HEAD_DRIFT_EYE_H,
            ),
            calibration_mode=CALIBRATION_MODE,
            max_timeouts_per_target=1,
            on_timeout="retry",
        )
        self._calibration_overlay = ctx.overlay
        self._calibration_v2_session = ctx.session
        self._calib2_mode = ctx.calib_mode
        self._calib_clip_rect = ctx.calib_clip_rect
        self._mapper_mode = str(self._calib2_mode)
        self._log_verbose(f"[calib2] start: {len(ctx.session.targets)} targets mode={self._calib2_mode}")

    def _set_camera_preview_blocked(self, blocked: bool) -> None:
        if self.camera_preview_window is not None:
            self.camera_preview_window.set_calibration_blocked(blocked)

    def _on_calibration_finished(self, result) -> None:
        self._calibration_finish.on_finished(result)

    def _write_calibration_run_summary(self, **kwargs) -> None:
        self._calibration_finish.write_run_summary(**kwargs)

    def _write_calibration_coverage_diagnostic(self) -> None:
        self._calibration_finish.write_coverage_diagnostic()

    def _on_eye_data_main_thread(self, eye_data):
        """Main-thread handler for eye data (via TrackingBridge signal)."""
        loop = getattr(self, "_gaze_loop", None)
        if loop is None:
            return
        loop.on_eye_data_main_thread(eye_data)

    def _gaze_preview_active(self) -> bool:
        loop = getattr(self, "_gaze_loop", None)
        if loop is None:
            return (
                self.is_expanded
                and not self._is_calibrating
                and self._gaze_mapper_v2 is not None
                and self._preview_mode
                and not self._keyboard_accuracy_active()
            )
        return loop.gaze_preview_active()

    def _gaze_typing_active(self) -> bool:
        loop = getattr(self, "_gaze_loop", None)
        if loop is None:
            return False
        return loop.gaze_typing_active()

    def _process_gaze_preview(self, eye_data, dt: float) -> None:
        loop = getattr(self, "_gaze_loop", None)
        if loop is not None:
            loop.process_gaze_preview(eye_data, dt)

    def _process_gaze_typing(self, eye_data, dt: float) -> None:
        loop = getattr(self, "_gaze_loop", None)
        if loop is not None:
            loop.process_gaze_typing(eye_data, dt)

    def _clamp_v2_xy(self, x: float, y: float) -> Tuple[float, float]:
        return self._mapper_runtime.clamp_xy(x, y)

    def _predict_gaze_v2(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        return self._mapper_runtime.predict_gaze_v2(features)

    def _map_gaze_screen_xy(self, eye_data, *, now_ms: int) -> Tuple[Optional[float], Optional[float], Optional[Tuple[float, float]]]:
        return self._mapper_runtime.map_gaze_screen_xy(eye_data, now_ms=now_ms)

    def _schedule_layout_export(self) -> None:
        self._keyboard_layout_builder.schedule_layout_export()

    def _export_keyboard_layout(self) -> None:
        self._keyboard_layout_builder.export_keyboard_layout()

    def _derive_semantic_row_rects(self):
        return self._gaze_typing_support.derive_semantic_row_rects()

    def _derive_key_semantic_rows(self, keys):
        return self._keyboard_layout_builder.derive_key_semantic_rows(keys)

    def _row_adjacent(self, row_name: str) -> list[str]:
        return self._gaze_typing_support.row_adjacent(row_name)

    def _score_keys_row_weighted(self, *, gaze_x: float, gaze_y: float, row_weight: dict[str, float]):
        return self._gaze_typing_support.score_keys_row_weighted(
            gaze_x=gaze_x, gaze_y=gaze_y, row_weight=row_weight
        )

    def _clear_v2_focus(self) -> None:
        self._gaze_typing_support.clear_v2_focus()

    def _apply_v2_focus(self, key_id: str | None, *, progress: float) -> None:
        self._gaze_typing_support.apply_v2_focus(key_id, progress=progress)

    def _log_runtime_row(
        self,
        eye_data,
        *,
        mapped_x: float | None,
        mapped_y: float | None,
        row_name: str = "",
        row_confidence: float | None = None,
    ) -> None:
        self._gaze_typing_support.log_runtime_row(
            eye_data,
            mapped_x=mapped_x,
            mapped_y=mapped_y,
            row_name=row_name,
            row_confidence=row_confidence,
        )

    def _keyboard_accuracy_active(self) -> bool:
        ctrl = getattr(self, "_benchmark_controller", None)
        if ctrl is None:
            sess = self.__dict__.get("_keyboard_accuracy_session")
            return sess is not None and not sess.finished
        return ctrl.active()

    def _start_mvp_benchmark(self) -> None:
        self._benchmark_controller.start_mvp_benchmark()

    def _start_keyboard_accuracy_debug(self) -> None:
        self._benchmark_controller.start_keyboard_accuracy_debug()

    def _finish_mvp_benchmark(self, rows) -> None:
        self._benchmark_controller._finish_mvp_benchmark(rows)

    def _process_keyboard_accuracy_debug(self, eye_data) -> None:
        self._benchmark_controller.process_eye_data(eye_data)

    def _key_accuracy_predict_screen_xy(self, raw) -> Optional[Tuple[float, float]]:
        return self._mapper_runtime.key_accuracy_predict_screen_xy(raw)

    def _print_row_v_stats_and_export_ratio_space(self) -> None:
        self._calibration_finish.print_row_v_stats_and_export_ratio_space()

    def _write_calibration_debug_csv(self, *, ridge_fit, loocv_detail) -> None:
        self._calibration_finish.write_debug_csv(ridge_fit=ridge_fit, loocv_detail=loocv_detail)

    def _print_target_sample_quality(self) -> None:
        self._calibration_finish.print_target_sample_quality()

    def _show_calibration_geometry_overlay(self, *, samples, model, loocv_detail) -> None:
        self._calibration_finish.show_geometry_overlay(
            samples=samples, model=model, loocv_detail=loocv_detail
        )

    def _reset_calibration_debug_csvs(self) -> None:
        self._calibration_finish.reset_debug_csvs()

    def _on_gaze_focus_key(self, button, progress: float) -> None:
        if button is None:
            if self._gaze_focused_button is not None:
                self._set_key_gaze_style(self._gaze_focused_button, False, 0.0)
            self._gaze_focused_button = None
            return
        if self._gaze_focused_button is not None and self._gaze_focused_button is not button:
            self._set_key_gaze_style(self._gaze_focused_button, False, 0.0)
        self._gaze_focused_button = button
        dwelling = progress >= 0.7
        focused = progress > 0.0
        self._set_key_gaze_style(button, focused, progress, dwelling=dwelling)

    def _on_gaze_activate_key(self, button) -> None:
        if button is self.calibrate_btn:
            self.on_calibrate_clicked()
            return
        action = action_from_button(button)
        if action == "SHIFT":
            self.shift_btn.setChecked(not self.shift_btn.isChecked())
            self.on_shift_clicked(self.shift_btn.isChecked())
            return
        self.on_key_pressed(action)

    def _set_key_gaze_style(
        self,
        button,
        focused: bool,
        progress: float,
        dwelling: bool = False,
    ) -> None:
        button.setProperty("gazeFocused", focused and not dwelling)
        button.setProperty("gazeDwelling", dwelling)
        button.setProperty("dwellProgress", progress)
        style = button.style()
        style.unpolish(button)
        style.polish(button)
        button.update()
    
    def on_close_clicked(self):
        """Handle close button click - properly exit the application"""
        self._log_verbose("Closing GazeKey application...")
        
        # Cleanup tracking system if active
        if self.tracking_manager:
            self.tracking_manager.cleanup()
        
        # Close camera preview window
        if self.camera_preview_window:
            self.camera_preview_window.close()
        
        QApplication.quit()

    def _ensure_camera_preview(self, *, show: bool = False) -> None:
        """Create the floating camera preview window; show only when allowed."""
        if self._is_calibrating:
            return
        if self.camera_preview_window is None:
            self.camera_preview_window = CameraPreviewWindow(dock="bottom_right")
        if self.camera_preview_window.is_calibration_blocked:
            return
        if show and self.is_expanded and self._gaze_mapper_v2 is not None:
            self.camera_preview_window.show_post_calibration()
    
    def on_shift_clicked(self, checked):
        """Handle shift toggle - updates all letter keys"""
        self.shift_active = checked
        for char, btn in self.letter_keys.items():
            if checked:
                btn.setText(char.upper())
            else:
                btn.setText(char.lower())
        self._log_verbose(f"Shift {'ON' if checked else 'OFF'}")
    
    def on_language_clicked(self):
        """Handle language toggle"""
        if hasattr(self, "lang_btn") and not self.lang_btn.isEnabled():
            return
        current = self.lang_btn.text()
        self.lang_btn.setText("עב" if current == "EN" else "EN")
        self._log_verbose(f"Language switched to: {self.lang_btn.text()}")
    
    def on_minimize_clicked(self):
        """Handle minimize button click - shrink to keyboard icon"""
        self._gaze_typing_controller.clear_focus()
        # Hide main content, show minimized icon
        self.main_content_widget.hide()
        self.minimized_content_widget.show()
        self._keyboard_layout_builder.apply_minimized_geometry()
        self.is_expanded = False
        if self.camera_preview_window:
            self.camera_preview_window.hide()
        self._log_verbose("Keyboard minimized to icon")
    
    def on_restore_clicked(self):
        """Handle restore button click - expand to full keyboard"""
        # Hide minimized icon, show main content
        self.minimized_content_widget.hide()
        self.main_content_widget.show()
        self._keyboard_layout_builder.apply_full_keyboard_geometry()
        self.is_expanded = True
        if self.camera_preview_window and self._gaze_mapper_v2 is not None:
            self.camera_preview_window.show_post_calibration()
        self._gaze_typing_controller.mark_keyboard_dirty()
        self._log_verbose("Keyboard restored to full view")
    
    def on_symbols_clicked(self):
        """Handle symbols toggle"""
        if hasattr(self, "symbols_btn") and not self.symbols_btn.isEnabled():
            return
        if self.current_layout == 'letters':
            self._keyboard_layout_builder.switch_layout('symbols')
        else:
            self._keyboard_layout_builder.switch_layout('letters')
