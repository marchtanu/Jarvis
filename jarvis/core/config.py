import os
from dataclasses import dataclass, field

@dataclass
class Config:
    # Audio Settings
    SAMPLERATE: int = 44100
    CHANNELS: int = 1
    BLOCK_SIZE: int = 1024  # Size of audio chunks for processing
    
    # Snap Detection
    SNAP_THRESHOLD_MULTIPLIER: float = 6.0  # Multiplier over average energy
    SNAP_REFRACTORY_PERIOD: float = 0.3     # Seconds to ignore after a snap
    SNAP_WINDOW_TIMEOUT: float = 2.0        # Seconds allowed between snaps
    
    # Speech Recognition
    VOSK_MODEL_PATH: str = "vosk-model-small-en-us-0.15"         # Path to Vosk model directory
    COMMAND_TIMEOUT: float = 5.0            # Seconds to listen for command
    
    # State Timings
    ARMED_TIMEOUT: float = 3.0             # How long to stay armed before reverting to idle
    
    # Sound Monitoring
    SOUND_DETECTION_THRESHOLD: float = 0.01  # RMS energy above which we consider sound detected
    
    # Logging
    LOG_LEVEL: str = "INFO"

config = Config()
