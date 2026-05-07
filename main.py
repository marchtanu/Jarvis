import asyncio
import logging
import sys
import numpy as np

import qasync
from PyQt6.QtWidgets import QApplication

from jarvis.core.config import config
from jarvis.core.event_bus import event_bus
from jarvis.audio.microphone import Microphone
from jarvis.audio.snap_detector import SnapDetector
from jarvis.audio.speech_recognition import SpeechRecognizer
from jarvis.core.state_machine import JarvisStateMachine
from jarvis.core.agent import JarvisAgent
from jarvis.gui.main_window import JarvisMainWindow

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("Jarvis")


async def audio_loop(mic: Microphone, snap_detector: SnapDetector,
                     window: JarvisMainWindow, debug_panel):
    """Continuously processes audio chunks for snap detection and waveform."""
    try:
        while True:
            if debug_panel.mic_enabled:
                chunk = mic.get_audio_chunk()
                if chunk is not None:
                    await snap_detector.process_audio(chunk)
                    window.feed_audio(chunk)
            await asyncio.sleep(0.001)
    except (asyncio.CancelledError, RuntimeError):
        logger.info("Audio loop stopped.")


async def main():
    logger.info("Starting Jarvis Assistant...")

    # ── Initialize Components ─────────────────────────────────────────────
    mic = Microphone()
    snap_detector = SnapDetector()
    speech_recognizer = SpeechRecognizer()

    agent = JarvisAgent()
    fsm = JarvisStateMachine(speech_recognizer, agent)

    # ── Build GUI ─────────────────────────────────────────────────────────
    window = JarvisMainWindow(fsm, mic)
    window.hide()  # GUI activates on "daddy home" command

    # ── Start FSM ─────────────────────────────────────────────────────────
    await fsm.start()

    # ── Calibrate mic (non-blocking) ──────────────────────────────────────
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, speech_recognizer.initialize)

    # ── Start Audio Hardware ──────────────────────────────────────────────
    mic.start()
    snap_detector.start()

    logger.info("Jarvis is ready.")
    logger.info(f"  Wake phrase    : '{config.WAKE_PHRASE}'")
    logger.info(f"  Shutdown phrase: '{config.SHUTDOWN_PHRASE}'")

    # ── Run Audio Loop ────────────────────────────────────────────────────
    try:
        await audio_loop(mic, snap_detector, window, window._debug_panel)
    except asyncio.CancelledError:
        pass
    finally:
        snap_detector.stop()
        mic.stop()
        logger.info("Jarvis shut down.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Jarvis Assistant")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        try:
            loop.run_until_complete(main())
        except KeyboardInterrupt:
            logger.info("Interrupted.")
        finally:
            if not loop.is_closed():
                loop.stop()
