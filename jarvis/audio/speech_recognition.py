import logging
import asyncio
import json
import time
import numpy as np
try:
    import vosk
except ImportError:
    vosk = None
import speech_recognition as sr
from ..core.config import config

logger = logging.getLogger(__name__)


class SpeechRecognizer:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.model = None
        self.rec = None
        self._calibrated = False
        self._use_vosk = True  # Set to False to switch back to Google

    def initialize(self) -> bool:
        if self._use_vosk:
            try:
                if not vosk:
                    logger.error("Vosk module not found. Please install it: pip install vosk")
                    return False
                logger.info(f"Loading Vosk model from: {config.VOSK_MODEL_PATH}")
                # Vosk logging is very verbose, suppress it unless debugging
                vosk.SetLogLevel(-1)
                self.model = vosk.Model(config.VOSK_MODEL_PATH)
                self.rec = vosk.KaldiRecognizer(self.model, config.SAMPLERATE)
                self._calibrated = True
                return True
            except Exception as e:
                logger.error(f"Vosk initialization failed: {e}")
                return False
        else:
            # --- OLD GOOGLE METHOD (Commented out but preserved) ---
            # try:
            #     logger.info("Calibrating microphone against ambient noise...")
            #     with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
            #         self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            #     logger.info(f"Calibration complete. Threshold: {self.recognizer.energy_threshold:.0f}")
            #     self._calibrated = True
            #     return True
            # except Exception as e:
            #     logger.error(f"Microphone calibration failed: {e}")
            #     return False
            return False

    def _listen_blocking(self, timeout: float, phrase_time_limit: float, grammar: list = None, validator: callable = None) -> str | None:
        if not self._use_vosk:
            return self._listen_google_blocking(timeout, phrase_time_limit)

        text, audio_buffer = self._listen_vosk_blocking(timeout, phrase_time_limit, grammar)
        
        # Fallback Logic:
        # If Vosk returned nothing, OR if a validator is provided and says the text isn't a valid command,
        # we send the EXACT same audio buffer to Google Cloud to try again.
        should_fallback = False
        if not text:
            should_fallback = True
        elif validator and not validator(text):
            logger.info(f"Vosk recognized '{text}', but it doesn't match a command. Falling back to Google...")
            should_fallback = True

        if should_fallback and audio_buffer:
            fallback_text = self._recognize_google_from_buffer(audio_buffer)
            if fallback_text:
                return fallback_text
        
        return text

    def _listen_vosk_blocking(self, timeout: float, phrase_time_limit: float, grammar: list = None) -> tuple[str | None, bytes | None]:
        """Local Vosk recognition loop. Returns (text, raw_audio_buffer)."""
        import sounddevice as sd
        audio_buffer = bytearray()
        try:
            if grammar:
                grammar_json = json.dumps(grammar + ["[unk]"])
                rec = vosk.KaldiRecognizer(self.model, config.SAMPLERATE, grammar_json)
            else:
                rec = self.rec

            with sd.RawInputStream(samplerate=config.SAMPLERATE, blocksize=8000, dtype='int16',
                                  channels=1, device=config.MIC_DEVICE_INDEX) as stream:
                logger.info("Vosk is listening...")
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    data, overflowed = stream.read(4000)
                    audio_buffer.extend(data)
                    
                    if rec.AcceptWaveform(bytes(data)):
                        result = json.loads(rec.Result())
                        text = result.get("text", "")
                        if text:
                            logger.info(f'Vosk Recognized: "{text}"')
                            return text, bytes(audio_buffer)
                
                # Final check after timeout
                result = json.loads(rec.FinalResult())
                text = result.get("text", "")
                if text:
                    logger.info(f'Vosk Recognized (Final): "{text}"')
                return (text if text else None), bytes(audio_buffer)
                
        except Exception as e:
            logger.error(f"Vosk recognition error: {e}")
        return None, bytes(audio_buffer)

    def _recognize_google_from_buffer(self, buffer: bytes) -> str | None:
        """Fallback: Process already-captured audio through Google Cloud STT."""
        try:
            logger.info("Requesting Google Cloud fallback recognition...")
            # Vosk uses int16, which is 2 bytes per sample
            audio_data = sr.AudioData(buffer, config.SAMPLERATE, 2)
            text = self.recognizer.recognize_google(audio_data).lower()
            logger.info(f"Google Fallback Recognized: '{text}'")
            return text
        except sr.UnknownValueError:
            logger.debug("Google fallback also failed to understand audio.")
        except Exception as e:
            logger.error(f"Google fallback error: {e}")
        return None

    def _listen_google_blocking(self, timeout: float, phrase_time_limit: float) -> str | None:
        """Original Google Cloud recognition method."""
        try:
            with sr.Microphone(device_index=config.MIC_DEVICE_INDEX) as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            text = self.recognizer.recognize_google(audio).lower()
            logger.info(f'Google Recognized: "{text}"')
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
        self, timeout: float = 10.0, phrase_time_limit: float = 10.0, grammar: list = None, validator: callable = None
    ) -> str | None:
        """
        Listens for a command. 
        If grammar is provided, Vosk is restricted to those words.
        If validator is provided, it checks if the text is a valid command; if not, falls back to Google.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._listen_blocking(timeout, phrase_time_limit, grammar, validator)
        )

    def process_chunk(self, audio_data) -> str | None:
        """Used for streaming recognition if the audio loop feeds chunks directly."""
        if self._use_vosk and self.rec:
            # Convert float32 to int16 if necessary
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            if self.rec.AcceptWaveform(audio_data.tobytes()):
                result = json.loads(self.rec.Result())
                return result.get("text")
        return None
