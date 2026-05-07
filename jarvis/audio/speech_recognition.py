import logging
import asyncio
import speech_recognition as sr
from ..core.config import config

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._calibrated = False

    def initialize(self) -> bool:
        try:
            logger.info("Calibrating microphone against ambient noise...")
            with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            logger.info(f"Calibration complete. Threshold: {self.recognizer.energy_threshold:.0f}")
            self._calibrated = True
            return True
        except Exception as e:
            logger.error(f"Microphone calibration failed: {e}")
            return False

    def _listen_blocking(self, timeout: float, phrase_time_limit: float) -> str | None:
        try:
            with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            text = self.recognizer.recognize_google(audio).lower()
            logger.info(f'Recognized: "{text}"')
            return text
        except sr.WaitTimeoutError:
            logger.info("Listening timed out.")
        except sr.UnknownValueError:
            logger.warning("Could not understand audio.")
        except sr.RequestError as e:
            logger.error(f"Google API error: {e}")
        except Exception as e:
            logger.error(f"Recognition error: {e}")
        return None

    async def listen_for_command(
        self, timeout: float = 10.0, phrase_time_limit: float = 10.0
    ) -> str | None:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._listen_blocking(timeout, phrase_time_limit)
        )

    def process_chunk(self, audio_data) -> str | None:
        return None
