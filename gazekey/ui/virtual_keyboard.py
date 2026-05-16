"""
Virtual keyboard overlay window
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QPushButton, QLabel, QApplication
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from gazekey.ui.camera_preview_window import CameraPreviewWindow


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
        self.tracking_manager = None  # Will be initialized when calibrate is clicked
        self.camera_preview_window = None  # Separate camera preview window
        self.init_ui()
        self.dragging = False
        self.drag_position = QPoint()
        
    def init_ui(self):
        """Initialize the user interface"""
        # Window properties
        self.setWindowTitle("GazeKey")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Set fixed size (increased height for suggestion bar and better visibility)
        self.setFixedSize(820, 430)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container with background (main content view)
        self.main_content_widget = QWidget()
        self.main_content_widget.setObjectName("container")
        self.main_content_widget.setStyleSheet("""
            QWidget#container {
                background-color: rgba(30, 30, 40, 230);
                border-radius: 12px;
                border: 2px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        container_layout = QVBoxLayout(self.main_content_widget)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(8)
        
        # Add control bar and keyboard
        container_layout.addLayout(self.create_control_bar())
        
        # Add suggestion bar (for future auto-complete)
        container_layout.addLayout(self.create_suggestion_bar())
        
        # Create keyboard layout widget (so we can hide/show it for zoom)
        self.keyboard_widget = QWidget()
        self.keyboard_widget.setStyleSheet("background: transparent;")
        keyboard_layout = QVBoxLayout(self.keyboard_widget)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard_layout.addLayout(self.create_letters_layout())
        container_layout.addWidget(self.keyboard_widget)
        
        # Create minimized view (hidden initially)
        self.minimized_content_widget = self.create_minimized_view()
        self.minimized_content_widget.hide()
        
        # Add both views to main layout
        main_layout.addWidget(self.main_content_widget)
        main_layout.addWidget(self.minimized_content_widget)
        
        self.setLayout(main_layout)
        
        # Center on screen
        self.center_on_screen()
        
    def create_control_bar(self):
        """Create the top control bar with calibrate, zoom, etc."""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Calibrate button (prominent)
        self.calibrate_btn = QPushButton("👁 CALIBRATE")
        self.calibrate_btn.setMinimumSize(140, 45)
        self.calibrate_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
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
        
        layout.addWidget(self.lang_btn)
        layout.addWidget(self.minimize_btn)
        layout.addWidget(self.close_btn)
        
        return layout
    
    def create_suggestion_bar(self):
        """Create the suggestion bar for future auto-complete (UI only)"""
        layout = QHBoxLayout()
        layout.setSpacing(8)
        
        # Store suggestion buttons for future updates
        self.suggestion_buttons = []
        
        # Placeholder suggestions (will be replaced by prediction engine later)
        placeholder_suggestions = ["word1", "word2", "word3"]
        
        for suggestion in placeholder_suggestions:
            btn = QPushButton(suggestion)
            btn.setMinimumSize(150, 40)
            btn.setFont(QFont("Segoe UI", 12))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 255, 255, 0.08);
                    color: #E0E0E0;
                    border: 1px solid rgba(255, 255, 255, 0.15);
                    border-radius: 6px;
                    text-align: center;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 255, 0.15);
                    border: 1px solid #FBBF24;
                }
                QPushButton:pressed {
                    background-color: #4A90E2;
                    color: white;
                }
            """)
            # Connect to placeholder handler (will be replaced with real logic later)
            btn.clicked.connect(lambda checked, s=suggestion: self.on_suggestion_clicked(s))
            self.suggestion_buttons.append(btn)
            layout.addWidget(btn)
        
        # Add stretch to push buttons to the left
        layout.addStretch()
        
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
    
    def create_letters_layout(self):
        """Create the main keyboard grid with letters"""
        layout = QVBoxLayout()
        layout.setSpacing(8)  # Increased row spacing for better visual separation
        
        # Row 1: Numbers
        row1 = QHBoxLayout()
        row1.setSpacing(4)  # Reduced key spacing
        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        for num in numbers:
            btn = self.create_key(num, 58, 52)
            row1.addWidget(btn)
        
        backspace_btn = self.create_key('⌫', 75, 52)
        backspace_btn.clicked.connect(lambda: self.on_key_pressed('BACKSPACE'))
        row1.addWidget(backspace_btn)
        
        # Row 2: QWERTY (lowercase by default)
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        row2.addStretch()
        qwerty = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']
        for char in qwerty:
            btn = self.create_key(char, 58, 52)
            self.letter_keys[char] = btn  # Store reference for shift toggle
            row2.addWidget(btn)
        row2.addStretch()
        
        # Row 3: ASDFGH (lowercase by default)
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.addStretch()
        asdfgh = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l']
        for char in asdfgh:
            btn = self.create_key(char, 58, 52)
            self.letter_keys[char] = btn  # Store reference for shift toggle
            row3.addWidget(btn)
        row3.addStretch()
        
        enter_btn = self.create_key('↵', 75, 52)
        enter_btn.clicked.connect(lambda: self.on_key_pressed('ENTER'))
        row3.addWidget(enter_btn)
        
        # Row 4: ZXCVBNM (lowercase by default)
        row4 = QHBoxLayout()
        row4.setSpacing(4)
        row4.addStretch()
        zxcvbnm = ['z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.']
        for char in zxcvbnm:
            btn = self.create_key(char, 58, 52)
            if char.isalpha():
                self.letter_keys[char] = btn  # Store reference for shift toggle
            row4.addWidget(btn)
        row4.addStretch()
        
        # Row 5: Bottom row with space
        row5 = QHBoxLayout()
        row5.setSpacing(4)
        
        shift_btn = self.create_key('Shift', 85, 52)
        shift_btn.setCheckable(True)
        shift_btn.clicked.connect(self.on_shift_clicked)
        self.shift_btn = shift_btn  # Store reference
        row5.addWidget(shift_btn)
        
        space_btn = self.create_key('Space', 350, 52)
        space_btn.clicked.connect(lambda: self.on_key_pressed(' '))
        row5.addWidget(space_btn)
        
        # Store reference to switch button so we can update it
        self.symbols_btn = self.create_key('?123', 85, 52)
        self.symbols_btn.clicked.connect(self.on_symbols_clicked)
        row5.addWidget(self.symbols_btn)
        
        # Add all rows
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addLayout(row4)
        layout.addLayout(row5)
        
        return layout
    
    def create_symbols_layout(self):
        """Create the symbols/numbers keyboard layout"""
        layout = QVBoxLayout()
        layout.setSpacing(8)  # Same spacing as letters layout
        
        # Row 1: Special symbols
        row1 = QHBoxLayout()
        row1.setSpacing(4)
        numbers = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
        for num in numbers:
            btn = self.create_key(num, 58, 52)
            row1.addWidget(btn)
        
        backspace_btn = self.create_key('⌫', 75, 52)
        backspace_btn.clicked.connect(lambda: self.on_key_pressed('BACKSPACE'))
        row1.addWidget(backspace_btn)
        
        # Row 2: Numbers
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        row2.addStretch()
        symbols1 = ['!', '@', '#', '$', '%', '^', '&&', '*', '(', ')']
        for sym in symbols1:
            btn = self.create_key(sym, 58, 52)
            row2.addWidget(btn)
        row2.addStretch()
        
        # Row 3: Common symbols
        row3 = QHBoxLayout()
        row3.setSpacing(4)
        row3.addStretch()
        symbols3 = ['-', '/', ':', ';', '(', ')', '$', '&&', '@']
        for sym in symbols3:
            btn = self.create_key(sym, 58, 52)
            row3.addWidget(btn)
        row3.addStretch()
        
        enter_btn = self.create_key('↵', 75, 52)
        enter_btn.clicked.connect(lambda: self.on_key_pressed('ENTER'))
        row3.addWidget(enter_btn)
        
        # Row 4: Punctuation
        row4 = QHBoxLayout()
        row4.setSpacing(4)
        row4.addStretch()
        symbols4 = ['.', ',', '?', '!', "'", '"', '_', '+', '=']
        for sym in symbols4:
            btn = self.create_key(sym, 58, 52)
            row4.addWidget(btn)
        row4.addStretch()
        
        # Row 5: Bottom row with space and switch back
        row5 = QHBoxLayout()
        row5.setSpacing(4)
        
        extra_symbols_btn = self.create_key('#+=', 85, 52)
        extra_symbols_btn.clicked.connect(lambda: print("Extra symbols - TODO"))
        row5.addWidget(extra_symbols_btn)
        
        space_btn = self.create_key('Space', 350, 52)
        space_btn.clicked.connect(lambda: self.on_key_pressed(' '))
        row5.addWidget(space_btn)
        
        # Store reference to switch button so we can update it
        self.symbols_btn = self.create_key('ABC', 85, 52)
        self.symbols_btn.clicked.connect(self.on_symbols_clicked)
        row5.addWidget(self.symbols_btn)
        
        # Add all rows
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addLayout(row4)
        layout.addLayout(row5)
        
        return layout
    
    def create_key(self, text, width, height):
        """Create a styled keyboard key button"""
        btn = QPushButton(text)
        btn.setMinimumSize(width, height)
        btn.setMaximumSize(width, height)
        btn.setFont(QFont("Segoe UI", 13))
        btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #1A1A1A;
                border: none;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #FFFFFF;
                border: 2px solid #FBBF24;
            }
            QPushButton:pressed {
                background-color: #10B981;
                color: white;
            }
            QPushButton:checked {
                background-color: #4A90E2;
                color: white;
            }
        """)
        
        # Connect regular character keys
        special_chars = [',', '.', '!', '@', '#', '$', '%', '^', '*', '(', ')', 
                        '-', '/', ':', ';', '?', "'", '"', '_', '+', '=']
        
        if len(text) == 1 and (text.isalnum() or text in special_chars):
            btn.clicked.connect(lambda: self.on_key_pressed(text))
        elif text == '&&':  # Handle Qt's double ampersand for display
            btn.clicked.connect(lambda: self.on_key_pressed('&'))
        
        return btn
    
    def on_key_pressed(self, key):
        """Handle key press event"""
        print(f"Key pressed: {key}")
    
    def on_calibrate_clicked(self):
        """Handle calibrate button click - start eye tracking"""
        if not self.tracking_manager:
            # Initialize tracking system
            from gazekey.tracking.tracking_manager import TrackingManager
            self.tracking_manager = TrackingManager(camera_id=0)
        
        # Start or stop tracking
        if not self.tracking_manager.is_tracking:
            # Start tracking
            success = self.tracking_manager.start_tracking(callback=self.on_eye_data_received)
            if success:
                # Update button to STOP
                self.calibrate_btn.setText("👁 STOP")
                self.calibrate_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E63946;
                        color: white;
                        border: none;
                        border-radius: 8px;
                        padding: 8px;
                    }
                    QPushButton:hover {
                        background-color: #F64956;
                    }
                    QPushButton:pressed {
                        background-color: #D62936;
                    }
                """)
                
                # Update status label
                self.camera_status_label.setText("📷 Camera: Connected ✓")
                self.camera_status_label.setStyleSheet("""
                    QLabel {
                        color: #10B981;
                        padding: 5px;
                        font-weight: bold;
                    }
                """)
                
                # Show camera preview window
                if not self.camera_preview_window:
                    self.camera_preview_window = CameraPreviewWindow()
                self.camera_preview_window.show()
                
                print("Eye tracking started successfully")
                print("Look at the camera - you should see iris positions in console and preview window")
            else:
                # Failed to start
                self.camera_status_label.setText("📷 Camera: ERROR ✗")
                self.camera_status_label.setStyleSheet("""
                    QLabel {
                        color: #E63946;
                        padding: 5px;
                        font-weight: bold;
                    }
                """)
                print("Failed to start eye tracking - check camera permissions or if another app is using the camera")
        else:
            # Stop tracking
            self.tracking_manager.stop_tracking()
            
            # Hide camera preview window
            if self.camera_preview_window:
                self.camera_preview_window.clear_preview()
                self.camera_preview_window.hide()
            
            # Update button back to CALIBRATE
            self.calibrate_btn.setText("👁 CALIBRATE")
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
            """)
            
            # Update status label
            self.camera_status_label.setText("📷 Camera: Off")
            self.camera_status_label.setStyleSheet("""
                QLabel {
                    color: #999999;
                    padding: 5px;
                }
            """)
            
            # Print statistics
            stats = self.tracking_manager.get_statistics()
            print(f"Tracking stopped. Stats: {stats}")
    
    def on_eye_data_received(self, eye_data):
        """
        Callback when eye data is received from tracking system
        
        Args:
            eye_data: EyeData object with detected eye information
        """
        # Update camera preview window with latest frame
        if self.tracking_manager and self.camera_preview_window:
            frame = self.tracking_manager.get_latest_frame()
            if frame is not None:
                self.camera_preview_window.update_frame(frame)
        
        # Update status label with face detection info and statistics
        if self.tracking_manager:
            stats = self.tracking_manager.get_statistics()
            detection_rate = stats['detection_rate']
            
            if eye_data.face_detected:
                if eye_data.left_iris_center and eye_data.right_iris_center:
                    # Both eyes and irises detected
                    self.camera_status_label.setText(
                        f"📷 Connected ✓ | 👁 Eyes Tracked | Detection: {detection_rate}"
                    )
                    self.camera_status_label.setStyleSheet("""
                        QLabel {
                            color: #10B981;
                            padding: 5px;
                            font-weight: bold;
                        }
                    """)
                else:
                    # Face detected but iris not clear
                    self.camera_status_label.setText(
                        f"📷 Connected ✓ | 👤 Face Only | Detection: {detection_rate}"
                    )
                    self.camera_status_label.setStyleSheet("""
                        QLabel {
                            color: #FBBF24;
                            padding: 5px;
                            font-weight: bold;
                        }
                    """)
            else:
                # No face detected
                self.camera_status_label.setText(
                    f"📷 Connected ✓ | 👁 No Face | Detection: {detection_rate}"
                )
                self.camera_status_label.setStyleSheet("""
                    QLabel {
                        color: #F59E0B;
                        padding: 5px;
                    }
                """)
        
        # Print iris positions every 30 frames to avoid console spam
        if self.tracking_manager and self.tracking_manager.frame_count % 30 == 0:
            if eye_data.left_iris_center and eye_data.right_iris_center:
                print(f"[Frame {self.tracking_manager.frame_count}] Eyes tracked - "
                      f"Left: ({eye_data.left_iris_center[0]:.2f}, {eye_data.left_iris_center[1]:.2f}) | "
                      f"Right: ({eye_data.right_iris_center[0]:.2f}, {eye_data.right_iris_center[1]:.2f})")
        
        # FUTURE: This is where calibration will use the eye data
        # - During calibration: collect gaze points at known screen positions
        # - After calibration: map gaze to screen coordinates for key selection
    
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
        # Hide main content, show minimized icon
        self.main_content_widget.hide()
        self.minimized_content_widget.show()
        self.setFixedSize(120, 100)
        self.is_expanded = False
        print("Keyboard minimized to icon")
    
    def on_restore_clicked(self):
        """Handle restore button click - expand to full keyboard"""
        # Hide minimized icon, show main content
        self.minimized_content_widget.hide()
        self.main_content_widget.show()
        self.setFixedSize(820, 430)
        self.is_expanded = True
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
            print("Switched to letters layout")
        else:  # symbols
            new_layout = self.create_symbols_layout()
            print("Switched to symbols layout")
        
        keyboard_layout.addLayout(new_layout)
        self.current_layout = layout_type
    
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
    
    def center_on_screen(self):
        """Center the window on the screen"""
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = screen.height() - self.height() - 50
        self.move(x, y)
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging"""
        if self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
