"""
Tracking Manager
Orchestrates video capture and eye detection in background thread
"""

import threading
import time
from typing import Optional, Callable
from gazekey.tracking.video_capture import VideoCapture
from gazekey.tracking.eye_detector import EyeDetector, EyeData


class TrackingManager:
    """
    Manages the eye tracking pipeline
    
    Coordinates VideoCapture and EyeDetector, runs tracking loop in background
    """
    
    def __init__(self, camera_id: int = 0, target_fps: int = 30):
        """
        Initialize tracking manager
        
        Args:
            camera_id: Camera device ID (default 0)
            target_fps: Target tracking loop rate (default 30)
        """
        self.video_capture = VideoCapture(camera_id)
        self.eye_detector = EyeDetector()
        self.target_fps = target_fps
        self._frame_interval = 1.0 / target_fps
        
        self.is_tracking = False
        self.tracking_thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable[[EyeData], None]] = None
        
        # Statistics
        self.frame_count = 0
        self.detection_count = 0
        self._no_face_frames = 0
        
        # Timestamp tracking for MediaPipe
        self.start_time = time.time()
        
        # Latest frame for camera preview (shared between threads)
        self.latest_frame = None
        self._frame_lock = threading.Lock()
        
    def start_tracking(self, callback: Optional[Callable[[EyeData], None]] = None) -> bool:
        """
        Start eye tracking in background thread
        
        Args:
            callback: Optional function to call with each EyeData result
        
        Returns:
            bool: True if tracking started successfully
        """
        if self.is_tracking:
            print("Tracking already running")
            return True
        
        # Start camera
        if not self.video_capture.start():
            print("Failed to start camera")
            return False
        
        self.callback = callback
        self.is_tracking = True
        
        # Start tracking loop in background thread
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        
        print("Eye tracking started")
        return True
    
    def stop_tracking(self):
        """Stop eye tracking and cleanup resources"""
        if not self.is_tracking:
            return
        
        self.is_tracking = False
        
        # Wait for tracking thread to finish
        if self.tracking_thread:
            self.tracking_thread.join(timeout=2.0)
        
        # Stop camera
        self.video_capture.stop()
        
        print(f"Eye tracking stopped. Processed {self.frame_count} frames, "
              f"detected face in {self.detection_count} frames")
        
        # Reset statistics
        self.frame_count = 0
        self.detection_count = 0
        self._no_face_frames = 0
    
    def _tracking_loop(self):
        """
        Main tracking loop (runs in background thread)
        
        Continuously captures frames and detects eyes
        """
        print("Tracking loop started")
        
        while self.is_tracking:
            frame_start = time.perf_counter()

            # Get frame from camera
            frame = self.video_capture.get_frame()
            
            if frame is None:
                time.sleep(0.01)  # Brief pause if frame capture failed
                continue
            
            # Store latest frame for preview (thread-safe)
            with self._frame_lock:
                self.latest_frame = frame.copy()
            
            # Calculate timestamp in milliseconds (required by MediaPipe)
            timestamp_ms = int((time.time() - self.start_time) * 1000)
            
            # Detect eyes in frame with timestamp
            eye_data = self.eye_detector.detect(frame, timestamp_ms)
            
            # Update statistics
            self.frame_count += 1
            if eye_data.face_detected:
                self.detection_count += 1
                self._no_face_frames = 0
            else:
                self._no_face_frames += 1
                if self._no_face_frames == 30:
                    print(
                        f"WARNING: No face detected for {self._no_face_frames} "
                        "consecutive frames."
                    )
            
            # Call callback if provided (always call, even if no face detected)
            if self.callback:
                try:
                    self.callback(eye_data)
                except Exception as e:
                    print(f"Error in tracking callback: {e}")
            
            elapsed = time.perf_counter() - frame_start
            time.sleep(max(0.0, self._frame_interval - elapsed))
        
        print("Tracking loop ended")
    
    def get_statistics(self) -> dict:
        """
        Get tracking statistics
        
        Returns:
            dict: Statistics including frame count and detection rate
        """
        detection_rate = (self.detection_count / self.frame_count * 100) if self.frame_count > 0 else 0
        
        return {
            'frames_processed': self.frame_count,
            'faces_detected': self.detection_count,
            'detection_rate': f"{detection_rate:.1f}%",
            'is_tracking': self.is_tracking
        }
    
    def get_latest_frame(self):
        """
        Get the latest camera frame (thread-safe)
        
        Returns:
            numpy.ndarray: Latest frame or None if no frame available
        """
        with self._frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None
    
    def cleanup(self):
        """Cleanup all resources"""
        self.stop_tracking()
        self.eye_detector.close()
