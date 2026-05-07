import asyncio
import logging
from enum import Enum, auto
from .event_bus import event_bus
from .config import config

logger = logging.getLogger(__name__)


class State(Enum):
    IDLE = auto()
    SNAP_1_DETECTED = auto()
    ARMED = auto()
    LISTENING = auto()
    EXECUTING = auto()


class JarvisStateMachine:
    def __init__(self, speech_recognizer, command_registry):
        self.state = State.IDLE
        self.speech_recognizer = speech_recognizer
        self.command_registry = command_registry
        self.last_snap_time = 0.0

    async def start(self):
        event_bus.subscribe("SNAP_DETECTED", self.on_snap_detected)
        logger.info("Jarvis State Machine started in IDLE mode.")

    # process_audio is still here for snap_detector to call, but no
    # longer needs to feed chunks to the recognizer.
    async def process_audio(self, chunk) -> None:
        pass

    async def on_snap_detected(self, data: dict):
        """Handles SNAP_DETECTED events published by the snap detector."""
        current_time = data["time"]

        if self.state == State.IDLE:
            self.state = State.SNAP_1_DETECTED
            self.last_snap_time = current_time
            logger.info("State: IDLE → SNAP_1_DETECTED (snap 1 registered)")
            asyncio.create_task(self._snap_window_timeout())

        elif self.state == State.SNAP_1_DETECTED:
            gap = current_time - self.last_snap_time
            if gap <= config.SNAP_WINDOW_TIMEOUT:
                logger.info("=" * 40)
                logger.info("!!! DOUBLE SNAP DETECTED !!!")
                logger.info("=" * 40)
                logger.info(f"State: SNAP_1_DETECTED → ARMED (gap: {gap:.2f}s)")
                self.state = State.ARMED
                # Kick off listening as a background task so event loop stays free
                asyncio.create_task(self._enter_listening_mode())
            else:
                # Too slow — treat as a fresh first snap
                self.last_snap_time = current_time
                logger.info(f"Second snap too slow ({gap:.2f}s). Window reset.")

    async def _snap_window_timeout(self):
        await asyncio.sleep(config.SNAP_WINDOW_TIMEOUT)
        if self.state == State.SNAP_1_DETECTED:
            self.state = State.IDLE
            logger.info("State: SNAP_1_DETECTED → IDLE (window timed out)")

    async def _enter_listening_mode(self):
        self.state = State.LISTENING
        logger.info(f"State: ARMED → LISTENING")
        logger.info("Speak your command now...")
        print("\a", end="", flush=True)  # Beep

        text = await self.speech_recognizer.listen_for_command(
            timeout=config.COMMAND_TIMEOUT,
            phrase_time_limit=config.COMMAND_TIMEOUT,
        )

        if text:
            await self._execute_command(text)
        else:
            logger.info("No command recognized. Back to IDLE.")
            self.state = State.IDLE

    async def _execute_command(self, command_text: str):
        self.state = State.EXECUTING
        logger.info(f"State: LISTENING → EXECUTING (command: '{command_text}')")
        success = await self.command_registry.execute(command_text)
        if success:
            logger.info("Command executed successfully.")
        else:
            logger.warning(f"No command matched '{command_text}'.")
        self.state = State.IDLE
        logger.info("State: EXECUTING → IDLE")
