import logging
import asyncio
import json
import time
import queue
import os
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
                    self._use_vosk = False
                    return False
                
                if not os.path.exists(config.VOSK_MODEL_PATH):
                    logger.error(f"Vosk model not found at: {config.VOSK_MODEL_PATH}")
                    self._use_vosk = False
                    return False

                logger.info(f"Loading Vosk model from: {config.VOSK_MODEL_PATH}")
                # Vosk logging is very verbose, suppress it unless debugging
                vosk.SetLogLevel(-1)
                self.model = vosk.Model(config.VOSK_MODEL_PATH)
                
                if not self.model:
                    logger.error("Vosk model failed to load (returned None).")
                    self._use_vosk = False
                    return False

                self.rec = vosk.KaldiRecognizer(self.model, config.SAMPLERATE)
                self._calibrated = True
                logger.info("Vosk initialized successfully.")
                return True
            except Exception as e:
                logger.error(f"Vosk initialization failed: {e}")
                self.model = None
                self.rec = None
                self._use_vosk = False
                return False
        return False

    def _listen_blocking(self, timeout: float, phrase_time_limit: float, grammar: list = None, validator: callable = None, cancel_event: asyncio.Event = None, mic=None) -> str | None:
        if not self._use_vosk or not self.model:
            if self._use_vosk:
                logger.warning("Vosk requested but model not loaded. Falling back to Google.")
            return self._listen_google_blocking(timeout, phrase_time_limit)

        text, audio_buffer = self._listen_vosk_blocking(timeout, phrase_time_limit, grammar, cancel_event, mic)
        
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

    def _listen_vosk_blocking(self, timeout: float, phrase_time_limit: float, grammar: list = None, cancel_event: asyncio.Event = None, mic=None) -> tuple[str | None, bytes | None]:
        """Local Vosk recognition loop. Returns (text, raw_audio_buffer)."""
        import sounddevice as sd
        audio_buffer = bytearray()
        try:
            if not self.model:
                logger.error("Vosk model is None in _listen_vosk_blocking")
                return None, None

            if grammar:
                grammar_json = json.dumps(grammar + ["[unk]"])
                rec = vosk.KaldiRecognizer(self.model, config.SAMPLERATE, grammar_json)
            else:
                rec = self.rec

            if not rec:
                logger.error("Vosk recognizer (rec) is None in _listen_vosk_blocking")
                return None, None

            # Use shared mic if provided, otherwise open own stream
            if mic:
                logger.info("Vosk is listening (shared stream)...")
                q = mic.subscribe()
                try:
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        if cancel_event and cancel_event.is_set():
                            logger.info("Vosk listening cancelled by event.")
                            break
                        
                        try:
                            # 0.1s wait to stay responsive to cancel_event
                            data = q.get(timeout=0.1)
                            # Convert float32 from sounddevice to int16 for Vosk
                            if data.dtype != np.int16:
                                data_int16 = (data * 32767).astype(np.int16)
                            else:
                                data_int16 = data
                            
                            chunk_bytes = data_int16.tobytes()
                            audio_buffer.extend(chunk_bytes)
                            
                            if rec.AcceptWaveform(chunk_bytes):
                                result = json.loads(rec.Result())
                                text = result.get("text", "")
                                if text:
                                    logger.info(f'Vosk Recognized: "{text}"')
                                    return text, bytes(audio_buffer)
                        except queue.Empty:
                            continue
                finally:
                    mic.unsubscribe(q)
            else:
                # Fallback to creating own stream (not recommended if shared mic exists)
                with sd.RawInputStream(samplerate=config.SAMPLERATE, blocksize=8000, dtype='int16',
                                    channels=1, device=config.MIC_DEVICE_INDEX) as stream:
                    logger.info("Vosk is listening (dedicated stream)...")
                    start_time = time.time()
                    while time.time() - start_time < timeout:
                        if cancel_event and cancel_event.is_set():
                            logger.info("Vosk listening cancelled by event.")
                            break
                        
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
        self, timeout: float = 10.0, phrase_time_limit: float = 10.0, grammar: list = None, validator: callable = None, cancel_event: asyncio.Event = None, mic=None
    ) -> str | None:
        """
        Listens for a command. 
        If mic is provided, it uses the shared stream.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._listen_blocking(timeout, phrase_time_limit, grammar, validator, cancel_event, mic)
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
