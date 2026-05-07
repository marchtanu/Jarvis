import os
from dataclasses import dataclass

@dataclass
class Config:
    # Audio
    SAMPLERATE: int = 44100
    CHANNELS: int = 1
    BLOCK_SIZE: int = 1024
    MIC_DEVICE_INDEX: int | None = None

    # Snap Detection
    SNAP_THRESHOLD_MULTIPLIER: float = 6.0
    SNAP_REFRACTORY_PERIOD: float = 0.3
    SNAP_WINDOW_TIMEOUT: float = 2.0

    # Activation Phrases
    WAKE_PHRASE: str = "daddy home"
    SHUTDOWN_PHRASE: str = "goodbye jojo"
    EXIT_PHRASE: str = "exit"

    # Speech Recognition
    VOSK_MODEL_PATH: str = "vosk-model-small-en-us-0.15"
    WAKE_WORD_TIMEOUT: float = 8.0
    COMMAND_TIMEOUT: float = 10.0

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "jarvis.log"

    # Sound Monitoring
    SOUND_DETECTION_THRESHOLD: float = 0.01

config = Config()
