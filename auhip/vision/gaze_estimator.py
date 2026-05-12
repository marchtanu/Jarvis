from typing import Optional
from .types import EyeData, GazeData
from .calibration import CalibrationManager

class GazeEstimator:
    def __init__(self, calibration_manager: CalibrationManager, smoothing_alpha=0.3):
        self.calibration_manager = calibration_manager
        self.smoothing_alpha = smoothing_alpha
        
        self.smoothed_h = 0.5
        self.smoothed_v = 0.5
        self.initialized = False

    def _calculate_ratio(self, min_val, max_val, val):
        if max_val - min_val == 0:
            return 0.5
        return (val - min_val) / (max_val - min_val)

    def process(self, left_eye: Optional[EyeData], right_eye: Optional[EyeData]) -> GazeData:
        if not left_eye or not right_eye:
            return GazeData(direction="unknown", confidence=0.0, raw_horizontal_ratio=0.5, raw_vertical_ratio=0.5)

        # Left eye points: 0 is left corner, 1 is right corner
        # (Note: From camera perspective, mirrored, but let's just use the absolute coordinates)
        # We will compute the iris center relative to the bounding box of the eye landmarks.
        
        def get_ratios(eye: EyeData):
            bb = eye["bounding_box"]
            iris = eye["iris_center"]
            
            h_ratio = self._calculate_ratio(bb[0], bb[0] + bb[2], iris["x"])
            v_ratio = self._calculate_ratio(bb[1], bb[1] + bb[3], iris["y"])
            return h_ratio, v_ratio

        l_h, l_v = get_ratios(left_eye)
        r_h, r_v = get_ratios(right_eye)

        h_ratio = (l_h + r_h) / 2.0
        v_ratio = (l_v + r_v) / 2.0

        # Apply Exponential Moving Average
        if not self.initialized:
            self.smoothed_h = h_ratio
            self.smoothed_v = v_ratio
            self.initialized = True
        else:
            self.smoothed_h = (self.smoothing_alpha * h_ratio) + ((1.0 - self.smoothing_alpha) * self.smoothed_h)
            self.smoothed_v = (self.smoothing_alpha * v_ratio) + ((1.0 - self.smoothing_alpha) * self.smoothed_v)

        calib = self.calibration_manager.get_calibration()
        
        # Determine direction based on thresholds
        direction = "center"
        if self.smoothed_h < calib.neutral_h_ratio - calib.h_threshold:
            direction = "right" # Mirrored logic might apply here depending on image flip
        elif self.smoothed_h > calib.neutral_h_ratio + calib.h_threshold:
            direction = "left"
        elif self.smoothed_v < calib.neutral_v_ratio - calib.v_threshold:
            direction = "up"
        elif self.smoothed_v > calib.neutral_v_ratio + calib.v_threshold:
            direction = "down"

        # Calculate a pseudo-confidence based on how clear the eye is (using the average confidence of the EyeData)
        confidence = (left_eye["confidence"] + right_eye["confidence"]) / 2.0

        return GazeData(
            direction=direction,
            confidence=confidence,
            raw_horizontal_ratio=self.smoothed_h,
            raw_vertical_ratio=self.smoothed_v
        )
