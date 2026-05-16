"""
Eye Detection Module
Wraps MediaPipe for face and eye landmark detection
"""

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import time


@dataclass
class EyeData:
    """
    Structured data representing detected eye information
    
    Attributes:
        face_detected: Whether a face was found in the frame
        left_iris_center: (x, y) normalized coordinates of left iris center
        right_iris_center: (x, y) normalized coordinates of right iris center
        left_eye_landmarks: List of normalized (x, y) coordinates for left eye region
        right_eye_landmarks: List of normalized (x, y) coordinates for right eye region
    """
    face_detected: bool
    left_iris_center: Optional[Tuple[float, float]] = None
    right_iris_center: Optional[Tuple[float, float]] = None
    left_eye_landmarks: Optional[List[Tuple[float, float]]] = None
    right_eye_landmarks: Optional[List[Tuple[float, float]]] = None


class EyeDetector:
    """
    Extracts eye landmarks from video frames using MediaPipe
    
    Uses MediaPipe Face Landmarker (new API) for facial landmark detection
    """
    
    # MediaPipe landmark indices for eyes (full contours)
    LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
    RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
    
    def __init__(self, model_path: str = "models/face_landmarker.task"):
        """
        Initialize MediaPipe Face Landmarker detector
        
        Args:
            model_path: Path to the face_landmarker.task model file
        """
        self.model_path = model_path
        self.start_time = time.time()
        
        try:
            # Initialize MediaPipe Face Landmarker with new API
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5
            )
            self.landmarker = vision.FaceLandmarker.create_from_options(options)
            print(f"MediaPipe Face Landmarker initialized (model: {model_path})")
        except Exception as e:
            print(f"ERROR: Failed to initialize MediaPipe Face Landmarker: {e}")
            raise
    
    def detect(self, frame: np.ndarray, timestamp_ms: int) -> EyeData:
        """
        Process frame and detect eye landmarks
        
        Args:
            frame: RGB image frame (numpy array)
            timestamp_ms: Frame timestamp in milliseconds (required by MediaPipe)
        
        Returns:
            EyeData: Structured eye information
        """
        if frame is None:
            return EyeData(face_detected=False)
        
        try:
            # Convert numpy array to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            
            # Detect face landmarks using new API
            detection_result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
            
            if not detection_result.face_landmarks:
                return EyeData(face_detected=False)
            
            # Extract landmarks from first detected face
            face_landmarks = detection_result.face_landmarks[0]
            
            # Extract eye data
            eye_data = self._extract_eye_landmarks(face_landmarks)
            
            return eye_data
            
        except Exception as e:
            print(f"Error detecting eyes: {e}")
            return EyeData(face_detected=False)
    
    def _extract_eye_landmarks(self, face_landmarks) -> EyeData:
        """
        Extract eye-specific landmarks from MediaPipe face landmarks
        
        Args:
            face_landmarks: MediaPipe face landmarks list
        
        Returns:
            EyeData: Extracted eye information
        """
        # Extract left eye landmarks
        left_eye = [(face_landmarks[i].x, face_landmarks[i].y) for i in self.LEFT_EYE_INDICES]
        
        # Extract right eye landmarks
        right_eye = [(face_landmarks[i].x, face_landmarks[i].y) for i in self.RIGHT_EYE_INDICES]
        
        # Extract iris centers (average of iris landmarks)
        left_iris = self._calculate_iris_center(face_landmarks, self.LEFT_IRIS_INDICES)
        right_iris = self._calculate_iris_center(face_landmarks, self.RIGHT_IRIS_INDICES)
        
        return EyeData(
            face_detected=True,
            left_iris_center=left_iris,
            right_iris_center=right_iris,
            left_eye_landmarks=left_eye,
            right_eye_landmarks=right_eye
        )
    
    def _calculate_iris_center(self, face_landmarks, iris_indices: List[int]) -> Tuple[float, float]:
        """
        Calculate iris center as average of iris landmark positions
        
        Args:
            face_landmarks: MediaPipe landmarks list
            iris_indices: List of landmark indices for iris
        
        Returns:
            (x, y): Normalized iris center coordinates
        """
        iris_points = [(face_landmarks[i].x, face_landmarks[i].y) for i in iris_indices]
        
        # Calculate average position
        avg_x = sum(p[0] for p in iris_points) / len(iris_points)
        avg_y = sum(p[1] for p in iris_points) / len(iris_points)
        
        return (avg_x, avg_y)
    
    def close(self):
        """Cleanup MediaPipe resources"""
        if self.landmarker:
            self.landmarker.close()
            print("MediaPipe Face Landmarker closed")
