import numpy as np
import time
import logging
# pyrefly: ignore [missing-import]
import asyncio
from ..core.config import config
from ..core.event_bus import event_bus

logger = logging.getLogger(__name__)

class SnapDetector:
    def __init__(self):
        self.energy_history = []
        self.history_size = 50
        self.last_trigger_time = 0
        self.is_running = False

    async def process_audio(self, audio_data: np.ndarray):
        if not self.is_running:
            return

        # Use absolute values for energy calculation
        # Pre-emphasis: boost high frequencies where snaps reside
        # y[n] = x[n] - 0.97 * x[n-1]
        # For simplicity, we just use RMS energy here, but filter could be added
        
        current_energy = np.sqrt(np.mean(audio_data**2))
        
        # Continuous sound detection logging (optional, can be noisy)
        if current_energy > config.SOUND_DETECTION_THRESHOLD:
            # We use a slight throttle for sound detection logs to avoid spam
            if not hasattr(self, 'last_sound_log_time'):
                self.last_sound_log_time = 0
            
            if time.time() - self.last_sound_log_time > 1.0:
                logger.info(f"Sound detected! Energy: {current_energy:.4f}")
                self.last_sound_log_time = time.time()
                await event_bus.publish("SOUND_DETECTED", {"energy": current_energy})

        # Maintain history for adaptive thresholding
        self.energy_history.append(current_energy)
        if len(self.energy_history) > self.history_size:
            self.energy_history.pop(0)
            
        avg_energy = max(np.mean(self.energy_history), 0.001)
        
        # Detection logic
        current_time = time.time()
        if (current_energy > avg_energy * config.SNAP_THRESHOLD_MULTIPLIER and 
            current_time - self.last_trigger_time > config.SNAP_REFRACTORY_PERIOD):
            
            logger.info(f"Snap detected! Energy: {current_energy:.4f}, Avg: {avg_energy:.4f}")
            self.last_trigger_time = current_time
            await event_bus.publish("SNAP_DETECTED", {"time": current_time, "energy": current_energy})

    def start(self):
        self.is_running = True
        logger.info("Snap detector activated.")

    def stop(self):
        self.is_running = False
        logger.info("Snap detector deactivated.")
