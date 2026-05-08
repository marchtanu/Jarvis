import queue
# pyrefly: ignore [missing-import]
import sounddevice as sd
import logging
from ..core.config import config

logger = logging.getLogger(__name__)

class Microphone:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.stream = None

    def _callback(self, indata, frames, time, status):
        if status:
            logger.warning(f"Audio stream status: {status}")
        self.audio_queue.put(indata.copy())

    def start(self, device_index=None):
        self.stream = sd.InputStream(
            device=device_index,
            samplerate=config.SAMPLERATE,
            channels=config.CHANNELS,
            blocksize=config.BLOCK_SIZE,
            callback=self._callback
        )
        self.stream.start()
        logger.info(f"Microphone stream started (Device: {device_index if device_index is not None else 'Default'}).")

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            logger.info("Microphone stream stopped.")

    def get_audio_chunk(self):
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None
