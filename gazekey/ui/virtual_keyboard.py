"""
Virtual keyboard overlay window
"""

import os
import time
from dataclasses import replace
from pathlib import Path
from typing import Optional, Tuple
import csv

import numpy as np

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QApplication, QSizePolicy, QLineEdit,
)
from PySide6.QtCore import Qt, QTimer, QPoint, QRect
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush
from gazekey.ui.camera_preview_window import CameraPreviewWindow
from gazekey.ui.calibration_controller import CalibrationController
from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.ui.gaze_preview import GazePreviewController
from gazekey.evaluation.benchmark_runner import build_benchmark_run, evaluate_benchmark_pass
from gazekey.evaluation.failure_analysis import format_failure_analysis, infer_likely_cause
from gazekey.evaluation.run_summary import RunSummaryWriter
from gazekey.mvp_log import mvp_log
from gazekey.calibration import TrackingBridge
from gazekey.calibration2.calibration_csv import CalibrationCsvLogger
from gazekey.calibration2.quality import (
    assess_fullscreen_feasibility,
    evaluate_calibration_quality,
)
from gazekey.calibration2.mapper_store import MapperStore
from gazekey.calibration2.session import CalibrationV2Result, CalibrationV2Session
from gazekey.calibration2.geometry_diagnostics import print_geometric_diagnostics
from gazekey.calibration2.targets import CalibrationTarget, keyboard_geometry_targets
from gazekey.ui.calibration_geometry_overlay import CalibrationGeometryOverlay
from gazekey.debug.keyboard_accuracy import (
    KeyAccuracyDebugCsv,
    KeyboardAccuracyEvalSession,
    default_key_accuracy_debug_path,
    predict_key_accuracy_screen_xy,
    print_accuracy_summary,
    resolve_sample_keys,
)
from gazekey.debug.keyboard_accuracy_mapper_diag import run_keyboard_accuracy_mapper_diagnostics
from gazekey.debug.keyboard_accuracy_compare import (
    compare_mapper_candidates,
    default_compare_csv_path,
    print_compare_leaderboard,
    validate_selected_mapper_matches_debug,
    write_compare_csv,
)
from gazekey.mapping.ridge import MapperCandidateReport
from gazekey.debug.runtime_key_confidence_logger import (
    RuntimeKeyConfidenceLogger,
    RuntimeLogRow,
)
from gazekey.features import FeatureExtractor
from gazekey.features.feature_types import FrameFeatures
from gazekey.mapping.base import MapperPrediction
from gazekey.layout import KeyboardLayoutCsvExporter, inspect_keyboard_layout
from gazekey.intent import score_keys
from gazekey.mapping import fit_calibration_mapper
from gazekey.calibration2.fixation_gate import FixationGateConfig
from gazekey.mapping.typing_candidate import (
    CALIB_HEAD_DRIFT_EYE_H,
    CALIB_HEAD_DRIFT_FACE_XY,
    CALIBRATION_MODE,
    FEATURE_SMOOTHER_ALPHA,
    GAZE_SMOOTHER_ALPHA,
    HALF_KEY_HEIGHT_PX,
    INTENT_CROSS_ROW_PENALTY,
    INTENT_ROW_STICKINESS,
    INTENT_SIGMA_PX,
    INTENT_SIGMA_Y_PX,
    MAX_HEAD_DRIFT_EYE_H,
    MAX_LOOCV_RMS_PX,
    MAX_OFF_SCREEN_LOOCV,
    MAX_SINGLE_TARGET_TRAIN_PX,
    MAX_TARGET_LOOCV_PX,
    MAX_TRAIN_ERROR_PX,
    MAX_VALIDATION_ERROR_PX,
    MIN_AVG_V_ROW_SEPARATION,
    MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR,
    MIN_SCREEN_Y_AVG_V_CORR,
    MIN_ALPHA,
    SELECTION_CROSS_ROW_MIN_SWITCH_MS,
    SELECTION_CROSS_ROW_SWITCH_MARGIN,
    SELECTION_MIN_SWITCH_MS,
    SELECTION_SWITCH_MARGIN,
    TYPING_CANDIDATE_ID,
)
from gazekey.selection import SelectionPolicy
from gazekey.typing import (
    GazeTypingController,
    TextBufferController,
    action_from_button,
)
from gazekey.typing.gaze_smoother import GazeSmoother
from gazekey.features.feature_smoother import PcaFeatureSmoother
from gazekey.typing.gaze_ui_mapper import letter_keys_region_rect, typing_region_rect


class VirtualKeyboard(QWidget):
    """
    Transparent, always-on-top virtual keyboard overlay
    """

    @staticmethod
    def _gazekey_verbose() -> bool:
        return os.environ.get("GAZEKEY_VERBOSE", "0").strip() == "1"

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
        self._mapper_store = MapperStore()
        self._gaze_mapper_v2 = None  # Ridge calibration v2 mapper when calibrated
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
        # Debug mode: chosen must equal best every frame.
        self._selection_policy = SelectionPolicy(
            debug_follow_best=os.environ.get("GAZEKEY_SELECTION_DEBUG", "0").strip() == "1",
            switch_margin=SELECTION_SWITCH_MARGIN,
            cross_row_switch_margin=SELECTION_CROSS_ROW_SWITCH_MARGIN,
            min_switch_ms=SELECTION_MIN_SWITCH_MS,
            cross_row_min_switch_ms=SELECTION_CROSS_ROW_MIN_SWITCH_MS,
        )
        self._last_tick_time = time.perf_counter()
        self._layout_exporter = KeyboardLayoutCsvExporter()
        self._layout_version = ""
        self._layout_export_pending = False
        self._verbose = self._gazekey_verbose()
        self._runtime_logger = RuntimeKeyConfidenceLogger(enabled=self._verbose)
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
        self._row_aware_mapping = True
        # New experimental path: PCA geometric features + ridge regression (recommended default).
        self._use_ridge_mapper = True
        # Verbose detail: GAZEKEY_VERBOSE=1 (legacy per-flag env vars still honored).
        self._rt2_debug = self._verbose or os.environ.get("GAZEKEY_GAZE_DEBUG", "0").strip() == "1"
        self._rt2_debug_pred = self._rt2_debug or os.environ.get("GAZEKEY_GAZE_DEBUG_PRED", "0").strip() == "1"
        self._rt2_debug_selection = (
            self._verbose or os.environ.get("GAZEKEY_GAZE_DEBUG_SELECTION", "0").strip() == "1"
        )
        self._calib_debug = self._verbose or os.environ.get("GAZEKEY_CALIB_DEBUG", "0").strip() == "1"
        self._keyboard_accuracy_debug = self._verbose or (
            os.environ.get("GAZEKEY_KEYBOARD_ACCURACY_DEBUG", "0").strip() == "1"
        )
        self._keyboard_accuracy_compare = self._verbose or (
            os.environ.get("GAZEKEY_KEYBOARD_ACCURACY_COMPARE", "0").strip() == "1"
        )
        self._last_mapper_candidate_reports: tuple[MapperCandidateReport, ...] = ()
        self._last_calib_samples = []
        self._keyboard_accuracy_session: KeyboardAccuracyEvalSession | None = None
        self._benchmark_mvp_run = False
        self._keyboard_accuracy_banner: QLabel | None = None
        self._keyboard_accuracy_highlight_btn = None
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
        self.init_ui()
        self._text_buffer = TextBufferController(self.text_display)
        self._gaze_preview = GazePreviewController(self.keyboard_widget)
        self._gaze_typing_controller = GazeTypingController(
            self.main_content_widget,
            on_focus_key=self._on_gaze_focus_key,
            on_activate_key=self._on_gaze_activate_key,
        )
        self._schedule_layout_export()
        self._init_calibration_on_startup()
        
    def init_ui(self):
        """Initialize the user interface"""
        # Window properties
        self.setWindowTitle("GazeKey")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self._apply_full_keyboard_geometry()
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container with background (main content view)
        self.main_content_widget = QWidget()
        self.main_content_widget.setObjectName("container")
        self.main_content_widget.setStyleSheet("""
            QWidget#container {
                background-color: #000000;
            }
        """)
        
        self._container_layout = QVBoxLayout(self.main_content_widget)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(0)
        
        # Wrap top bars in widgets so we can enforce fixed heights.
        self._control_bar_layout = self.create_control_bar()
        self._control_bar_widget = QWidget()
        self._control_bar_widget.setLayout(self._control_bar_layout)

        self._text_display_layout = self.create_text_display()
        self._text_display_widget = QWidget()
        self._text_display_widget.setLayout(self._text_display_layout)

        self._suggestion_bar_layout = self.create_suggestion_bar()
        self._suggestion_bar_widget = QWidget()
        self._suggestion_bar_widget.setLayout(self._suggestion_bar_layout)

        self._container_layout.addWidget(self._control_bar_widget, 0)
        self._container_layout.addWidget(self._text_display_widget, 0)
        self._container_layout.addWidget(self._suggestion_bar_widget, 0)
        
        # Create keyboard layout widget (so we can hide/show it for zoom)
        self.keyboard_widget = QWidget()
        self.keyboard_widget.setStyleSheet("background-color: #000000;")
        self._keyboard_layout = QVBoxLayout(self.keyboard_widget)
        self._keyboard_layout.setContentsMargins(0, 0, 0, 0)
        self._keyboard_layout.setSpacing(0)
        self._keyboard_layout.addLayout(self.create_letters_layout())
        self._container_layout.addWidget(self.keyboard_widget, 1)

        # Floating webcam preview window (bottom-right of screen).
        # Created lazily when tracking starts.
        
        # Create minimized view (hidden initially)
        self.minimized_content_widget = self.create_minimized_view()
        self.minimized_content_widget.hide()
        
        # Add both views to main layout
        main_layout.addWidget(self.main_content_widget)
        main_layout.addWidget(self.minimized_content_widget)
        
        self.setLayout(main_layout)
        self.setStyleSheet("background-color: #000000;")
        self._update_responsive_sizes()
        
    def create_control_bar(self):
        """Create the top control bar with calibrate, zoom, etc."""
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Calibrate button (prominent)
        self.calibrate_btn = QPushButton("👁 CALIBRATE")
        self.calibrate_btn.setObjectName("gazeTarget")
        self.calibrate_btn.setMinimumSize(220, 56)
        self.calibrate_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.calibrate_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF6B35;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #FF8555;
            }
            QPushButton:pressed {
                background-color: #E55A25;
            }
            QPushButton#gazeTarget[gazeFocused="true"] {
                border: 2px solid #FBBF24;
            }
            QPushButton#gazeTarget[gazeDwelling="true"] {
                border: 2px solid #10B981;
            }
        """)
        self.calibrate_btn.clicked.connect(self.on_calibrate_clicked)
        self._calibrate_btn_style_default = self.calibrate_btn.styleSheet()
        
        # Camera status label (shows if camera is connected)
        self.camera_status_label = QLabel("📷 Camera: Off")
        self.camera_status_label.setFont(QFont("Segoe UI", 9))
        self.camera_status_label.setStyleSheet("""
            QLabel {
                color: #999999;
                padding: 5px;
            }
        """)
        
        # Spacer
        layout.addWidget(self.calibrate_btn)
        layout.addWidget(self.camera_status_label)
        
        # Preview button: show mapped gaze dot without activating keys
        self.preview_btn = QPushButton("PREVIEW")
        self.preview_btn.setMinimumSize(90, 45)
        self.preview_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.preview_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(16, 185, 129, 0.12);
                color: #10B981;
                border: 1px solid rgba(16, 185, 129, 0.35);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(16, 185, 129, 0.18);
            }
            QPushButton[active="true"] {
                background-color: rgba(16, 185, 129, 0.25);
                border: 1px solid rgba(16, 185, 129, 0.6);
            }
        """)
        self.preview_btn.clicked.connect(self.on_preview_clicked)
        self.preview_btn.setEnabled(False)
        layout.addWidget(self.preview_btn)
        layout.addStretch()
        
        # Language toggle
        self.lang_btn = QPushButton("EN")
        self.lang_btn.setMinimumSize(60, 45)
        self.lang_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.lang_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.lang_btn.clicked.connect(self.on_language_clicked)
        
        # Minimize button (replaces zoom button)
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setMinimumSize(50, 45)
        self.minimize_btn.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.minimize_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.minimize_btn.clicked.connect(self.on_minimize_clicked)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setMinimumSize(50, 45)
        self.close_btn.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 0.3);
                color: #FF6B6B;
            }
        """)
        self.close_btn.clicked.connect(self.on_close_clicked)
        
        self.symbols_btn = QPushButton("?123")
        self.symbols_btn.setMinimumSize(60, 45)
        self.symbols_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.symbols_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
            }
        """)
        self.symbols_btn.clicked.connect(self.on_symbols_clicked)

        layout.addWidget(self.lang_btn)
        layout.addWidget(self.symbols_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.close_btn)
        
        return layout

    def _calibration_usable(self) -> bool:
        return self._gaze_mapper_v2 is not None

    def _set_post_calibration_controls(self, enabled: bool) -> None:
        if hasattr(self, "preview_btn"):
            self.preview_btn.setEnabled(enabled and not self._keyboard_accuracy_active())

    @staticmethod
    def _dev_benchmark_enabled() -> bool:
        return os.environ.get("GAZEKEY_DEV_BENCHMARK", "0").strip() == "1"

    def _maybe_start_dev_benchmark(self) -> None:
        """Developer-only: auto-start MVP benchmark after calibration + preview (no UI click)."""
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

    @staticmethod
    def _with_avg(features, *, avg_h, avg_v):
        # FrameFeatures is frozen; create a copy with updated averages.
        return type(features)(
            timestamp_ms=features.timestamp_ms,
            face_detected=features.face_detected,
            blink=features.blink,
            confidence=features.confidence,
            Lh=features.Lh,
            Lv=features.Lv,
            Rh=features.Rh,
            Rv=features.Rv,
            avg_h=avg_h,
            avg_v=avg_v,
            eye_box_w=features.eye_box_w,
            eye_box_h=features.eye_box_h,
            face_x=features.face_x,
            face_y=features.face_y,
        )

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._gaze_preview is not None:
            self._gaze_preview.resize_to_keyboard()
        if self._keyboard_accuracy_banner is not None:
            self._keyboard_accuracy_banner.setGeometry(
                12, 8, max(200, self.main_content_widget.width() - 24), 44
            )

    def create_text_display(self):
        """Internal text buffer display for gaze/mouse typing."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.text_display = QLineEdit()
        self.text_display.setPlaceholderText("Typed text appears here…")
        self.text_display.setReadOnly(True)
        # Keep readable but allow shrinking on small screens.
        self.text_display.setMinimumHeight(34)
        self.text_display.setFont(QFont("Segoe UI", 14))
        self.text_display.setStyleSheet("""
            QLineEdit {
                background-color: #111111;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 4px;
                padding: 6px 10px;
            }
        """)
        layout.addWidget(self.text_display)
        return layout
    
    def create_suggestion_bar(self):
        """Create the suggestion bar for future auto-complete (UI only)"""
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Store suggestion buttons for future updates
        self.suggestion_buttons = []
        
        # Placeholder suggestions (will be replaced by prediction engine later)
        placeholder_suggestions = ["word1", "word2", "word3"]
        
        for suggestion in placeholder_suggestions:
            btn = QPushButton(suggestion)
            # Suggestion bar should never force the keyboard off-screen.
            btn.setMinimumHeight(30)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Medium))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #000000;
                    color: #CCCCCC;
                    border: 1px solid #333333;
                    border-radius: 0;
                    text-align: center;
                    padding: 0px 10px;
                }
                QPushButton:hover {
                    background-color: #1A1A1A;
                    border: 1px solid #555555;
                }
                QPushButton:pressed {
                    background-color: #2A2A2A;
                    color: white;
                }
            """)
            # Connect to placeholder handler (will be replaced with real logic later)
            btn.clicked.connect(lambda checked, s=suggestion: self.on_suggestion_clicked(s))
            self.suggestion_buttons.append(btn)
            layout.addWidget(btn, 1)
        
        return layout
    
    def on_suggestion_clicked(self, suggestion):
        """Handle suggestion button click (placeholder for future auto-complete)"""
        self._log_verbose(f"Suggestion clicked: {suggestion} - TODO: Insert word into text")
    
    def create_minimized_view(self):
        """Create the minimized keyboard icon view"""
        widget = QWidget()
        widget.setObjectName("minimized_container")
        widget.setStyleSheet("""
            QWidget#minimized_container {
                background-color: rgba(30, 30, 40, 230);
                border-radius: 12px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Keyboard icon button (clickable to restore)
        self.restore_btn = QPushButton("⌨")
        self.restore_btn.setMinimumSize(80, 60)
        self.restore_btn.setFont(QFont("Segoe UI", 36))
        self.restore_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 2px solid #FBBF24;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.restore_btn.clicked.connect(self.on_restore_clicked)
        
        layout.addWidget(self.restore_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return widget
    
    def _keyboard_key_stylesheet(self):
        return """
            QPushButton#keyboardKey {
                background-color: #000000;
                color: #FFFFFF;
                border: 1px solid #333333;
                border-radius: 0;
                padding: 2px 4px;
                margin: 0;
                font-weight: 500;
                text-align: center;
            }
            QPushButton#keyboardKey:hover {
                background-color: #1A1A1A;
                border: 1px solid #555555;
            }
            QPushButton#keyboardKey:pressed {
                background-color: #2A2A2A;
                border: 1px solid #777777;
            }
            QPushButton#keyboardKey:checked {
                background-color: #333333;
                border: 1px solid #888888;
            }
            QPushButton#keyboardKey[gazeFocused="true"] {
                background-color: #1A1A1A;
                border: 2px solid #FBBF24;
            }
            QPushButton#keyboardKey[gazeDwelling="true"] {
                background-color: #2A3A1A;
                border: 2px solid #10B981;
            }
        """

    def _keyboard_row_layout(self):
        """Horizontal row with a small gap so gaze hit boxes do not overlap."""
        row = QHBoxLayout()
        row.setSpacing(int(getattr(self, "_key_gap_px", 3)))
        row.setContentsMargins(0, 0, 0, 0)
        return row

    def _add_key_row(self, parent_layout, widgets_with_stretch):
        """Add a row of keys; each item is (widget, stretch_factor)."""
        row = self._keyboard_row_layout()
        for widget, stretch in widgets_with_stretch:
            row.addWidget(widget, stretch)
        parent_layout.addLayout(row, 1)

    def create_letters_layout(self):
        """Create the main QWERTY keyboard grid (4 rows, full-width stretch)."""
        self.letter_keys.clear()
        layout = QVBoxLayout()
        layout.setSpacing(int(getattr(self, "_key_gap_px", 3)))
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 1: Q W E R T Y U I O P
        row1_keys = []
        for char in 'qwertyuiop':
            btn = self.create_key(char)
            self.letter_keys[char] = btn
            row1_keys.append((btn, 1))
        self._add_key_row(layout, row1_keys)

        # Row 2: A S D F G H J K L (indented under QWERTY)
        row2 = self._keyboard_row_layout()
        row2.addStretch(1)
        for char in 'asdfghjkl':
            btn = self.create_key(char)
            self.letter_keys[char] = btn
            row2.addWidget(btn, 1)
        row2.addStretch(1)
        layout.addLayout(row2, 1)

        # Row 3: Shift Z X C V B N M Backspace
        row3_keys = []
        self.shift_btn = self.create_key('Shift')
        self.shift_btn.setCheckable(True)
        self.shift_btn.clicked.connect(self.on_shift_clicked)
        row3_keys.append((self.shift_btn, 2))
        for char in 'zxcvbnm':
            btn = self.create_key(char)
            self.letter_keys[char] = btn
            row3_keys.append((btn, 1))
        backspace_btn = self.create_key('⌫')
        backspace_btn.clicked.connect(lambda: self.on_key_pressed('BACKSPACE'))
        row3_keys.append((backspace_btn, 2))
        self._add_key_row(layout, row3_keys)

        # Row 4: Ctrl Alt Space Enter
        ctrl_btn = self.create_key('Ctrl')
        ctrl_btn.clicked.connect(lambda: self.on_key_pressed('CTRL'))
        alt_btn = self.create_key('Alt')
        alt_btn.clicked.connect(lambda: self.on_key_pressed('ALT'))
        space_btn = self.create_key('Space')
        space_btn.clicked.connect(lambda: self.on_key_pressed(' '))
        enter_btn = self.create_key('↵')
        enter_btn.clicked.connect(lambda: self.on_key_pressed('ENTER'))
        self._add_key_row(layout, [
            (ctrl_btn, 1),
            (alt_btn, 1),
            (space_btn, 5),
            (enter_btn, 2),
        ])

        return layout

    def create_symbols_layout(self):
        """Create the symbols keyboard grid (same 4-row structure as letters)."""
        layout = QVBoxLayout()
        layout.setSpacing(int(getattr(self, "_key_gap_px", 3)))
        layout.setContentsMargins(0, 0, 0, 0)

        # Row 1: 1 2 3 4 5 6 7 8 9 0
        self._add_key_row(layout, [(self.create_key(n), 1) for n in '1234567890'])

        # Row 2: ! @ # $ % ^ & * ( )
        self._add_key_row(layout, [
            (self.create_key(sym), 1)
            for sym in ['!', '@', '#', '$', '%', '^', '&&', '*', '(', ')']
        ])

        # Row 3: - / : ; ' " , . + Backspace
        row3_keys = [(self.create_key(sym), 1) for sym in ['-', '/', ':', ';', "'", '"', ',', '.']]
        backspace_btn = self.create_key('⌫')
        backspace_btn.clicked.connect(lambda: self.on_key_pressed('BACKSPACE'))
        row3_keys.append((backspace_btn, 2))
        self._add_key_row(layout, row3_keys)

        # Row 4: Ctrl Alt Space Enter
        ctrl_btn = self.create_key('Ctrl')
        ctrl_btn.clicked.connect(lambda: self.on_key_pressed('CTRL'))
        alt_btn = self.create_key('Alt')
        alt_btn.clicked.connect(lambda: self.on_key_pressed('ALT'))
        space_btn = self.create_key('Space')
        space_btn.clicked.connect(lambda: self.on_key_pressed(' '))
        enter_btn = self.create_key('↵')
        enter_btn.clicked.connect(lambda: self.on_key_pressed('ENTER'))
        self._add_key_row(layout, [
            (ctrl_btn, 1),
            (alt_btn, 1),
            (space_btn, 5),
            (enter_btn, 2),
        ])

        return layout

    def create_key(self, text):
        """Create a styled keyboard key that expands to fill its grid cell."""
        btn = QPushButton(text)
        btn.setObjectName("keyboardKey")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Do not force a large min height; we scale keys to fit the window.
        btn.setMinimumHeight(24)
        btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Medium))
        btn.setStyleSheet(self._keyboard_key_stylesheet())

        special_chars = [
            ',', '.', '!', '@', '#', '$', '%', '^', '*', '(', ')',
            '-', '/', ':', ';', '?', "'", '"', '_', '+', '=',
        ]

        if len(text) == 1 and (text.isalnum() or text in special_chars):
            btn.clicked.connect(lambda checked=False, t=text: self.on_key_pressed(t))
        elif text == '&&':
            btn.clicked.connect(lambda: self.on_key_pressed('&'))

        return btn
    
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
        self._update_responsive_sizes()
        if self._gaze_mapper_v2 is not None:
            self._gaze_typing_controller.mark_keyboard_dirty()
        self._schedule_layout_export()

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
        if not self.tracking_manager:
            from gazekey.tracking.tracking_manager import TrackingManager
            self.tracking_manager = TrackingManager(camera_id=0)

        if self.tracking_manager.is_tracking:
            return True

        success = self.tracking_manager.start_tracking(
            callback=self._tracking_bridge.forward
        )
        if success:
            self.camera_status_label.setText("📷 Camera: Connected ✓")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    color: #10B981;
                    padding: 5px;
                    font-weight: bold;
                }
            """)
            self._log_verbose("Eye tracking started")
        else:
            self.camera_status_label.setText("📷 Camera: ERROR ✗")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    color: #E63946;
                    padding: 5px;
                    font-weight: bold;
                }
            """)
            print(
                "Failed to start eye tracking - check camera permissions "
                "or if another app is using the camera"
            )
        return success

    def _get_frame_size(self) -> tuple[int, int]:
        """Return (width, height) for iris pixel conversion."""
        if self._locked_frame_size is not None:
            return self._locked_frame_size
        if self.tracking_manager:
            frame = self.tracking_manager.get_latest_frame()
            if frame is not None:
                h, w = frame.shape[:2]
                return w, h
        return 640, 480

    def _lock_frame_size_for_calibration(self) -> tuple[int, int]:
        """Freeze camera dimensions for consistent iris pixel scaling."""
        w, h = self._get_frame_size()
        self._locked_frame_size = (w, h)
        return w, h

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
            self._export_keyboard_layout()
        except Exception:
            pass

        if self._calibration_overlay is not None:
            self._calibration_overlay.close()
            self._calibration_overlay = None

        self._is_calibrating = True
        self._calib2_v_ema = None
        self._reset_calibration_debug_csvs()

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

    def _write_calibration_run_summary(
        self,
        *,
        passed: bool,
        failure_reason: Optional[str] = None,
        loocv_rms_px: Optional[float] = None,
        quality_warnings: Optional[list[str]] = None,
    ) -> None:
        session = self._calibration_v2_session
        if session is None:
            return
        collected = sum(
            1 for i in range(len(session.targets)) if session.accepted_count_for_target(i) > 0
        )
        self._run_summary_writer.write_calibration_summary(
            session_id=self._calibration_controller.session_id or session.csv.session_id,
            status="passed" if passed else "failed",
            layout=str(self._calib2_mode or CALIBRATION_MODE),
            targets_collected=collected,
            targets_total=len(session.targets),
            failure_reason=failure_reason,
            loocv_rms_px=loocv_rms_px,
            quality_warnings=quality_warnings,
        )

    def _on_calibration_finished(self, result) -> None:
        self._is_calibrating = False
        if self._calibration_overlay is not None:
            try:
                self._calibration_overlay.hide()
                self._calibration_overlay.close()
            except Exception:
                pass
        self._calibration_overlay = None
        self._locked_frame_size = None
        self._set_camera_preview_blocked(False)

        if not isinstance(result, CalibrationV2Result):
            self._log_verbose(f"[calib2] unexpected result type: {type(result)}")
            return

        if not result.success:
            self._log_verbose(f"[calib2] failed: {result.message}")
            self._write_calibration_run_summary(
                passed=False,
                failure_reason=result.message,
            )
            return

        if self._calibration_v2_session is None:
            self._log_verbose("[calib2] missing session at finish")
            self._write_calibration_run_summary(passed=False, failure_reason="missing_session")
            return

        # Safety: don't fit until we have at least 1 accepted sample for every target.
        missing = [
            i
            for i in range(len(self._calibration_v2_session.targets))
            if self._calibration_v2_session.accepted_count_for_target(i) <= 0
        ]
        if missing:
            self._log_verbose(f"[calib2] not fitting mapper: missing accepted samples for targets {missing}")
            self._write_calibration_run_summary(
                passed=False,
                failure_reason=f"missing_samples targets={missing}",
            )
            return

        try:
            self._calibration_v2_session.print_training_means()
        except Exception as e:
            self._log_verbose(f"[calib2] training means print failed: {e}")

        samples = self._calibration_v2_session.get_training_samples()

        # Diagnostics before fitting (feature span sanity).
        try:
            h_vals = [float(s.avg_h) for (s, _p) in samples if s.avg_h is not None]
            v_vals = [float(s.avg_v) for (s, _p) in samples if s.avg_v is not None]
            if h_vals and v_vals:
                span_h = float(max(h_vals) - min(h_vals))
                span_v = float(max(v_vals) - min(v_vals))
                self._log_verbose(f"[diag] avg_h range: {min(h_vals):.3f}-{max(h_vals):.3f} span={span_h:.3f}")
                self._log_verbose(f"[diag] avg_v range: {min(v_vals):.3f}-{max(v_vals):.3f} span={span_v:.3f}")
                self._log_verbose(f"[diag] pca features sample[0]: {samples[0][0]}")
                min_span = 0.06 if str(self._calib2_mode).startswith("keyboard") else 0.15
                if span_v < min_span or span_h < min_span:
                    self._log_verbose(
                        f"[diag] WARNING: feature span small (h={span_h:.3f} v={span_v:.3f}) "
                        f"— quality gates may fail"
                    )
        except Exception as e:
            self._log_verbose(f"[diag] pre-fit diagnostics failed: {e}")
        self._log_verbose(f"[calib2] fitting mapper with {len(samples)} target-mean samples")

        screen = QApplication.primaryScreen().geometry()
        clip_rect = getattr(self, "_calib_clip_rect", None)
        if clip_rect is not None:
            screen_rect_fit = clip_rect
            self._log_verbose(f"[calib2] mapper clip bounds: keyboard region {clip_rect}")
        else:
            screen_rect_fit = (
                float(screen.x()),
                float(screen.y()),
                float(screen.width()),
                float(screen.height()),
            )
        ridge_fit = fit_calibration_mapper(
            samples=samples,
            targets=self._calibration_v2_session.targets,
            calibration_mode=str(self._calib2_mode),
            screen_rect=screen_rect_fit,
            min_alpha=MIN_ALPHA,
            max_loocv_rms_px=MAX_LOOCV_RMS_PX,
            max_target_loocv_px=MAX_TARGET_LOOCV_PX,
            max_train_error_px=MAX_TRAIN_ERROR_PX,
            half_key_height_px=HALF_KEY_HEIGHT_PX,
        )
        self._last_calib_samples = list(samples)
        self._last_mapper_candidate_reports = tuple(
            r for r in (ridge_fit.candidate_reports or ()) if isinstance(r, MapperCandidateReport)
        )
        self._log_verbose(f"[calib2] mapper fit: success={ridge_fit.success} rms_px={ridge_fit.rms_px} msg={ridge_fit.message}")
        if not ridge_fit.success or ridge_fit.model is None:
            self._log_verbose(f"[calib2] ridge fit failed: {ridge_fit.message}")
            self._gaze_mapper_v2 = None
            self._preview_mode = False
            self._set_post_calibration_controls(False)
            self._write_calibration_run_summary(
                passed=False,
                failure_reason=ridge_fit.message,
            )
            self._show_recalibrate_prompt(
                "Calibration could not find a reliable mapper — keep head still, eyes on each dot"
            )
            return

        # Ridge diagnostics (stability / overfitting).
        try:
            feature_count = int(getattr(ridge_fit.model, "train_X", np.zeros((0, 0))).shape[1])
            sample_count = int(getattr(ridge_fit.model, "train_X", np.zeros((0, 0))).shape[0])
        except Exception:
            feature_count = 0
            sample_count = 0
        ridge_alpha = float(getattr(ridge_fit.model, "alpha", 0.0))
        ridge_train_rms = float(ridge_fit.rms_px) if ridge_fit.rms_px is not None else None

        # Ridge LOOCV diagnostics.
        ridge_per_target_err = None
        ridge_loocv_rms = None
        ridge_worst_str = None
        ridge_loocv_detail = None
        try:
            ridge_loocv_detail = ridge_fit.model.leave_one_out_detail_px()
            ridge_per_target_err = [float(d["err"]) for d in ridge_loocv_detail]
            ridge_loocv_rms = (
                float(np.sqrt(np.mean(np.array(ridge_per_target_err, dtype=np.float64) ** 2)))
                if ridge_per_target_err
                else None
            )
            if ridge_per_target_err:
                worst = sorted([(float(d["err"]), int(d["i"])) for d in ridge_loocv_detail], reverse=True)[:4]
                ridge_worst_str = ", ".join([f"T{i+1:02d}={e:.1f}px" for e, i in worst])
        except Exception as e:
            self._log_verbose(f"[calib2] ridge LOOCV compute failed: {e}")
            ridge_per_target_err = None
            ridge_loocv_rms = None
            ridge_worst_str = None
            ridge_loocv_detail = None

        self._log_verbose(
            f"[calib2] ridge diag: feature_count={feature_count} sample_count={sample_count} "
            f"alpha={ridge_alpha} training_RMS={ridge_train_rms} LOOCV_RMS={ridge_loocv_rms}"
        )

        if ridge_loocv_rms is not None:
            self._log_verbose(f"[calib2] pca_ridge: LOOCV_RMS={float(ridge_loocv_rms):.1f}px")
        else:
            self._log_verbose("[calib2] pca_ridge: LOOCV_RMS=(unavailable)")
        if ridge_worst_str:
            self._log_verbose(f"[calib2] pca_ridge: LOOCV worst targets: {ridge_worst_str}")
        # Rich LOOCV diagnostics: include target label, coords, predicted coords.
        try:
            if ridge_loocv_detail is not None and self._calibration_v2_session is not None:
                sess = self._calibration_v2_session
                # Sort by error and print top few.
                worst = sorted(ridge_loocv_detail, key=lambda d: float(d["err"]), reverse=True)[:4]
                for d in worst:
                    i = int(d["i"])
                    t = sess.targets[i] if i < len(sess.targets) else None
                    label = t.label if t is not None else "?"
                    tx = float(t.screen_x) if t is not None else float("nan")
                    ty = float(t.screen_y) if t is not None else float("nan")
                    self._log_verbose(
                        "[calib2] loocv worst: "
                        f"T{i+1:02d} label={label} "
                        f"target=({tx:.1f},{ty:.1f}) "
                        f"pred=({float(d['pred_x']):.1f},{float(d['pred_y']):.1f}) "
                        f"err={float(d['err']):.1f}px"
                    )
        except Exception as e:
            self._log_verbose(f"[calib2] loocv worst detail print failed: {e}")

        selected_type = getattr(ridge_fit.model, "mapper_type", "unknown") if ridge_fit.model else "unknown"
        self._log_verbose(f"[calib2] active_mapper={selected_type}")
        self._active_mapper = str(selected_type)
        fit = ridge_fit
        per_target_err = ridge_per_target_err
        loocv_rms = ridge_loocv_rms

        # Per-row avg_v statistics + ratio-space export for debugging vertical separation.
        try:
            self._print_row_v_stats_and_export_ratio_space()
        except Exception as e:
            self._log_verbose(f"[calib2] ratio-space stats/export failed: {e}")

        screen_rect = screen_rect_fit
        quality = evaluate_calibration_quality(
            model=ridge_fit.model,
            samples=samples,
            targets=self._calibration_v2_session.targets,
            screen_rect=screen_rect,
            calibration_mode=str(self._calib2_mode),
            loocv_detail=ridge_loocv_detail,
            max_validation_error_px=MAX_VALIDATION_ERROR_PX,
            max_train_error_px=MAX_TRAIN_ERROR_PX,
            max_loocv_rms_px=MAX_LOOCV_RMS_PX,
            max_target_loocv_px=MAX_TARGET_LOOCV_PX,
            max_off_screen_loocv=MAX_OFF_SCREEN_LOOCV,
            min_screen_y_avg_v_corr=MIN_SCREEN_Y_AVG_V_CORR,
            min_catastrophic_screen_y_avg_v_corr=MIN_CATASTROPHIC_SCREEN_Y_AVG_V_CORR,
            max_single_target_train_px=MAX_SINGLE_TARGET_TRAIN_PX,
            max_head_drift_eye_h=MAX_HEAD_DRIFT_EYE_H,
            min_avg_v_row_separation=MIN_AVG_V_ROW_SEPARATION,
        )
        try:
            assess_fullscreen_feasibility(
                row_stats=quality.row_stats,
                monotonicity=quality.monotonicity,
                loocv_rms_px=quality.loocv_rms_px,
            )
        except Exception as e:
            self._log_verbose(f"[calib2] feasibility assessment failed: {e}")

        try:
            print_geometric_diagnostics(
                model=ridge_fit.model,
                samples=samples,
                targets=self._calibration_v2_session.targets,
                loocv_detail=ridge_loocv_detail,
                keys=self._intent_keys or inspect_keyboard_layout(self.keyboard_widget),
            )
        except Exception as e:
            self._log_verbose(f"[calib2] geometric diagnostics failed: {e}")

        if self._calib_debug or os.environ.get("GAZEKEY_CALIB_GEOM_DEBUG", "0").strip() == "1":
            try:
                self._show_calibration_geometry_overlay(
                    samples=samples,
                    model=ridge_fit.model,
                    loocv_detail=ridge_loocv_detail,
                )
            except Exception as e:
                self._log_verbose(f"[calib2] geometry overlay failed: {e}")

        if not quality.usable:
            mvp_log(
                "[calib2] RECALIBRATE: calibration not usable — preview/benchmark blocked",
                always=True,
            )
            gate_reason = "; ".join(quality.reasons[:3]) if quality.reasons else "calibration_not_usable"
            for reason in quality.reasons:
                self._log_verbose(f"[calib2]   reason: {reason}")
            self._gaze_mapper_v2 = None
            self._preview_mode = False
            self._set_post_calibration_controls(False)
            self._write_calibration_run_summary(
                passed=False,
                failure_reason=gate_reason,
                loocv_rms_px=quality.loocv_rms_px,
                quality_warnings=quality.warnings,
            )
            self._show_recalibrate_prompt(
                "Calibration failed — keep head still, move eyes only, then tap RECALIBRATE"
            )
            try:
                self._write_calibration_debug_csv(ridge_fit=ridge_fit, loocv_detail=ridge_loocv_detail)
                self._print_target_sample_quality()
            except Exception:
                pass
            return

        try:
            self._calibration_v2_session.write_summary(
                mapper_type=getattr(fit.model, "mapper_type", "unknown"),
                per_target_error_px=per_target_err,
                overall_rms_px=loocv_rms,
            )
        except Exception as e:
            self._log_verbose(f"[calib2] summary write failed: {e}")

        self._write_calibration_run_summary(
            passed=True,
            loocv_rms_px=quality.loocv_rms_px,
            quality_warnings=quality.warnings,
        )
        self._gaze_mapper_v2 = ridge_fit.model
        self._set_post_calibration_controls(True)
        try:
            self._mapper_store.save(
                ridge_fit.model,
                calibration_mode=str(self._calib2_mode),
                mapper_mode=str(self._mapper_mode or self._calib2_mode),
            )
        except Exception as e:
            self._log_verbose(f"[calib2] v2 mapper save failed: {e}")
        self._gaze_smoother.reset()
        self._feature_smoother.reset()
        self._gaze_bias_x = 0.0
        self._gaze_bias_y = 0.0
        self._selection_policy.reset()
        self._last_v2_pred_x = None
        self._last_v2_pred_y = None
        self._last_v2_pred_t = None
        self._gaze_typing_controller.mark_keyboard_dirty()
        QTimer.singleShot(150, self._gaze_typing_controller.mark_keyboard_dirty)

        self._reset_calibrate_button_style()
        status_suffix = " (best-effort)" if getattr(ridge_fit, "best_effort", False) else ""
        self.camera_status_label.setText(f"📷 Calibration v2 saved ✓{status_suffix}")
        self.camera_status_label.setStyleSheet("""
            QLabel {
                color: #10B981;
                padding: 5px;
                font-weight: bold;
            }
        """)
        self._log_verbose(
            f"[calib2] complete. Read-only gaze preview enabled ({TYPING_CANDIDATE_ID}: "
            f"{self._active_mapper})."
        )
        self._log_verbose("[preview] Gaze dot tracks mapped position; keys are not activated (MVP).")
        mapper_type = getattr(self._gaze_mapper_v2, "mapper_type", "unknown")
        runtime_line = (
            "[runtime] "
            f"typing_candidate={TYPING_CANDIDATE_ID} "
            f"mapper_mode={self._mapper_mode or self._calib2_mode} "
            f"active_mapper={self._active_mapper} "
            f"mapper_type={mapper_type} "
            f"LOOCV_RMS={quality.loocv_rms_px}"
        )
        if quality.screen_y_avg_v_corr is not None:
            runtime_line += f" corr(screen_y,avg_v)={float(quality.screen_y_avg_v_corr):.3f}"
        if quality.warnings:
            runtime_line += f" calibration_warnings={len(quality.warnings)}"
        self._log_verbose(runtime_line)
        for w in quality.warnings:
            self._log_verbose(f"[runtime]   warning: {w}")
        # Default to read-only preview after calibration (FR-008).
        self._preview_mode = True
        if hasattr(self, "preview_btn"):
            self.preview_btn.setProperty("active", "true")
            self.preview_btn.style().unpolish(self.preview_btn)
            self.preview_btn.style().polish(self.preview_btn)
            self.preview_btn.update()
        # Restore webcam preview window after calibration (CQ-4; user may close).
        try:
            if self.is_expanded:
                self._ensure_camera_preview(show=True)
        except Exception:
            pass

        if self._keyboard_accuracy_debug:
            try:
                self._start_keyboard_accuracy_debug()
            except Exception as e:
                self._log_verbose(f"[key_accuracy] failed to start: {e}")
        elif self._dev_benchmark_enabled():
            # Defer so preview UI is initialized before the 15-key sequence starts.
            QTimer.singleShot(150, self._maybe_start_dev_benchmark)

        try:
            self._write_calibration_debug_csv(ridge_fit=ridge_fit, loocv_detail=ridge_loocv_detail)
        except Exception as e:
            self._log_verbose(f"[calib2] calibration_debug.csv write failed: {e}")

        try:
            self._print_target_sample_quality()
        except Exception as e:
            self._log_verbose(f"[calib2] per-target sample diagnostics failed: {e}")

    def _show_calibration_geometry_overlay(self, *, samples, model, loocv_detail) -> None:
        if self._calibration_v2_session is None:
            return
        targets = self._calibration_v2_session.targets
        expected = [(float(t.screen_x), float(t.screen_y)) for t in targets]
        labels = [str(t.label) for t in targets]
        train_pred: list = []
        loocv_pred: list = []
        loocv_by_i = {int(d["i"]): d for d in (loocv_detail or [])}
        for i, (feat, _xy) in enumerate(samples):
            pred = model.predict(feat)
            train_pred.append((float(pred.x), float(pred.y)) if pred is not None else None)
            d = loocv_by_i.get(i)
            if d is not None:
                loocv_pred.append((float(d["pred_x"]), float(d["pred_y"])))
            else:
                loocv_pred.append(None)
        ov = CalibrationGeometryOverlay(
            expected=expected,
            train_pred=train_pred,
            loocv_pred=loocv_pred,
            labels=labels,
        )
        ov.show()
        ov.raise_()
        self._log_verbose("[calib2] geometry overlay shown (green=target blue=train orange=LOOCV)")

    def _reset_calibration_debug_csvs(self) -> None:
        """Remove prior-run debug CSVs; they are recreated when calibration finishes."""
        root = Path(__file__).resolve().parents[2]
        for name in ("calibration_debug.csv", "calibration_ratio_space.csv"):
            path = root / name
            try:
                if path.is_file():
                    path.unlink()
            except OSError as e:
                self._log_verbose(f"[calib2] could not reset {name}: {e}")

    def _write_calibration_debug_csv(self, *, ridge_fit, loocv_detail) -> None:
        if self._calibration_v2_session is None or ridge_fit is None or ridge_fit.model is None:
            return
        sess = self._calibration_v2_session
        model = ridge_fit.model

        # Build a fast lookup for LOOCV info by index.
        loocv_by_i = {}
        if loocv_detail:
            for d in loocv_detail:
                loocv_by_i[int(d["i"])] = d

        # Write debug CSV at repo root.
        root = Path(__file__).resolve().parents[2]
        out_path = root / "calibration_debug.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(
                [
                    "target_index",
                    "label",
                    "target_x",
                    "target_y",
                    "mean_avg_h",
                    "mean_avg_v",
                    "mean_pca_vL",
                    "mean_pca_vR",
                    "mean_face_y",
                    "mean_eye_box_h",
                    "predicted_x",
                    "predicted_y",
                    "train_error_px",
                    "loocv_error_px",
                    "sample_count",
                ]
            )

            # Training samples are in target order (one mean feature per target).
            pairs = sess.get_training_samples()
            for i, ((feat, (tx, ty))) in enumerate(pairs):
                # Training prediction (on the same point).
                pred = model.predict(feat)
                if pred is None:
                    px = py = None
                    train_err = None
                else:
                    px = float(pred.x)
                    py = float(pred.y)
                    train_err = float(np.hypot(px - float(tx), py - float(ty)))

                loocv_err = None
                if i in loocv_by_i:
                    loocv_err = float(loocv_by_i[i]["err"])

                n_raw = sess.samples_used_for_target_mean(i)

                w.writerow(
                    [
                        int(i + 1),
                        sess.targets[i].label if i < len(sess.targets) else "",
                        float(tx),
                        float(ty),
                        float(feat.avg_h) if feat.avg_h is not None else "",
                        float(feat.avg_v) if feat.avg_v is not None else "",
                        float(feat.pca_vL) if feat.pca_vL is not None else "",
                        float(feat.pca_vR) if feat.pca_vR is not None else "",
                        float(feat.face_y) if feat.face_y is not None else "",
                        float(feat.eye_box_h) if feat.eye_box_h is not None else "",
                        "" if px is None else float(px),
                        "" if py is None else float(py),
                        "" if train_err is None else float(train_err),
                        "" if loocv_err is None else float(loocv_err),
                        int(n_raw),
                    ]
                )
        self._log_verbose(f"[calib2] wrote calibration debug CSV: {out_path}")

    def _print_target_sample_quality(self) -> None:
        """Per-target sample stats to diagnose noisy targets."""
        if self._calibration_v2_session is None:
            return
        sess = self._calibration_v2_session

        def iqr_filter(values: np.ndarray) -> np.ndarray:
            values = np.asarray(values, dtype=np.float64)
            values = values[np.isfinite(values)]
            if values.size < 4:
                return values
            q1, q3 = np.percentile(values, [25, 75])
            iqr = float(q3 - q1)
            if iqr <= 1e-12:
                return values
            lo = float(q1 - 1.5 * iqr)
            hi = float(q3 + 1.5 * iqr)
            m = (values >= lo) & (values <= hi)
            kept = values[m]
            return kept if kept.size else values

        max_std = float(getattr(sess.gate.cfg, "max_std", 0.045))
        for i, t in enumerate(sess.targets):
            # Accepted ratio frames used for the target mean.
            ratios = sess._accepted_ratios[i]  # noqa: SLF001
            hs = np.array([p[0] for p in ratios], dtype=np.float64) if ratios else np.array([], dtype=np.float64)
            vs = np.array([p[1] for p in ratios], dtype=np.float64) if ratios else np.array([], dtype=np.float64)
            hs_f = iqr_filter(hs)
            vs_f = iqr_filter(vs)

            raw_n = int(hs.size)
            filt_n = int(min(hs_f.size, vs_f.size))
            if raw_n > 0:
                mu_h = float(np.mean(hs))
                mu_v = float(np.mean(vs))
                sd_h = float(np.std(hs))
                sd_v = float(np.std(vs))
                noisy = bool(max(sd_h, sd_v) > max_std)
            else:
                mu_h = mu_v = sd_h = sd_v = 0.0
                noisy = True

            self._log_verbose(
                "[calib2] target samples: "
                f"T{i+1:02d} label={t.label} "
                f"raw_n={raw_n} filt_n={filt_n} "
                f"avg_h(mean={mu_h:.4f} std={sd_h:.4f}) "
                f"avg_v(mean={mu_v:.4f} std={sd_v:.4f}) "
                f"noisy={noisy}"
            )

    def _keyboard_accuracy_active(self) -> bool:
        return self._keyboard_accuracy_session is not None and not self._keyboard_accuracy_session.finished

    def _ensure_keyboard_accuracy_banner(self) -> None:
        if self._keyboard_accuracy_banner is not None:
            return
        banner = QLabel(self.main_content_widget)
        banner.setObjectName("keyboardAccuracyBanner")
        banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        banner.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        banner.setStyleSheet(
            """
            QLabel#keyboardAccuracyBanner {
                background-color: rgba(15, 23, 42, 230);
                color: #FBBF24;
                border: 2px solid #FBBF24;
                border-radius: 6px;
                padding: 8px 12px;
            }
            """
        )
        banner.setGeometry(12, 8, max(200, self.main_content_widget.width() - 24), 44)
        banner.raise_()
        self._keyboard_accuracy_banner = banner

    def _update_keyboard_accuracy_banner(self, text: str) -> None:
        self._ensure_keyboard_accuracy_banner()
        if self._keyboard_accuracy_banner is not None:
            self._keyboard_accuracy_banner.setText(str(text))
            self._keyboard_accuracy_banner.show()
            self._keyboard_accuracy_banner.raise_()

    def _hide_keyboard_accuracy_banner(self) -> None:
        if self._keyboard_accuracy_banner is not None:
            self._keyboard_accuracy_banner.hide()

    def _clear_keyboard_accuracy_highlight(self) -> None:
        if self._keyboard_accuracy_highlight_btn is not None:
            self._set_key_gaze_style(self._keyboard_accuracy_highlight_btn, False, 0.0)
        self._keyboard_accuracy_highlight_btn = None

    def _highlight_keyboard_accuracy_target(self, button) -> None:
        self._clear_keyboard_accuracy_highlight()
        if button is None:
            return
        self._keyboard_accuracy_highlight_btn = button
        self._set_key_gaze_style(button, True, 1.0, dwelling=True)

    def _benchmark_session_id(self) -> str:
        session = self._calibration_v2_session
        base = ""
        if session is not None:
            base = self._calibration_controller.session_id or session.csv.session_id
        if not base:
            base = "unknown"
        return f"{base}-bench{int(time.time())}"

    def _begin_key_accuracy_session(self, *, mvp_benchmark: bool) -> bool:
        if self._gaze_mapper_v2 is None:
            tag = "benchmark" if mvp_benchmark else "key_accuracy"
            self._log_verbose(f"[{tag}] skipped: no v2 mapper loaded")
            return False
        self._export_keyboard_layout()
        if not self._intent_keys:
            tag = "benchmark" if mvp_benchmark else "key_accuracy"
            self._log_verbose(f"[{tag}] skipped: keyboard layout not ready")
            return False
        if self.current_layout != "letters":
            self.switch_layout("letters")
        try:
            resolved = resolve_sample_keys(self._intent_keys)
        except ValueError as e:
            tag = "benchmark" if mvp_benchmark else "key_accuracy"
            self._log_verbose(f"[{tag}] {e}")
            return False

        self._benchmark_mvp_run = bool(mvp_benchmark)
        self._set_post_calibration_controls(False)
        self._preview_mode = True
        if hasattr(self, "preview_btn"):
            self.preview_btn.setProperty("active", "true")
            self.preview_btn.style().unpolish(self.preview_btn)
            self.preview_btn.style().polish(self.preview_btn)
            self.preview_btn.update()
        self._clear_v2_focus()
        self._gaze_smoother.reset()
        self._feature_smoother.reset()

        self._keyboard_accuracy_session = KeyboardAccuracyEvalSession(
            resolved,
            keys_for_hit_test=self._intent_keys,
            predict_screen_xy=self._key_accuracy_predict_screen_xy,
            on_collect_begin=lambda: self._feature_smoother.reset(),
        )
        now_ms = int(time.time() * 1000)
        self._keyboard_accuracy_session.begin(now_ms)
        cur = self._keyboard_accuracy_session.current_sample()
        if cur is not None:
            _label, row = cur
            self._highlight_keyboard_accuracy_target(row.button)
        self._update_keyboard_accuracy_banner(self._keyboard_accuracy_session.instruction_text())
        return True

    def _start_mvp_benchmark(self) -> None:
        if not self._begin_key_accuracy_session(mvp_benchmark=True):
            return
        self._log_verbose("[benchmark] started — dev MVP benchmark (15 keys, GAZEKEY_DEV_BENCHMARK=1)")

    def _start_keyboard_accuracy_debug(self) -> None:
        if not self._begin_key_accuracy_session(mvp_benchmark=False):
            return
        self._log_verbose(
            f"[key_accuracy] started — CSV -> {default_key_accuracy_debug_path()}"
        )

    def _finish_mvp_benchmark(self, rows) -> None:
        run = build_benchmark_run(rows)
        passed, reason = evaluate_benchmark_pass(run.metrics)
        status = "passed" if passed else "failed"
        likely_cause = infer_likely_cause(rows) if status == "failed" else "none"
        analysis = format_failure_analysis(rows, likely_cause=likely_cause)
        self._log_verbose(analysis)
        self._run_summary_writer.write_benchmark_summary(
            session_id=self._benchmark_session_id(),
            metrics=run.metrics,
            status=status,
            failure_reason=reason or None,
            failure_analysis=analysis,
        )

    def _finish_keyboard_accuracy_debug(self) -> None:
        session = self._keyboard_accuracy_session
        if session is None:
            return
        rows = session.results
        mvp = bool(self._benchmark_mvp_run)
        if mvp:
            self._finish_mvp_benchmark(rows)
        else:
            try:
                KeyAccuracyDebugCsv().write(rows, overwrite=True)
                self._log_verbose(f"[key_accuracy] wrote {len(rows)} rows to {default_key_accuracy_debug_path()}")
            except Exception as e:
                self._log_verbose(f"[key_accuracy] CSV write failed: {e}")
            print_accuracy_summary(rows)
            if session.recorded_gaze and self._last_calib_samples and self._calibration_v2_session is not None:
                run_keyboard_accuracy_mapper_diagnostics(
                    recorded=session.recorded_gaze,
                    keys=self._intent_keys,
                    model=self._gaze_mapper_v2,
                    calib_samples=self._last_calib_samples,
                    calib_targets=self._calibration_v2_session.targets,
                    gaze_bias_x=float(self._gaze_bias_x),
                    gaze_bias_y=float(self._gaze_bias_y),
                    clamp_xy=self._clamp_v2_xy,
                    feature_smoother_alpha=float(self._feature_smoother.alpha),
                )
            if self._keyboard_accuracy_compare and session.recorded_gaze:
                self._run_keyboard_accuracy_mapper_compare(session)
        self._benchmark_mvp_run = False
        self._keyboard_accuracy_session = None
        self._clear_keyboard_accuracy_highlight()
        self._hide_keyboard_accuracy_banner()
        self._reset_preview_overlay()
        self._preview_mode = True
        self._set_post_calibration_controls(True)
        if hasattr(self, "preview_btn"):
            self.preview_btn.setProperty("active", "true")
            self.preview_btn.style().unpolish(self.preview_btn)
            self.preview_btn.style().polish(self.preview_btn)
            self.preview_btn.update()

    def _process_keyboard_accuracy_debug(self, eye_data) -> None:
        session = self._keyboard_accuracy_session
        if session is None:
            return
        now_ms = int(time.time() * 1000)
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        xy = self._preview_mapped_screen_xy(eye_data, now_ms=now_ms)
        if xy is not None:
            px, py = xy
            self._update_gaze_preview_dot(px, py)
        else:
            self._hide_preview_dot()

        completed = session.tick(now_ms, features=features)
        log_tag = "benchmark" if self._benchmark_mvp_run else "key_accuracy"
        if completed is not None:
            self._log_verbose(
                f"[{log_tag}] {completed.target_key}: "
                f"pred=({completed.predicted_x:.1f},{completed.predicted_y:.1f}) "
                f"key={completed.predicted_key} err={completed.error_px:.1f}px "
                f"correct={completed.is_correct}"
            )

        if session.finished:
            self._finish_keyboard_accuracy_debug()
            return

        cur = session.current_sample()
        if cur is not None:
            _label, row = cur
            self._highlight_keyboard_accuracy_target(row.button)
        banner = session.instruction_text()
        if self._benchmark_mvp_run:
            banner = banner.replace("Look at key:", "Benchmark — look at:")
            if banner.endswith("complete"):
                banner = "Benchmark complete"
        self._update_keyboard_accuracy_banner(banner)

    def _key_accuracy_predict_screen_xy(self, raw) -> Optional[Tuple[float, float]]:
        """Shared keyboard-accuracy predict path (live session + compare replay)."""
        if self._gaze_mapper_v2 is None:
            return None
        return predict_key_accuracy_screen_xy(
            raw,
            model=self._gaze_mapper_v2,
            feature_smoother=self._feature_smoother,
            gaze_bias_x=float(self._gaze_bias_x),
            gaze_bias_y=float(self._gaze_bias_y),
            clamp_xy=self._clamp_v2_xy,
            min_quality=float(self._rt2_min_quality),
        )

    def _run_keyboard_accuracy_mapper_compare(self, session: KeyboardAccuracyEvalSession) -> None:
        if not self._last_mapper_candidate_reports:
            self._log_verbose("[key_accuracy_compare] skipped: no candidate reports from last fit")
            return
        if self._calibration_v2_session is None:
            return
        recorded = list(session.recorded_gaze)
        if not recorded:
            self._log_verbose("[key_accuracy_compare] skipped: no recorded gaze features")
            return
        runtime_mapper_type = str(getattr(self._gaze_mapper_v2, "mapper_type", "") or "")
        self._log_verbose(
            f"[key_accuracy_compare] replaying {len(recorded)} keys across "
            f"{len(self._last_mapper_candidate_reports)} candidates"
        )
        results = compare_mapper_candidates(
            recorded=recorded,
            keys=self._intent_keys,
            candidates=self._last_mapper_candidate_reports,
            calib_samples=self._last_calib_samples,
            calib_targets=self._calibration_v2_session.targets,
            runtime_model=self._gaze_mapper_v2,
            runtime_mapper_type=runtime_mapper_type,
            gaze_bias_x=float(self._gaze_bias_x),
            gaze_bias_y=float(self._gaze_bias_y),
            clamp_xy=self._clamp_v2_xy,
            min_quality=float(self._rt2_min_quality),
        )
        path = write_compare_csv(results)
        self._log_verbose(f"[key_accuracy_compare] wrote {path}")
        print_compare_leaderboard(results)
        if runtime_mapper_type:
            try:
                validate_selected_mapper_matches_debug(
                    session.results,
                    results,
                    runtime_mapper_type,
                )
                debug_ok = sum(1 for r in session.results if r.is_correct)
                self._log_verbose(
                    f"[key_accuracy_compare] selected mapper {runtime_mapper_type} "
                    f"matches debug CSV ({debug_ok}/{len(session.results)} correct)"
                )
            except AssertionError as e:
                self._log_verbose(f"[key_accuracy_compare] WARNING: debug/compare mismatch: {e}")

    def _print_row_v_stats_and_export_ratio_space(self) -> None:
        if self._calibration_v2_session is None:
            return
        sess = self._calibration_v2_session
        # Build per-target mean (avg_h,avg_v) from accepted ratios.
        rows = []
        for i, t in enumerate(sess.targets):
            n = sess.samples_used_for_target_mean(i)
            if n <= 0:
                continue
            ratios = sess._accepted_ratios[i]  # noqa: SLF001
            hs = [p[0] for p in ratios]
            vs = [p[1] for p in ratios]
            mh = float(sum(hs) / len(hs))
            mv = float(sum(vs) / len(vs))
            rows.append((t.target_id, t.label, float(t.screen_x), float(t.screen_y), n, mh, mv))

        if not rows:
            return

        # Group by row using label hints (works for 9/13 modes).
        top = [r for r in rows if "top" in r[1]]
        mid = [r for r in rows if r[1] in {"left", "center", "right"} or ("middle" in r[1])]
        bot = [r for r in rows if "bottom" in r[1]]

        def stats(name: str, rs):
            if not rs:
                self._log_verbose(f"[calib2] avg_v row {name}: (no targets)")
                return None
            vs = np.array([r[6] for r in rs], dtype=np.float64)
            mu = float(np.mean(vs))
            sd = float(np.std(vs))
            self._log_verbose(f"[calib2] avg_v row {name}: mean={mu:.4f} std={sd:.4f} n_targets={len(rs)}")
            return mu

        mu_top = stats("top", top)
        mu_mid = stats("mid", mid)
        mu_bot = stats("bottom", bot)
        if mu_top is not None and mu_mid is not None:
            self._log_verbose(f"[calib2] avg_v separation top-mid: {abs(mu_top - mu_mid):.4f}")
        if mu_mid is not None and mu_bot is not None:
            self._log_verbose(f"[calib2] avg_v separation mid-bottom: {abs(mu_mid - mu_bot):.4f}")

        # Export ratio-space CSV for scatter plotting (Excel / Python).
        root = Path(__file__).resolve().parents[2]
        out_path = root / "calibration_ratio_space.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["session_id", "target_id", "label", "screen_x", "screen_y", "n_samples", "mean_avg_h", "mean_avg_v"])
            for (tid, label, sx, sy, n, mh, mv) in rows:
                w.writerow([sess.csv.session_id, tid, label, sx, sy, n, mh, mv])
        self._log_verbose(f"[calib2] wrote ratio-space scatter CSV: {out_path}")

    def _derive_semantic_row_rects(self):
        """Return (row_rects, row_centers_y) for the 6 semantic regions."""
        if not self._intent_keys:
            return {}, {}
        keys = list(self._intent_keys)
        # Aggregate by physical row_index -> rect union + center_y.
        phys = {}
        for k in keys:
            ys = phys.setdefault(k.row_index, {"ys": [], "x0": k.rect.left(), "x1": k.rect.right(), "y0": k.rect.top(), "y1": k.rect.bottom()})
            ys["ys"].append(float(k.center[1]))
            ys["x0"] = min(ys["x0"], k.rect.left())
            ys["x1"] = max(ys["x1"], k.rect.right())
            ys["y0"] = min(ys["y0"], k.rect.top())
            ys["y1"] = max(ys["y1"], k.rect.bottom())

        phys_rows = []
        for ridx, d in phys.items():
            cy = float(sum(d["ys"]) / max(1, len(d["ys"])))
            phys_rows.append((cy, ridx, d))
        phys_rows.sort(key=lambda t: t[0])

        # Map physical rows to semantic row names by quantized rank.
        sem_rects = {n: QRect() for n in self._row_aware_row_names}
        sem_centers_y = {}

        def sem_for_rank(rank: int) -> str:
            if len(phys_rows) <= len(self._row_aware_row_names):
                return self._row_aware_row_names[min(rank, len(self._row_aware_row_names) - 1)]
            q = int(round((rank / max(1, len(phys_rows) - 1)) * (len(self._row_aware_row_names) - 1)))
            return self._row_aware_row_names[max(0, min(len(self._row_aware_row_names) - 1, q))]

        # Union rects per semantic.
        for rank, (cy, _ridx, d) in enumerate(phys_rows):
            sem = sem_for_rank(rank)
            r = QRect(int(d["x0"]), int(d["y0"]), int(d["x1"] - d["x0"]), int(d["y1"] - d["y0"]))
            if sem_rects[sem].isNull():
                sem_rects[sem] = r
            else:
                sem_rects[sem] = sem_rects[sem].united(r)
            sem_centers_y.setdefault(sem, []).append(float(cy))

        sem_centers_y = {k: float(sum(v) / len(v)) for k, v in sem_centers_y.items() if v}
        return sem_rects, sem_centers_y

    def _on_eye_data_main_thread(self, eye_data):
        """Main-thread handler for eye data (via TrackingBridge signal)."""
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if (
            self.tracking_manager
            and self.camera_preview_window
            and not self._is_calibrating
        ):
            frame = self.tracking_manager.get_latest_frame()
            if frame is not None:
                self.camera_preview_window.update_frame(frame)

        # Floating live preview in bottom-right of the screen (post-calibration only).
        if self.tracking_manager and not self._is_calibrating and self._gaze_mapper_v2 is not None:
            self._ensure_camera_preview(show=True)

        if self.tracking_manager:
            stats = self.tracking_manager.get_statistics()
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

            if self._gaze_mapper_v2 is not None and not self._is_calibrating:
                status = f"📷 Gaze active | {detection_rate}"

            self.camera_status_label.setText(status)
            self.camera_status_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    padding: 5px;
                    font-weight: bold;
                }}
            """)

        if self._is_calibrating and self._calibration_overlay is not None:
            now_ms = int(time.time() * 1000)
            features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
            # Optional vertical-only smoothing during calibration to stabilize target means.
            if self._calib2_enable_v_ema and features.avg_v is not None:
                if self._calib2_v_ema is None:
                    self._calib2_v_ema = float(features.avg_v)
                else:
                    a = float(self._calib2_v_alpha)
                    self._calib2_v_ema = (1.0 - a) * float(self._calib2_v_ema) + a * float(features.avg_v)
                features = self._with_avg(features, avg_h=features.avg_h, avg_v=float(self._calib2_v_ema))
                if self._verbose and now_ms - self._last_calib2_log_ms >= 250:
                    self._log_verbose(f"[calib2] v_ema raw_v={features.avg_v} ema_v={self._calib2_v_ema}")
            if self._calibration_v2_session is not None and self._verbose:
                # Throttle logs to avoid overwhelming the console.
                if now_ms - self._last_calib2_log_ms >= 250:
                    self._last_calib2_log_ms = now_ms
                    idx = int(self._calibration_v2_session.target_index)
                    samples_used = self._calibration_v2_session.samples_used_for_target_mean(idx)
                    means_count = self._calibration_v2_session.target_means_count()
                    mean_ready = self._calibration_v2_session.target_mean_ready(idx)
                    gate_dbg = self._calibration_v2_session.gate.debug_metrics()
                    self._log_verbose(
                        "[calib2] "
                        f"t={idx}/{len(self._calibration_v2_session.targets)} "
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
                        f"reason={self._calibration_v2_session.last_reject_reason}"
                    )
            self._calibration_overlay.add_features_dt(features, dt_ms=dt * 1000.0)
            return

        if self._keyboard_accuracy_active():
            try:
                self._process_keyboard_accuracy_debug(eye_data)
            except Exception as e:
                self._log_verbose(f"[key_accuracy] frame handler failed: {e}")
            return

        if self._gaze_preview_active():
            self._gaze_typing_controller.set_enabled(False)
            self._process_gaze_preview(eye_data, dt)
            return

        active = self._gaze_typing_active()
        self._gaze_typing_controller.set_enabled(active)
        if active:
            self._process_gaze_typing(eye_data, dt)
        else:
            self._gaze_smoother.reset()
            self._feature_smoother.reset()

    def _gaze_preview_active(self) -> bool:
        return (
            self.is_expanded
            and not self._is_calibrating
            and self._gaze_mapper_v2 is not None
            and self._preview_mode
            and not self._keyboard_accuracy_active()
        )

    def _gaze_typing_active(self) -> bool:
        # MVP (FR-021): dwell/intent/selection disabled; preview is the validation surface.
        return False

    def _clamp_v2_xy(self, x: float, y: float) -> Tuple[float, float]:
        bounds = getattr(self._gaze_mapper_v2, "clip_bounds", None) if self._gaze_mapper_v2 else None
        if bounds is not None:
            x0, y0, x1, y1 = bounds
            return (
                float(max(x0, min(x1, x))),
                float(max(y0, min(y1, y))),
            )
        if self._rt2_clamp_to_screen:
            screen = QApplication.primaryScreen().geometry()
            return (
                float(max(float(screen.left()), min(float(screen.right()), x))),
                float(max(float(screen.top()), min(float(screen.bottom()), y))),
            )
        return x, y

    def _predict_gaze_v2(self, features: FrameFeatures) -> Optional[MapperPrediction]:
        """Smooth PCA features, predict screen point, apply optional gaze bias offset."""
        if self._gaze_mapper_v2 is None:
            return None
        smooth = self._feature_smoother.smooth(features)
        pred = self._gaze_mapper_v2.predict(smooth)
        if pred is None:
            return None
        if pred.quality is not None and float(pred.quality) < float(self._rt2_min_quality):
            return None
        px = float(pred.x) + float(self._gaze_bias_x)
        py = float(pred.y) + float(self._gaze_bias_y)
        px, py = self._clamp_v2_xy(px, py)
        return replace(pred, x=px, y=py)

    def _map_gaze_screen_xy(self, eye_data, *, now_ms: int) -> Tuple[Optional[float], Optional[float], Optional[Tuple[float, float]]]:
        """Predict and smooth gaze; returns (x, y, raw_global) or Nones."""
        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)
        mapped_x = mapped_y = None
        if self._gaze_mapper_v2 is not None:
            pred = self._predict_gaze_v2(features)
            if pred is not None:
                mapped_x = float(pred.x)
                mapped_y = float(pred.y)
                self._last_raw_mapped_x = mapped_x
                self._last_raw_mapped_y = mapped_y
                self._last_v2_pred_x = mapped_x
                self._last_v2_pred_y = mapped_y
                self._last_v2_pred_t = now_ms
                if self._rt2_debug and self._rt2_debug_pred:
                    self._log_verbose(
                        f"[rt2] pred x={mapped_x:.1f} y={mapped_y:.1f} "
                        f"q={float(pred.quality) if pred.quality is not None else 0:.2f}"
                    )
            else:
                grace_ms = 220
                if (
                    self._last_v2_pred_x is not None
                    and self._last_v2_pred_y is not None
                    and self._last_v2_pred_t is not None
                    and (now_ms - self._last_v2_pred_t) <= grace_ms
                ):
                    mapped_x = float(self._last_v2_pred_x)
                    mapped_y = float(self._last_v2_pred_y)
                else:
                    return None, None, None

        if mapped_x is None or mapped_y is None:
            return None, None, None

        raw_global = None
        if self._last_raw_mapped_x is not None and self._last_raw_mapped_y is not None:
            raw_global = (float(self._last_raw_mapped_x), float(self._last_raw_mapped_y))

        mapped_x, mapped_y = self._gaze_smoother.filter(mapped_x, mapped_y)
        return mapped_x, mapped_y, raw_global

    def _process_gaze_preview(self, eye_data, dt: float) -> None:
        """Read-only gaze dot — no intent, selection, dwell, or text buffer updates (FR-008)."""
        now_ms = int(time.time() * 1000)
        xy = self._preview_mapped_screen_xy(eye_data, now_ms=now_ms)
        if xy is None:
            self._clear_v2_focus()
            self._hide_preview_dot()
            return

        mapped_x, mapped_y = xy
        raw_global = None
        dbg_label = ""
        if self._rt2_debug and self._gaze_mapper_v2 is not None:
            gaze_x, gaze_y, _pre = self._map_gaze_screen_xy(eye_data, now_ms=now_ms)
            dbg_label = (
                f"mapper={getattr(self._gaze_mapper_v2, 'mapper_type', '?')} "
                f"mapped=({mapped_x:.0f},{mapped_y:.0f})"
            )
            if gaze_x is not None and gaze_y is not None:
                raw_global = (float(gaze_x), float(gaze_y))
                dbg_label += f" gaze_smooth=({gaze_x:.0f},{gaze_y:.0f})"
        self._update_gaze_preview_dot(
            mapped_x,
            mapped_y,
            label=dbg_label,
            raw_global=raw_global,
            show_raw=bool(self._rt2_debug and raw_global is not None),
        )
        self._gaze_typing_controller.tick(None, None, dt)

    def _process_gaze_typing(self, eye_data, dt: float) -> None:
        """Map gaze to screen coords and run intent->selection->activation (disabled in MVP)."""
        now_ms = int(time.time() * 1000)
        mapped_x, mapped_y, raw_global = self._map_gaze_screen_xy(eye_data, now_ms=now_ms)
        if mapped_x is None or mapped_y is None:
            self._clear_v2_focus()
            self._gaze_typing_controller.tick(None, None, dt)
            return

        # Intent scoring -> selection policy -> UI focus/activation.
        best_id = None
        best_conf = 0.0
        second_id = None
        second_conf = 0.0
        best_row_index = None
        if mapped_x is not None and mapped_y is not None and self._intent_keys:
            scored = score_keys(
                keys=self._intent_keys,
                gaze_x=mapped_x,
                gaze_y=mapped_y,
                sigma_px=INTENT_SIGMA_PX,
                sigma_y_px=INTENT_SIGMA_Y_PX,
                focused_key_id=self._selection_policy._focused,
                row_stickiness=INTENT_ROW_STICKINESS,
                cross_row_penalty=INTENT_CROSS_ROW_PENALTY,
            )
            if scored:
                best_id = scored[0].key_id
                best_conf = float(scored[0].probability)
                for k in self._intent_keys:
                    if k.key_id == best_id:
                        best_row_index = int(k.row_index)
                        break
            if len(scored) >= 2:
                second_id = scored[1].key_id
                second_conf = float(scored[1].probability)

        velocity_px_s = None
        if mapped_x is not None and mapped_y is not None:
            if self._last_mapped_x is not None and self._last_mapped_y is not None and self._last_mapped_t is not None:
                dt_s = max(1e-6, (now_ms - self._last_mapped_t) / 1000.0)
                dx = float(mapped_x - self._last_mapped_x)
                dy = float(mapped_y - self._last_mapped_y)
                velocity_px_s = (dx * dx + dy * dy) ** 0.5 / dt_s
            self._last_mapped_x = float(mapped_x)
            self._last_mapped_y = float(mapped_y)
            self._last_mapped_t = now_ms

        state = self._selection_policy.update(
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
        if self._rt2_debug and self._rt2_debug_selection:
            self._log_verbose(f"[rt2] best={best_id} p={best_conf:.2f} chosen={chosen} dwell={state.progress:.2f} act={state.should_activate}")
        self._apply_v2_focus(chosen, progress=float(state.progress))
        if state.should_activate and chosen is not None:
            row = self._keys_by_id.get(chosen)
            if row is not None:
                self._on_gaze_activate_key(row.button)

        # Keep debug CSV logging (now reflects actual runtime decision path).
        self._log_runtime_row(
            eye_data,
            mapped_x=mapped_x,
            mapped_y=mapped_y,
            row_name="",
            row_confidence=None,
        )

    def _schedule_layout_export(self) -> None:
        if self._layout_export_pending:
            return
        self._layout_export_pending = True
        QTimer.singleShot(0, self._export_keyboard_layout)

    def _export_keyboard_layout(self) -> None:
        self._layout_export_pending = False
        tl = self.mapToGlobal(QPoint(0, 0))
        window_rect = QRect(tl, self.size())

        try:
            region_rect = typing_region_rect(self.keyboard_widget, self.calibrate_btn)
            keys = inspect_keyboard_layout(self.main_content_widget)
            self._layout_version = self._layout_exporter.export(
                window_rect=window_rect,
                typing_region_rect=region_rect,
                keys=keys,
            )
            self._intent_keys = keys
            self._keys_by_id = {k.key_id: k for k in keys}
            # Row-aware: update semantic row assignment for keys.
            self._key_semantic_row = self._derive_key_semantic_rows(keys)
        except Exception as e:
            self._log_verbose(f"Failed to export keyboard_layout.csv: {e}")

    def _derive_key_semantic_rows(self, keys):
        """Assign each key_id to one of the 6 semantic row regions."""
        # Use the same quantized-rank logic as in `_derive_semantic_row_rects`.
        phys = {}
        for k in keys:
            ys = phys.setdefault(k.row_index, [])
            ys.append(float(k.center[1]))
        phys_rows = [(float(sum(v) / len(v)), ridx) for ridx, v in phys.items() if v]
        phys_rows.sort(key=lambda t: t[0])
        ordered = [ridx for _, ridx in phys_rows]

        def sem_for_rank(rank: int) -> str:
            if len(ordered) <= len(self._row_aware_row_names):
                return self._row_aware_row_names[min(rank, len(self._row_aware_row_names) - 1)]
            q = int(round((rank / max(1, len(ordered) - 1)) * (len(self._row_aware_row_names) - 1)))
            return self._row_aware_row_names[max(0, min(len(self._row_aware_row_names) - 1, q))]

        sem_for_phys = {}
        for rank, ridx in enumerate(ordered):
            sem_for_phys[ridx] = sem_for_rank(rank)

        return {k.key_id: sem_for_phys.get(k.row_index, "letters2") for k in keys}

    def _row_adjacent(self, row_name: str) -> list[str]:
        names = list(self._row_aware_row_names)
        if row_name not in names:
            return []
        i = names.index(row_name)
        out = []
        if i - 1 >= 0:
            out.append(names[i - 1])
        if i + 1 < len(names):
            out.append(names[i + 1])
        return out

    def _score_keys_row_weighted(self, *, gaze_x: float, gaze_y: float, row_weight: dict[str, float]):
        # Clone of `score_keys` but with an extra multiplier per semantic row.
        from math import exp
        from PySide6.QtCore import QPoint

        p = QPoint(int(gaze_x), int(gaze_y))
        sigma_px = 52.0
        hitbox_bonus = 1.35

        scored = []
        for k in self._intent_keys:
            sem = self._key_semantic_row.get(k.key_id, "letters2")
            rw = float(row_weight.get(sem, 0.0))
            if rw <= 0.0:
                continue
            cx, cy = k.center
            dx = float(gaze_x - cx)
            dy = float(gaze_y - cy)
            d = (dx * dx + dy * dy) ** 0.5
            s = exp(-0.5 * (d / sigma_px) ** 2) * float(k.weight) * rw
            if k.hitbox.contains(p):
                s *= hitbox_bonus
            scored.append((k, float(s)))

        total = sum(s for _, s in scored)
        if total <= 1e-12:
            return []
        out = [
            (k, s / total)
            for k, s in scored
        ]
        out.sort(key=lambda t: t[1], reverse=True)
        return out

    def _clear_v2_focus(self) -> None:
        if self._last_v2_focused_key_id is not None:
            row = self._keys_by_id.get(self._last_v2_focused_key_id)
            if row is not None:
                self._set_key_gaze_style(row.button, False, 0.0)
        self._last_v2_focused_key_id = None

    def _apply_v2_focus(self, key_id: str | None, *, progress: float) -> None:
        if key_id is None:
            self._clear_v2_focus()
            return
        row = self._keys_by_id.get(key_id)
        if row is None:
            self._clear_v2_focus()
            return
        if self._last_v2_focused_key_id is not None and self._last_v2_focused_key_id != key_id:
            prev = self._keys_by_id.get(self._last_v2_focused_key_id)
            if prev is not None:
                self._set_key_gaze_style(prev.button, False, 0.0)
        self._last_v2_focused_key_id = key_id
        dwelling = progress >= 0.7
        focused = progress > 0.0
        self._set_key_gaze_style(row.button, focused, progress, dwelling=dwelling)

    def _log_runtime_row(
        self,
        eye_data,
        *,
        mapped_x: float | None,
        mapped_y: float | None,
        row_name: str = "",
        row_confidence: float | None = None,
    ) -> None:
        # Throttle to ~10 Hz to avoid massive files during development.
        now_ms = int(time.time() * 1000)
        if now_ms - self._last_runtime_log_ms < 100:
            return
        self._last_runtime_log_ms = now_ms

        features = FeatureExtractor.from_eye_data(eye_data, timestamp_ms=now_ms)

        velocity_px_s = None
        if mapped_x is not None and mapped_y is not None:
            if self._last_mapped_x is not None and self._last_mapped_y is not None and self._last_mapped_t is not None:
                dt_s = max(1e-6, (now_ms - self._last_mapped_t) / 1000.0)
                dx = float(mapped_x - self._last_mapped_x)
                dy = float(mapped_y - self._last_mapped_y)
                velocity_px_s = (dx * dx + dy * dy) ** 0.5 / dt_s
            self._last_mapped_x = float(mapped_x)
            self._last_mapped_y = float(mapped_y)
            self._last_mapped_t = now_ms

        focused = self._gaze_focused_button
        focused_key_id = ""
        focused_key_label = ""
        if focused is not None:
            focused_key_label = focused.text()
            # For Phase 0, we don't have a stable per-widget key_id here yet.
            focused_key_id = focused_key_label

        best_id = None
        best_conf = 0.0
        second_id = None
        second_conf = 0.0
        if mapped_x is not None and mapped_y is not None and self._intent_keys:
            scored = score_keys(
                keys=self._intent_keys,
                gaze_x=mapped_x,
                gaze_y=mapped_y,
                sigma_px=INTENT_SIGMA_PX,
                sigma_y_px=INTENT_SIGMA_Y_PX,
                focused_key_id=self._selection_policy._focused,
                row_stickiness=INTENT_ROW_STICKINESS,
                cross_row_penalty=INTENT_CROSS_ROW_PENALTY,
            )
            if scored:
                best_id = scored[0].key_id
                best_conf = float(scored[0].probability)
            if len(scored) >= 2:
                second_id = scored[1].key_id
                second_conf = float(scored[1].probability)

        self._runtime_logger.log(
            RuntimeLogRow(
                timestamp_ms=now_ms,
                layout_version=self._layout_version,
                calibration_version=6,
                mapper_type=getattr(self._gaze_mapper_v2, "mapper_type", "none"),
                blink=features.blink,
                confidence=float(features.confidence),
                Lh=features.Lh,
                Lv=features.Lv,
                Rh=features.Rh,
                Rv=features.Rv,
                avg_h=features.avg_h,
                avg_v=features.avg_v,
                eye_box_w=features.eye_box_w,
                eye_box_h=features.eye_box_h,
                face_x=features.face_x,
                face_y=features.face_y,
                mapped_x=mapped_x,
                mapped_y=mapped_y,
                mapped_quality=None,
                row_name=str(row_name or ""),
                row_confidence=row_confidence,
                focused_key_id=focused_key_id,
                focused_key_label=focused_key_label,
                focused_confidence=1.0 if focused is not None else 0.0,
                challenger_key_id=second_id or "",
                challenger_confidence=float(second_conf),
                switch_allowed=True,
                fixation_state="dwell_v1",
                dwell_progress=float(focused.property("dwellProgress") or 0.0) if focused is not None else 0.0,
                activated_key_id="",
                velocity_px_s=velocity_px_s,
                stability_score=None,
            )
        )

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
        current = self.lang_btn.text()
        self.lang_btn.setText("עב" if current == "EN" else "EN")
        self._log_verbose(f"Language switched to: {self.lang_btn.text()}")
    
    def on_minimize_clicked(self):
        """Handle minimize button click - shrink to keyboard icon"""
        self._gaze_typing_controller.clear_focus()
        # Hide main content, show minimized icon
        self.main_content_widget.hide()
        self.minimized_content_widget.show()
        self._apply_minimized_geometry()
        self.is_expanded = False
        if self.camera_preview_window:
            self.camera_preview_window.hide()
        self._log_verbose("Keyboard minimized to icon")
    
    def on_restore_clicked(self):
        """Handle restore button click - expand to full keyboard"""
        # Hide minimized icon, show main content
        self.minimized_content_widget.hide()
        self.main_content_widget.show()
        self._apply_full_keyboard_geometry()
        self.is_expanded = True
        if self.camera_preview_window and self._gaze_mapper_v2 is not None:
            self.camera_preview_window.show_post_calibration()
        self._gaze_typing_controller.mark_keyboard_dirty()
        self._log_verbose("Keyboard restored to full view")
    
    def on_symbols_clicked(self):
        """Handle symbols toggle"""
        if self.current_layout == 'letters':
            self.switch_layout('symbols')
        else:
            self.switch_layout('letters')
    
    def switch_layout(self, layout_type):
        """Switch between letters and symbols keyboard layouts"""
        # Get the keyboard widget's layout
        keyboard_layout = self.keyboard_widget.layout()
        
        # Remove all existing items from the layout
        while keyboard_layout.count():
            item = keyboard_layout.takeAt(0)
            if item.layout():
                self.clear_layout(item.layout())
            elif item.widget():
                item.widget().deleteLater()
        
        # Create and add the new layout
        if layout_type == 'letters':
            new_layout = self.create_letters_layout()
            self.symbols_btn.setText("?123")
            self._log_verbose("Switched to letters layout")
        else:  # symbols
            new_layout = self.create_symbols_layout()
            self.symbols_btn.setText("ABC")
            self._log_verbose("Switched to symbols layout")
        
        keyboard_layout.addLayout(new_layout)
        self.current_layout = layout_type
        self._gaze_typing_controller.mark_keyboard_dirty()
        self._schedule_layout_export()
    
    def clear_layout(self, layout):
        """Recursively clear a layout and its children"""
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                    self.clear_layout(item.layout())
    
    def _primary_screen_geometry(self):
        """Return the primary screen geometry in global coordinates."""
        return QApplication.primaryScreen().geometry()

    def _primary_screen_available_geometry(self):
        """
        Return the usable primary screen geometry (excludes taskbar/docks).
        This prevents the keyboard from being pushed behind the Windows taskbar.
        """
        return QApplication.primaryScreen().availableGeometry()

    def _full_keyboard_size(self):
        """Full-width keyboard size based on available screen height."""
        screen = self._primary_screen_available_geometry()
        width = screen.width()
        # Docked keyboard height ratio of usable screen.
        # Increase this if the bottom row is still clipped on high-DPI displays.
        height_ratio = 0.62
        height = int(screen.height() * height_ratio)
        return width, height

    def _position_at_bottom(self):
        """Pin the window to the bottom edge of the primary screen."""
        screen = self._primary_screen_available_geometry()
        x = screen.x()
        y = screen.y() + screen.height() - self.height()
        self.move(x, y)

    def _position_at_top(self):
        """Dock the window to the top edge of the usable primary screen."""
        screen = self._primary_screen_available_geometry()
        x = screen.x()
        y = screen.y()
        self.move(x, y)

    def _apply_full_keyboard_geometry(self):
        """Set full keyboard size and dock it to the top of the screen."""
        width, height = self._full_keyboard_size()
        screen = self._primary_screen_available_geometry()
        # Lock the height to the requested half-screen size.
        self.setFixedHeight(min(height, screen.height()))
        # Full width.
        self.setFixedWidth(width)
        self._position_at_top()

    def _update_responsive_sizes(self) -> None:
        """
        Scale key sizes/fonts so the full keyboard fits the current window.

        Root cause fixed: the window had a fixed height while keys and toolbars had
        large minimum sizes, so the keyboard rows were clipped.
        """
        if not hasattr(self, "keyboard_widget"):
            return

        window_h = float(self.height() or 0)
        if window_h <= 0:
            return

        window_w = float(self.width() or 0)
        if window_w <= 0:
            return

        # Global spacing/margins scale (OptiKey-style tight grid, but readable).
        margin = int(max(4.0, min(14.0, window_h * 0.02)))
        gap = int(max(2.0, min(8.0, window_h * 0.01)))
        self._key_gap_px = gap

        # Apply margins/gaps to the major layout blocks.
        if hasattr(self, "_container_layout"):
            self._container_layout.setContentsMargins(margin, margin, margin, margin)
            self._container_layout.setSpacing(gap)
        if hasattr(self, "_keyboard_layout"):
            self._keyboard_layout.setContentsMargins(0, 0, 0, 0)
            self._keyboard_layout.setSpacing(gap)
        if hasattr(self, "_control_bar_layout"):
            self._control_bar_layout.setSpacing(gap)
        if hasattr(self, "_text_display_layout"):
            self._text_display_layout.setSpacing(gap)
        if hasattr(self, "_suggestion_bar_layout"):
            self._suggestion_bar_layout.setSpacing(gap)

        # Camera preview is a separate floating window now.

        # Clamp the non-keyboard UI so it cannot steal all vertical space.
        # Allocate explicit heights so the keyboard always gets the remainder.
        chrome_h = int(max(34.0, min(58.0, window_h * 0.12)))
        text_h = int(max(24.0, min(38.0, window_h * 0.08)))
        # Give suggestions enough height to look centered.
        sugg_h = int(max(26.0, min(40.0, window_h * 0.08)))

        # Control bar typography
        chrome_pt = int(max(11.0, min(18.0, chrome_h * 0.30)))
        if hasattr(self, "calibrate_btn"):
            f = self.calibrate_btn.font()
            if f.pointSize() != chrome_pt + 4:
                f.setPointSize(chrome_pt + 4)
                self.calibrate_btn.setFont(f)
        if hasattr(self, "camera_status_label"):
            f = self.camera_status_label.font()
            if f.pointSize() != max(8, chrome_pt - 2):
                f.setPointSize(max(8, chrome_pt - 2))
                self.camera_status_label.setFont(f)

        if hasattr(self, "calibrate_btn"):
            self.calibrate_btn.setMinimumHeight(chrome_h)
            self.calibrate_btn.setMaximumHeight(chrome_h)
        for attr in ("lang_btn", "symbols_btn", "minimize_btn", "close_btn"):
            if hasattr(self, attr):
                btn = getattr(self, attr)
                btn.setMinimumHeight(max(34, chrome_h - 10))
                btn.setMaximumHeight(max(34, chrome_h - 10))
                f = btn.font()
                if f.pointSize() != max(9, chrome_pt):
                    f.setPointSize(max(9, chrome_pt))
                    btn.setFont(f)

        if hasattr(self, "text_display"):
            self.text_display.setMinimumHeight(text_h)
            self.text_display.setMaximumHeight(text_h)
            f = self.text_display.font()
            if f.pointSize() != int(max(11.0, min(18.0, text_h * 0.45))):
                f.setPointSize(int(max(11.0, min(18.0, text_h * 0.45))))
                self.text_display.setFont(f)

        if hasattr(self, "suggestion_buttons"):
            for btn in self.suggestion_buttons:
                btn.setMinimumHeight(sugg_h)
                btn.setMaximumHeight(sugg_h)
                f = btn.font()
                target = int(max(10.0, min(18.0, sugg_h * 0.45)))
                if f.pointSize() != target:
                    f.setPointSize(target)
                    btn.setFont(f)

        # Determine how much vertical space the keyboard should get.
        # This avoids depending on whatever height Qt happened to assign already.
        margins_total = float(margin * 2)
        gaps_total = float(gap * 3)  # between control/text/sugg/keyboard blocks
        desired_kb_h = window_h - (margins_total + gaps_total + chrome_h + text_h + sugg_h)

        if desired_kb_h < 4 * 24:
            # If space is still tight, compress chrome further but keep keyboard visible.
            extra = (4 * 24) - desired_kb_h
            shrink = min(extra, chrome_h * 0.25)
            chrome_h = int(max(28.0, chrome_h - shrink))
            desired_kb_h = window_h - (margins_total + gaps_total + chrome_h + text_h + sugg_h)

        # Force the keyboard widget to take the remainder.
        self.keyboard_widget.setMinimumHeight(int(max(0.0, desired_kb_h)))
        self.keyboard_widget.setMaximumHeight(int(max(0.0, desired_kb_h)))

        # And force the top bar containers to their computed heights.
        for widget_attr, h in (
            ("_control_bar_widget", chrome_h),
            ("_text_display_widget", text_h),
            ("_suggestion_bar_widget", sugg_h),
        ):
            if hasattr(self, widget_attr):
                w = getattr(self, widget_attr)
                w.setMinimumHeight(int(h))
                w.setMaximumHeight(int(h))

        kb_h = float(desired_kb_h)
        if kb_h <= 0:
            return

        row_spacing = float(gap)
        rows = 4.0
        usable = max(0.0, kb_h - row_spacing * (rows - 1.0))
        row_h = usable / rows if rows > 0 else usable

        key_h = int(max(24.0, min(72.0, row_h)))
        font_pt = int(max(11.0, min(22.0, key_h * 0.42)))

        # Update all keyboard keys.
        for btn in self.keyboard_widget.findChildren(QPushButton, "keyboardKey"):
            btn.setMinimumHeight(key_h)
            btn.setMaximumHeight(key_h)
            f = btn.font()
            if f.pointSize() != font_pt:
                f.setPointSize(font_pt)
                btn.setFont(f)

        # Update suggestion buttons (if present) to avoid pushing content off-screen.
        if hasattr(self, "suggestion_buttons"):
            sug_h = int(max(26.0, min(48.0, key_h * 0.75)))
            sug_pt = int(max(10.0, min(18.0, sug_h * 0.45)))
            for btn in self.suggestion_buttons:
                btn.setMinimumHeight(sug_h)
                btn.setMaximumHeight(sug_h)
                f = btn.font()
                if f.pointSize() != sug_pt:
                    f.setPointSize(sug_pt)
                    btn.setFont(f)

    def _apply_minimized_geometry(self):
        """Small minimized icon, fixed at the bottom-right corner."""
        self.setFixedSize(120, 100)
        screen = self._primary_screen_geometry()
        margin = 20
        x = screen.x() + screen.width() - self.width() - margin
        y = screen.y() + screen.height() - self.height() - margin
        self.move(x, y)
