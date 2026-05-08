import time
from typing import Optional
from .types import EyeData, BlinkData
import numpy as np

class BlinkDetector:
    def __init__(self, ear_threshold=0.21, consecutive_frames=2):
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames
        
        self.frame_counter = 0
        self.blink_active = False
        self.blink_start_time = 0.0
        
        self.last_blink_time = 0.0
        self.double_blink_max_gap = 0.4  # seconds
        
        self.long_blink_min_duration = 1.0  # seconds

    def _calculate_ear(self, eye: EyeData) -> float:
        """
        Calculates Eye Aspect Ratio.
        MediaPipe Eye landmarks are in a specific order. We'll use distances between
        vertical landmarks over the horizontal distance.
        The landmarks input has 12 points, indices 0-11 corresponding to the ordered extraction.
        Specifically, left eye points mapping:
        [33, 133, 160, 159, 158, 157, 173, 144, 145, 153, 154, 155]
        0: left corner
        1: right corner
        Top points: 2, 3, 4, 5
        Bottom points: 7, 8, 9, 10
        For EAR, we use distance between (2, 10), (3, 9), (4, 8) etc.
        Let's simplify by using the top and bottom extrema.
        """
        lms = eye["landmarks"]
        if len(lms) < 12:
            return 1.0
            
        def dist(p1, p2):
            return np.sqrt((p1["x"] - p2["x"])**2 + (p1["y"] - p2["y"])**2)

        # Horizontal distance
        horizontal_dist = dist(lms[0], lms[1])
        
        # Vertical distances
        v1 = dist(lms[3], lms[9])  # ~159 to ~145
        v2 = dist(lms[4], lms[8])  # ~158 to ~153
        
        if horizontal_dist == 0:
            return 1.0

        return (v1 + v2) / (2.0 * horizontal_dist)

    def process(self, left_eye: Optional[EyeData], right_eye: Optional[EyeData]) -> BlinkData:
        current_time = time.time()
        
        if not left_eye or not right_eye:
            self.frame_counter = 0
            self.blink_active = False
            return BlinkData(blink=False, type="none", duration_ms=0, confidence=0.0)

        left_ear = self._calculate_ear(left_eye)
        right_ear = self._calculate_ear(right_eye)
        
        ear = (left_ear + right_ear) / 2.0
        
        confidence = max(0.0, min(1.0, 1.0 - (ear / (self.ear_threshold * 2))))

        is_blink_frame = ear < self.ear_threshold
        
        blink_type = "none"
        duration_ms = 0
        blink_event_triggered = False

        if is_blink_frame:
            self.frame_counter += 1
            if self.frame_counter >= self.consecutive_frames and not self.blink_active:
                self.blink_active = True
                self.blink_start_time = current_time
        else:
            if self.blink_active:
                # Blink ended
                duration = current_time - self.blink_start_time
                duration_ms = int(duration * 1000)
                
                if duration >= self.long_blink_min_duration:
                    blink_type = "long"
                else:
                    # Check for double blink
                    if current_time - self.last_blink_time <= self.double_blink_max_gap:
                        blink_type = "double"
                    else:
                        blink_type = "single"
                        
                self.last_blink_time = current_time
                blink_event_triggered = True
                
            self.frame_counter = 0
            self.blink_active = False

        if self.blink_active and (current_time - self.blink_start_time) >= self.long_blink_min_duration:
             # Continuously report long blink if eyes are closed for a long time
             blink_event_triggered = True
             blink_type = "long"
             duration_ms = int((current_time - self.blink_start_time) * 1000)

        return BlinkData(
            blink=blink_event_triggered,
            type=blink_type,
            duration_ms=duration_ms,
            confidence=confidence
        )
