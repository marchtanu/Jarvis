import asyncio
import logging
import sys
import os

# Set matplotlib backend to Agg to prevent hangs during mediapipe import
os.environ['MPLBACKEND'] = 'Agg'

import warnings
# Silence Protobuf deprecation warning from Mediapipe
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.symbol_database")

import numpy as np

import qasync
from PyQt6.QtWidgets import QApplication

from auhip.core.config import config
from auhip.core.event_bus import event_bus
from auhip.audio.microphone import Microphone
from auhip.audio.snap_detector import SnapDetector
from auhip.audio.speech_recognition import SpeechRecognizer
from auhip.core.state_machine import AuhipStateMachine
from auhip.core.agent import AuhipAgent
from auhip.gui.main_window import AuhipMainWindow
from auhip.vision.worker import VisionWorker

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("auhip")


async def audio_loop(mic: Microphone, snap_detector: SnapDetector,
                     window: AuhipMainWindow, debug_panel):
    """Continuously processes audio chunks for snap detection and waveform."""
    try:
        while True:
            if debug_panel.mic_enabled:
                chunk = mic.get_audio_chunk()
                if chunk is not None:
                    await snap_detector.process_audio(chunk)
                    window.feed_audio(chunk)
            await asyncio.sleep(0.01)
    except (asyncio.CancelledError, RuntimeError):
        logger.info("Audio loop stopped.")


async def main():
    logger.info("Starting auhip Assistant...")

    # ── Initialize Components ─────────────────────────────────────────────
    mic = Microphone()
    snap_detector = SnapDetector()
    speech_recognizer = SpeechRecognizer()

    agent = AuhipAgent()
    fsm = AuhipStateMachine(speech_recognizer, agent, mic, snap_detector)
    vision_worker = VisionWorker()

    # ── Build GUI ─────────────────────────────────────────────────────────
    window = AuhipMainWindow(fsm, mic, vision_worker)
    window.hide()  # GUI activates on "daddy home" command

    # ── Start FSM ─────────────────────────────────────────────────────────
    await fsm.start()

    # ── Calibrate mic (non-blocking) ──────────────────────────────────────
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, speech_recognizer.initialize)

    # ── Start Audio Hardware ──────────────────────────────────────────────
    mic.start()
    snap_detector.start()
    
    # Connect mic to GUI for hardware switching
    window.debug_panel.set_mic_instance(mic)

    logger.info("auhip is ready.")
    logger.info(f"  Wake phrase    : '{config.WAKE_PHRASE}'")
    logger.info(f"  Shutdown phrase: '{config.SHUTDOWN_PHRASE}'")

    # ── Run Audio Loop ────────────────────────────────────────────────────
    try:
        await audio_loop(mic, snap_detector, window, window.debug_panel)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.exception(f"Unexpected error in main loop: {e}")
    finally:
        await fsm.stop()
        snap_detector.stop()
        mic.stop()
        vision_worker.stop()
        logger.info("auhip shut down.")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("auhip Assistant")

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
