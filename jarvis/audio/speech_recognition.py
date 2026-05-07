"""
jarvis/audio/speech_recognition.py
-----------------------------------
Speech recognition module using the SpeechRecognition library with Google Web API.

The key insight: sr.Microphone() handles its own audio capture internally
and does automatic noise adjustment + voice activity detection, making it
far more reliable than feeding raw numpy chunks.

When triggered (after double-snap), we open a Microphone context in a
thread-pool to avoid blocking the asyncio event loop.
"""
import logging
import asyncio
import speech_recognition as sr

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self._mic_device_index = None  # None = default device
        self._calibrated = False

    def initialize(self) -> bool:
        """
        Calibrate the recognizer against ambient noise.
        Call this once at startup.
        """
        try:
            logger.info("Calibrating microphone against ambient noise...")
            with sr.Microphone(device_index=self._mic_device_index) as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            logger.info(
                f"Calibration complete. Energy threshold: {self.recognizer.energy_threshold:.0f}"
            )
            self._calibrated = True
            return True
        except Exception as e:
            logger.error(f"Microphone calibration failed: {e}")
            return False

    def _listen_blocking(self, timeout: float, phrase_time_limit: float) -> str | None:
        """
        Blocking call — runs inside a thread-pool executor.
        Listens until speech ends or phrase_time_limit is reached.
        """
        try:
            with sr.Microphone(device_index=self._mic_device_index) as source:
                logger.info(
                    f"Listening for command (timeout={timeout}s, "
                    f"phrase_limit={phrase_time_limit}s)..."
                )
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )

            text = self.recognizer.recognize_google(audio).lower()
            logger.info(f"Recognized: \"{text}\"")
            return text

        except sr.WaitTimeoutError:
            logger.info("Listening timed out — no speech detected.")
        except sr.UnknownValueError:
            logger.warning("Could not understand audio.")
        except sr.RequestError as e:
            logger.error(f"Google API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected recognition error: {e}")

        return None

    async def listen_for_command(
        self, timeout: float = 5.0, phrase_time_limit: float = 7.0
    ) -> str | None:
        """
        Async wrapper — runs the blocking listen call in a thread so the
        asyncio event loop (and snap detector) keep running.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self._listen_blocking(timeout, phrase_time_limit),
        )

    # ── Compatibility shim for old chunk-based API ──────────────────────────
    def process_chunk(self, audio_data) -> str | None:
        """
        Not used in the new sr.Microphone() approach, kept for API compatibility.
        """
        return None
