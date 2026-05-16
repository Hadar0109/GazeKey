"""
Eye Detection Module
Wraps MediaPipe for face and eye landmark detection
"""

import math

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class EyeData:
    """
    Structured data representing detected eye information (subject-centric).

    MediaPipe iris indices: 468 = subject's left eye, 473 = subject's right eye.
    """
    face_detected: bool
    is_blinking: bool = False
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
    _EAR_CONTOUR_OFFSETS = (0, 4, 3, 8, 5, 11)
    _IRIS_SCORE_THRESHOLD = 0.5
    _EAR_BLINK_THRESHOLD = 0.20

    def __init__(self, model_path: str = "models/face_landmarker.task"):
        """
        Initialize MediaPipe Face Landmarker detector
        
        Args:
            model_path: Path to the face_landmarker.task model file
        """
        self.model_path = model_path

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
    
    def _landmark_xy(self, face_landmarks, index: int) -> Tuple[float, float]:
        lm = face_landmarks[index]
        return (lm.x, lm.y)

    def _eye_aspect_ratio(
        self,
        eye_landmarks: List[Tuple[float, float]],
    ) -> float:
        """EAR from six contour points indexed into the eye landmark list."""
        pts = [eye_landmarks[i] for i in self._EAR_CONTOUR_OFFSETS]
        p1, p2, p3, p4, p5, p6 = pts

        def dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
            return math.hypot(a[0] - b[0], a[1] - b[1])

        vertical = dist(p2, p6) + dist(p3, p5)
        horizontal = 2.0 * dist(p1, p4)
        if horizontal < 1e-9:
            return 1.0
        return vertical / horizontal

    def _iris_score(self, lm, attr: str) -> float:
        """MediaPipe often leaves presence/visibility unset (None) on iris points."""
        value = getattr(lm, attr, None)
        if value is None:
            return 1.0
        return float(value)

    def _iris_valid(self, face_landmarks, index: int) -> bool:
        lm = face_landmarks[index]
        presence = self._iris_score(lm, "presence")
        visibility = self._iris_score(lm, "visibility")
        return (
            presence >= self._IRIS_SCORE_THRESHOLD
            and visibility >= self._IRIS_SCORE_THRESHOLD
        )

    def _extract_eye_landmarks(self, face_landmarks) -> EyeData:
        """
        Extract eye-specific landmarks from MediaPipe face landmarks
        
        Args:
            face_landmarks: MediaPipe face landmarks list
        
        Returns:
            EyeData: Extracted eye information
        """
        subject_left_eye = [
            self._landmark_xy(face_landmarks, i) for i in self.LEFT_EYE_INDICES
        ]
        subject_right_eye = [
            self._landmark_xy(face_landmarks, i) for i in self.RIGHT_EYE_INDICES
        ]

        left_ear = self._eye_aspect_ratio(subject_left_eye)
        right_ear = self._eye_aspect_ratio(subject_right_eye)
        if left_ear < self._EAR_BLINK_THRESHOLD or right_ear < self._EAR_BLINK_THRESHOLD:
            return EyeData(face_detected=True, is_blinking=True)

        subject_left_iris: Optional[Tuple[float, float]] = None
        subject_right_iris: Optional[Tuple[float, float]] = None

        if self._iris_valid(face_landmarks, self.SUBJECT_LEFT_IRIS_CENTER):
            subject_left_iris = self._landmark_xy(
                face_landmarks, self.SUBJECT_LEFT_IRIS_CENTER
            )
        if self._iris_valid(face_landmarks, self.SUBJECT_RIGHT_IRIS_CENTER):
            subject_right_iris = self._landmark_xy(
                face_landmarks, self.SUBJECT_RIGHT_IRIS_CENTER
            )

        if subject_left_iris is None and subject_right_iris is None:
            return EyeData(face_detected=False)

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
