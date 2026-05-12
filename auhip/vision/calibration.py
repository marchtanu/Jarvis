from dataclasses import dataclass
from typing import Optional

@dataclass
class GazeCalibration:
    neutral_h_ratio: float = 0.5
    neutral_v_ratio: float = 0.5
    h_threshold: float = 0.1  # Deviation needed to register left/right
    v_threshold: float = 0.1  # Deviation needed to register up/down
    
    def is_calibrated(self) -> bool:
        return self.neutral_h_ratio != 0.5 or self.neutral_v_ratio != 0.5

class CalibrationManager:
    def __init__(self):
        self.calibration = GazeCalibration()
        self._collecting = False
        self._samples_h = []
        self._samples_v = []
        self._max_samples = 30
        
    def start_calibration(self):
        self._collecting = True
        self._samples_h.clear()
        self._samples_v.clear()
        
    def add_sample(self, h_ratio: float, v_ratio: float) -> bool:
        """Returns True if calibration is complete."""
        if not self._collecting:
            return False
            
        self._samples_h.append(h_ratio)
        self._samples_v.append(v_ratio)
        
        if len(self._samples_h) >= self._max_samples:
            self._finish_calibration()
            return True
            
        return False
        
    def _finish_calibration(self):
        self._collecting = False
        if not self._samples_h:
            return
            
        # Calculate mean for neutral offsets, dropping outliers
        self._samples_h.sort()
        self._samples_v.sort()
        
        # Drop top and bottom 10%
        trim_idx = max(1, int(len(self._samples_h) * 0.1))
        trimmed_h = self._samples_h[trim_idx:-trim_idx]
        trimmed_v = self._samples_v[trim_idx:-trim_idx]
        
        self.calibration.neutral_h_ratio = sum(trimmed_h) / len(trimmed_h)
        self.calibration.neutral_v_ratio = sum(trimmed_v) / len(trimmed_v)
        
        # Calculate standard deviation to set thresholds (minimum 0.05)
        var_h = sum((x - self.calibration.neutral_h_ratio)**2 for x in trimmed_h) / len(trimmed_h)
        var_v = sum((x - self.calibration.neutral_v_ratio)**2 for x in trimmed_v) / len(trimmed_v)
        
        self.calibration.h_threshold = max(0.05, (var_h ** 0.5) * 2)
        self.calibration.v_threshold = max(0.05, (var_v ** 0.5) * 2)

    def get_calibration(self) -> GazeCalibration:
        return self.calibration
