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
    Structured data representing detected eye information (subject-centric).

    MediaPipe iris indices: 468 = subject's left eye, 473 = subject's right eye.
    """
    face_detected: bool
    subject_left_iris_center: Optional[Tuple[float, float]] = None   # landmark 468
    subject_right_iris_center: Optional[Tuple[float, float]] = None  # landmark 473
    subject_left_eye_landmarks: Optional[List[Tuple[float, float]]] = None
    subject_right_eye_landmarks: Optional[List[Tuple[float, float]]] = None

    @property
    def left_iris_center(self) -> Optional[Tuple[float, float]]:
        return self.subject_left_iris_center

    @property
    def right_iris_center(self) -> Optional[Tuple[float, float]]:
        return self.subject_right_iris_center

    @property
    def left_eye_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        return self.subject_left_eye_landmarks

    @property
    def right_eye_landmarks(self) -> Optional[List[Tuple[float, float]]]:
        return self.subject_right_eye_landmarks


class EyeDetector:
    """
    Extracts eye landmarks from video frames using MediaPipe
    
    Uses MediaPipe Face Landmarker (new API) for facial landmark detection
    """
    
    # MediaPipe landmark indices for eyes (full contours, subject-centric)
    LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    SUBJECT_LEFT_IRIS_INDICES = [468, 474, 475, 476, 477]
    SUBJECT_RIGHT_IRIS_INDICES = [473, 469, 470, 471, 472]
    SUBJECT_LEFT_IRIS_CENTER = 468
    SUBJECT_RIGHT_IRIS_CENTER = 473
    
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
        subject_left_eye = [
            (face_landmarks[i].x, face_landmarks[i].y) for i in self.LEFT_EYE_INDICES
        ]
        subject_right_eye = [
            (face_landmarks[i].x, face_landmarks[i].y) for i in self.RIGHT_EYE_INDICES
        ]

        left_iris = face_landmarks[self.SUBJECT_LEFT_IRIS_CENTER]
        right_iris = face_landmarks[self.SUBJECT_RIGHT_IRIS_CENTER]
        subject_left_iris = (left_iris.x, left_iris.y)
        subject_right_iris = (right_iris.x, right_iris.y)

        return EyeData(
            face_detected=True,
            subject_left_iris_center=subject_left_iris,
            subject_right_iris_center=subject_right_iris,
            subject_left_eye_landmarks=subject_left_eye,
            subject_right_eye_landmarks=subject_right_eye,
        )
    
    def close(self):
        """Cleanup MediaPipe resources"""
        if self.landmarker:
            self.landmarker.close()
            print("MediaPipe Face Landmarker closed")
