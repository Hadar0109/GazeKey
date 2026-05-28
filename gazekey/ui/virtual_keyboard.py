"""
Virtual keyboard overlay window
"""

import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QApplication, QSizePolicy, QLineEdit,
)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QFont
from gazekey.ui.camera_preview_window import CameraPreviewWindow
from gazekey.ui.calibration_overlay import CalibrationOverlay
from gazekey.calibration import (
    TrackingBridge,
    CalibrationStore,
    gaze_ratios,
    compute_calibration_targets,
)
from gazekey.typing import (
    GazeTypingController,
    TextBufferController,
    action_from_button,
)
from gazekey.typing.gaze_smoother import GazeSmoother
from gazekey.typing.gaze_ui_mapper import map_gaze_to_typing_ui


class VirtualKeyboard(QWidget):
    """
    Transparent, always-on-top virtual keyboard overlay
    """
    
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
        self._calibration_store = CalibrationStore()
        self._gaze_mapper = None  # AffineGazeMapper when calibrated
        self._calibration_overlay: CalibrationOverlay | None = None
        self._is_calibrating = False
        self._needs_first_calibration = False
        self._locked_frame_size = None
        self._gaze_focused_button = None
        self._gaze_smoother = GazeSmoother(alpha=0.35)
        self._last_tick_time = time.perf_counter()
        self.init_ui()
        self._text_buffer = TextBufferController(self.text_display)
        self._gaze_typing_controller = GazeTypingController(
            self.main_content_widget,
            on_focus_key=self._on_gaze_focus_key,
            on_activate_key=self._on_gaze_activate_key,
        )
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
        print(f"Suggestion clicked: {suggestion} - TODO: Insert word into text")
    
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
        if key == "SHIFT":
            return
        self._text_buffer.apply_key(key, shift_active=self.shift_active)
        print(f"Key pressed: {key}")
    
    def on_calibrate_clicked(self):
        """Rerun full 5-point calibration from scratch."""
        self._gaze_mapper = None
        self._calibration_store.clear()
        if not self._ensure_tracking_started():
            return
        self._start_calibration()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._needs_first_calibration:
            self._needs_first_calibration = False
            QTimer.singleShot(0, self._start_calibration_if_needed)

    def on_app_started(self) -> None:
        """Called from main() after show(); backup for first-run calibration."""
        if self._gaze_mapper is None and not self._is_calibrating:
            if self._needs_first_calibration:
                self._needs_first_calibration = False
                QTimer.singleShot(0, self._start_calibration_if_needed)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_responsive_sizes()
        if self._gaze_mapper is not None:
            self._gaze_typing_controller.mark_keyboard_dirty()

    def _init_calibration_on_startup(self) -> None:
        """Load saved calibration or schedule first-run calibration overlay."""
        stored = self._calibration_store.load()
        if stored is not None:
            self._gaze_mapper = stored.mapper
            self._needs_first_calibration = False
            self._ensure_tracking_started()
            return
        self._needs_first_calibration = True
        print("No valid calibration — starting calibration on launch.")

    def _start_calibration_if_needed(self) -> None:
        if self._gaze_mapper is not None or self._is_calibrating:
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
            print("Eye tracking started")
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
        if not self._ensure_tracking_started():
            return

        frame_w, frame_h = self._lock_frame_size_for_calibration()
        screen = self._primary_screen_geometry()
        local_targets = compute_calibration_targets(
            0, 0, screen.width(), screen.height()
        )
        global_targets = [
            (screen.x() + tx, screen.y() + ty) for tx, ty in local_targets
        ]

        if self._calibration_overlay is not None:
            self._calibration_overlay.close()
            self._calibration_overlay = None

        self._is_calibrating = True

        self._calibration_overlay = CalibrationOverlay(
            dot_targets=local_targets,
            screen_targets=global_targets,
            frame_w=frame_w,
            frame_h=frame_h,
            on_finished=self._on_calibration_finished,
        )
        self._calibration_overlay.show()
        self._calibration_overlay.raise_()
        self._calibration_overlay.activateWindow()

    def _on_calibration_finished(self, result) -> None:
        self._is_calibrating = False
        self._calibration_overlay = None
        self._locked_frame_size = None

        if result.success and result.mapper is not None:
            self._gaze_mapper = result.mapper
            self._gaze_smoother.reset()
            self._gaze_typing_controller.mark_keyboard_dirty()
            QTimer.singleShot(150, self._gaze_typing_controller.mark_keyboard_dirty)
            self._calibration_store.save(
                result.mapper,
                result.screen_targets,
                result.iris_means,
            )
            self.camera_status_label.setText("📷 Calibration saved ✓")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    color: #10B981;
                    padding: 5px;
                    font-weight: bold;
                }
            """)
            print(result.message)
            print("Gaze tracking is active. Look at keys to type (dwell ~1.25s).")
        else:
            print(f"Calibration failed: {result.message}")

    def _on_eye_data_main_thread(self, eye_data):
        """Main-thread handler for eye data (via TrackingBridge signal)."""
        now = time.perf_counter()
        dt = now - self._last_tick_time
        self._last_tick_time = now

        if self.tracking_manager and self.camera_preview_window:
            frame = self.tracking_manager.get_latest_frame()
            if frame is not None:
                self.camera_preview_window.update_frame(frame)

        # Floating live preview in bottom-right of the screen.
        if self.tracking_manager:
            self._ensure_camera_preview()

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

            if self._gaze_mapper is not None and not self._is_calibrating:
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
            gaze = gaze_ratios(eye_data)
            if gaze is not None:
                self._calibration_overlay.add_sample_dt(gaze[0], gaze[1], dt_ms=dt * 1000.0)
            return

        active = self._gaze_typing_active()
        self._gaze_typing_controller.set_enabled(active)
        if active:
            self._process_gaze_typing(eye_data, dt)
        else:
            self._gaze_smoother.reset()

    def _gaze_typing_active(self) -> bool:
        return (
            self.is_expanded
            and not self._is_calibrating
            and self._gaze_mapper is not None
        )

    def _process_gaze_typing(self, eye_data, dt: float) -> None:
        """Map gaze to screen coords and advance dwell selection."""
        gaze = gaze_ratios(eye_data)
        if gaze is None:
            self._gaze_typing_controller.tick(None, None, dt)
            return

        sx, sy = map_gaze_to_typing_ui(
            gaze[0],
            gaze[1],
            self._gaze_mapper,
            self.keyboard_widget,
            self.calibrate_btn,
        )
        sx, sy = self._gaze_smoother.filter(sx, sy)
        self._gaze_typing_controller.tick(sx, sy, dt)

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
        print("Closing GazeKey application...")
        
        # Cleanup tracking system if active
        if self.tracking_manager:
            self.tracking_manager.cleanup()
        
        # Close camera preview window
        if self.camera_preview_window:
            self.camera_preview_window.close()
        
        QApplication.quit()

    def _ensure_camera_preview(self) -> None:
        """Create/show the floating camera preview window (bottom-right)."""
        if self.camera_preview_window is None:
            self.camera_preview_window = CameraPreviewWindow(dock="bottom_right")
        if self.is_expanded:
            if not self.camera_preview_window.isVisible():
                self.camera_preview_window.show()
            self.camera_preview_window.position_at_bottom_right()
    
    def on_shift_clicked(self, checked):
        """Handle shift toggle - updates all letter keys"""
        self.shift_active = checked
        for char, btn in self.letter_keys.items():
            if checked:
                btn.setText(char.upper())
            else:
                btn.setText(char.lower())
        print(f"Shift {'ON' if checked else 'OFF'}")
    
    def on_language_clicked(self):
        """Handle language toggle"""
        current = self.lang_btn.text()
        self.lang_btn.setText("עב" if current == "EN" else "EN")
        print(f"Language switched to: {self.lang_btn.text()}")
    
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
        print("Keyboard minimized to icon")
    
    def on_restore_clicked(self):
        """Handle restore button click - expand to full keyboard"""
        # Hide minimized icon, show main content
        self.minimized_content_widget.hide()
        self.main_content_widget.show()
        self._apply_full_keyboard_geometry()
        self.is_expanded = True
        if self.camera_preview_window:
            self.camera_preview_window.show()
            self.camera_preview_window.position_at_bottom_right()
        self._gaze_typing_controller.mark_keyboard_dirty()
        print("Keyboard restored to full view")
    
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
            print("Switched to letters layout")
        else:  # symbols
            new_layout = self.create_symbols_layout()
            self.symbols_btn.setText("ABC")
            print("Switched to symbols layout")
        
        keyboard_layout.addLayout(new_layout)
        self.current_layout = layout_type
        self._gaze_typing_controller.mark_keyboard_dirty()
    
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
