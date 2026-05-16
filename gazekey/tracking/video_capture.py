"""
Video Capture Module
Wraps OpenCV for webcam access and frame acquisition
"""

import cv2
import numpy as np
from typing import Optional, Tuple


class VideoCapture:
    """
    Manages webcam lifecycle and provides frame stream
    
    Uses OpenCV (external library) for camera access
    """
    
    def __init__(self, camera_id: int = 0):
        """
        Initialize video capture
        
        Args:
            camera_id: Camera device ID (0 for default webcam)
        """
        self.camera_id = camera_id
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        
    def start(self) -> bool:
        """
        Open camera and start capture
        
        Returns:
            bool: True if camera opened successfully, False otherwise
        """
        try:
            # EXTERNAL: OpenCV call to open camera
            self.cap = cv2.VideoCapture(self.camera_id)
            
            if not self.cap.isOpened():
                print(f"Error: Could not open camera {self.camera_id}")
                return False
            
            # Set camera properties for optimal performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            
            self.is_running = True
            print(f"Camera {self.camera_id} opened successfully")
            return True
            
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def get_frame(self) -> Optional[np.ndarray]:
        """
        Get single frame from camera
        
        Returns:
            numpy.ndarray: RGB image frame, or None if capture failed
        """
        if not self.is_running or self.cap is None:
            return None
        
        try:
            # EXTERNAL: OpenCV call to read frame
            ret, frame = self.cap.read()
            
            if not ret:
                print("Error: Failed to read frame")
                return None
            
            # EXTERNAL: OpenCV call to convert BGR to RGB
            # MediaPipe requires RGB format
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            return rgb_frame
            
        except Exception as e:
            print(f"Error getting frame: {e}")
            return None
    
    def stop(self):
        """Release camera and cleanup resources"""
        if self.cap is not None:
            # EXTERNAL: OpenCV call to release camera
            self.cap.release()
            print(f"Camera {self.camera_id} released")
        
        self.is_running = False
        self.cap = None
    
    def is_available(self) -> bool:
        """Check if camera is currently available"""
        return self.is_running and self.cap is not None and self.cap.isOpened()
