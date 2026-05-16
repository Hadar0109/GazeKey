"""
Camera Preview Window
Separate floating window to display live camera feed
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap, QImage
import cv2
import numpy as np


class CameraPreviewWindow(QWidget):
    """
    Floating window that displays live camera preview
    """
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """Initialize the camera preview window"""
        # Window properties
        self.setWindowTitle("GazeKey - Camera Preview")
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        
        # Set window size
        self.setFixedSize(320, 260)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Title label
        title_label = QLabel("📷 Camera Preview")
        title_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        title_label.setStyleSheet("color: white; padding: 5px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Camera preview label
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(300, 225)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 200);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setText("📷\nWaiting for camera...")
        self.preview_label.setFont(QFont("Segoe UI", 10))
        
        # Add widgets to layout
        layout.addWidget(title_label)
        layout.addWidget(self.preview_label)
        
        self.setLayout(layout)
        
        # Window styling
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 40, 240);
                border-radius: 12px;
            }
        """)
        
        # Position window at top-right of screen
        self.position_at_top_right()
    
    def position_at_top_right(self):
        """Position the window at the top-right corner of the screen"""
        screen = self.screen().availableGeometry()
        window_width = self.width()
        
        # Position: 20px from right edge, 20px from top
        x = screen.width() - window_width - 20
        y = 20
        
        self.move(x, y)
    
    def update_frame(self, frame):
        """
        Update the preview with a new camera frame
        
        Args:
            frame: OpenCV BGR frame (numpy array)
        """
        if frame is None:
            self.preview_label.setText("📷\nNo frame")
            return
        
        try:
            # Resize frame to fit preview
            preview_height, preview_width = 225, 300
            frame_resized = cv2.resize(frame, (preview_width, preview_height))
            
            # Convert BGR to RGB
            #frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            frame_rgb = frame_resized
            
            # Convert to QImage
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            
            # Convert to QPixmap and display
            pixmap = QPixmap.fromImage(qt_image)
            self.preview_label.setPixmap(pixmap)
        except Exception as e:
            print(f"Error updating camera preview: {e}")
    
    def clear_preview(self):
        """Clear the camera preview and show default text"""
        self.preview_label.setPixmap(QPixmap())
        self.preview_label.setText("📷\nCamera Off")
