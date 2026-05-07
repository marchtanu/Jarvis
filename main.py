import asyncio
import logging
import sys
from jarvis.core.config import config
from jarvis.audio.microphone import Microphone
from jarvis.audio.snap_detector import SnapDetector
from jarvis.audio.speech_recognition import SpeechRecognizer
from jarvis.core.state_machine import JarvisStateMachine
from jarvis.commands.registry import CommandRegistry
from jarvis.commands.actions import activate_home_mode, sleep_mode, system_status

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Jarvis")


async def main():
    logger.info("Initializing Jarvis System...")

    mic = Microphone()
    snap_detector = SnapDetector()
    speech_recognizer = SpeechRecognizer()

    # Calibrate microphone against ambient noise at startup
    speech_recognizer.initialize()

    registry = CommandRegistry()
    registry.register("daddy home", activate_home_mode)
    registry.register("jarvis sleep", sleep_mode)
    registry.register("status report", system_status)
    registry.register("system status", system_status)

    fsm = JarvisStateMachine(speech_recognizer, registry)
    await fsm.start()

    mic.start()
    snap_detector.start()

    logger.info("Jarvis is ready. Perform 2 snaps to activate.")
    logger.info(f"  Snap window    : {config.SNAP_WINDOW_TIMEOUT}s")
    logger.info(f"  Command timeout: {config.COMMAND_TIMEOUT}s")
    logger.info(f"  Commands       : {list(registry.commands.keys())}")

    try:
        while True:
            chunk = mic.get_audio_chunk()
            if chunk is not None:
                await snap_detector.process_audio(chunk)
            await asyncio.sleep(0.001)

    except KeyboardInterrupt:
        logger.info("Shutting down Jarvis...")
    finally:
        snap_detector.stop()
        mic.stop()


if __name__ == "__main__":
    asyncio.run(main())
