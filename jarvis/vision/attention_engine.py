import time
from typing import Dict, Any, Optional
from .types import AttentionState, AttentionData, BlinkData, GazeData, EyeData

class AttentionEngine:
    def __init__(self):
        self.current_state = AttentionState.USER_ABSENT
        
        self.last_face_time = 0.0
        self.absence_threshold = 2.0  # seconds before USER_ABSENT
        
        self.gaze_center_duration = 0.0
        self.last_gaze_direction = "unknown"
        self.gaze_start_time = time.time()
        
        self.distraction_threshold = 5.0 # seconds of non-center gaze to be DISTRACTED
        self.focus_threshold = 3.0 # seconds of center gaze to be FOCUSED
        
    def process(self, has_face: bool, gaze_data: GazeData, blink_data: BlinkData) -> AttentionData:
        current_time = time.time()
        
        metrics: Dict[str, Any] = {
            "gaze_duration": current_time - self.gaze_start_time
        }
        
        if not has_face:
            if current_time - self.last_face_time > self.absence_threshold:
                self._update_state(AttentionState.USER_ABSENT)
            return self._build_data(1.0, metrics)
            
        self.last_face_time = current_time
        
        if self.current_state == AttentionState.USER_ABSENT:
            self._update_state(AttentionState.USER_PRESENT)
            
        # Update gaze duration tracking
        if gaze_data["direction"] != self.last_gaze_direction:
            self.last_gaze_direction = gaze_data["direction"]
            self.gaze_start_time = current_time
            
        gaze_duration = current_time - self.gaze_start_time
        metrics["gaze_duration"] = gaze_duration
        
        if blink_data["type"] == "long" and blink_data["duration_ms"] > 5000:
            self._update_state(AttentionState.USER_IDLE)
        elif gaze_data["direction"] == "center":
            if gaze_duration >= self.focus_threshold:
                self._update_state(AttentionState.USER_FOCUSED)
            else:
                if self.current_state not in (AttentionState.USER_FOCUSED, AttentionState.USER_ENGAGED):
                    self._update_state(AttentionState.USER_ENGAGED)
        else:
            if gaze_duration >= self.distraction_threshold:
                self._update_state(AttentionState.USER_DISTRACTED)

        confidence = 0.85 # Heuristic confidence
        return self._build_data(confidence, metrics)

    def _update_state(self, new_state: AttentionState):
        self.current_state = new_state

    def _build_data(self, confidence: float, metrics: dict) -> AttentionData:
        return AttentionData(
            attention_state=self.current_state.name,
            confidence=confidence,
            metrics=metrics
        )
