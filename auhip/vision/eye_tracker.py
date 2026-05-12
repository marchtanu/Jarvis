import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, Dict, List, Tuple
from .types import EyeData, Point

class EyeTracker:
    def __init__(self, max_faces=1, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=max_faces,
            refine_landmarks=True, # Critical for iris tracking
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # MediaPipe landmark indices
        self.LEFT_EYE_INDICES = [33, 133, 160, 159, 158, 157, 173, 144, 145, 153, 154, 155]
        self.RIGHT_EYE_INDICES = [362, 263, 387, 386, 385, 384, 398, 373, 374, 380, 381, 382]
        self.LEFT_IRIS_INDICES = [468, 469, 470, 471, 472]
        self.RIGHT_IRIS_INDICES = [473, 474, 475, 476, 477]
        
    def process(self, frame: np.ndarray) -> Optional[Dict[str, EyeData]]:
        """
        Processes a BGR image and extracts eye/iris landmarks.
        Returns a dict with 'left_eye' and 'right_eye' EyeData, or None if no face is found.
        """
        # Convert the BGR image to RGB before processing
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # To improve performance, optionally mark the image as not writeable
        frame_rgb.flags.writeable = False
        results = self.face_mesh.process(frame_rgb)
        
        if not results.multi_face_landmarks:
            return None
            
        landmarks = results.multi_face_landmarks[0].landmark
        
        left_eye = self._extract_eye_data(landmarks, self.LEFT_EYE_INDICES, self.LEFT_IRIS_INDICES)
        right_eye = self._extract_eye_data(landmarks, self.RIGHT_EYE_INDICES, self.RIGHT_IRIS_INDICES)
        
        if left_eye and right_eye:
            return {
                "left_eye": left_eye,
                "right_eye": right_eye,
                "face_landmarks": [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in landmarks]
            }
        return None
        
    def _extract_eye_data(self, landmarks, eye_indices: List[int], iris_indices: List[int]) -> Optional[EyeData]:
        try:
            eye_lms = [{"x": landmarks[i].x, "y": landmarks[i].y, "z": landmarks[i].z} for i in eye_indices]
            iris_lms = [{"x": landmarks[i].x, "y": landmarks[i].y, "z": landmarks[i].z} for i in iris_indices]
            
            # The center of the iris is the first index in the iris landmarks list for mediapipe
            iris_center = iris_lms[0]
            
            # Calculate bounding box (xmin, ymin, width, height)
            xs = [lm["x"] for lm in eye_lms]
            ys = [lm["y"] for lm in eye_lms]
            xmin, xmax = min(xs), max(xs)
            ymin, ymax = min(ys), max(ys)
            
            return EyeData(
                landmarks=eye_lms,
                iris_center=iris_center,
                bounding_box=(xmin, ymin, xmax - xmin, ymax - ymin),
                confidence=0.9  # FaceMesh doesn't provide point confidence directly, assuming 0.9 if detected
            )
        except IndexError:
            return None
            
    def close(self):
        self.face_mesh.close()
