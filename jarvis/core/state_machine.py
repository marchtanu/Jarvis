import asyncio
import logging
from enum import Enum, auto
from .event_bus import event_bus
from .config import config

logger = logging.getLogger(__name__)


class State(Enum):
    STANDBY = auto()
    SNAP_DETECTED = auto()       # Snap 1 heard, waiting for snap 2
    WAITING_WAKE_WORD = auto()   # Double snap done, listening for "daddy home"
    COMMAND_MODE = auto()        # Activated, looping command listener
    PROCESSING = auto()          # Executing a command
    SLEEP = auto()               # Visible GUI, waiting for 2 snaps (to wake or exit)
    SHUTDOWN = auto()            # Terminating program


STATE_LABELS = {
    State.STANDBY:          "Standby",
    State.SNAP_DETECTED:    "Snap Detected",
    State.WAITING_WAKE_WORD: "Say 'Daddy Home'",
    State.COMMAND_MODE:     "Command Mode",
    State.PROCESSING:       "Processing",
    State.SLEEP:            "Sleeping",
    State.SHUTDOWN:         "Shutting Down",
}


class JarvisStateMachine:
    def __init__(self, speech_recognizer, agent):
        self.state = State.STANDBY
        self.speech_recognizer = speech_recognizer
        self.agent = agent
        self.last_snap_time = 0.0

    async def start(self):
        event_bus.subscribe("SNAP_DETECTED", self.on_snap_detected)
        event_bus.subscribe("GESTURE_DETECTED", self.on_gesture_detected)
        event_bus.subscribe("MOTION_DETECTED", self.on_motion_detected)
        await self._publish_state("Jarvis initialized. Waiting for activation.")
        logger.info("State Machine started in STANDBY.")

    async def _publish_state(self, message: str = ""):
        await event_bus.publish("STATE_CHANGED", {
            "state": self.state.name,
            "label": STATE_LABELS[self.state],
            "message": message,
        })

    async def on_snap_detected(self, data: dict):
        current_time = data["time"]

        if self.state in (State.STANDBY, State.SLEEP):
            self.state = State.SNAP_DETECTED
            self.last_snap_time = current_time
            await self._publish_state("Snap 1 — snap again quickly!")
            asyncio.create_task(self._snap_timeout())

        elif self.state == State.SNAP_DETECTED:
            gap = current_time - self.last_snap_time
            if gap <= config.SNAP_WINDOW_TIMEOUT:
                asyncio.create_task(self._enter_waiting_wake_word())
            else:
                self.last_snap_time = current_time
                await self._publish_state("Too slow! Snap again.")

    async def _snap_timeout(self):
        await asyncio.sleep(config.SNAP_WINDOW_TIMEOUT)
        if self.state == State.SNAP_DETECTED:
            self.state = State.STANDBY
            await self._publish_state("Window expired. Back to standby.")

    async def _enter_waiting_wake_word(self):
        self.state = State.WAITING_WAKE_WORD
        await self._publish_state(f"Say '{config.WAKE_PHRASE}' to activate!")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": f"Double snap detected! Say \"{config.WAKE_PHRASE}\" to activate.",
            "type": "info",
        })

        text = await self.speech_recognizer.listen_for_command(
            timeout=config.WAKE_WORD_TIMEOUT,
            phrase_time_limit=config.WAKE_WORD_TIMEOUT,
        )

        if text:
            await event_bus.publish("SPEECH_RECOGNIZED", {"text": text})

        if text and config.WAKE_PHRASE in text:
            await self._enter_command_mode()
        elif text and config.EXIT_PHRASE in text:
            await self._exit_application()
        else:
            # Revert to appropriate state (SLEEP or STANDBY)
            # If the window is currently shown, we were likely in SLEEP
            await event_bus.publish("JARVIS_RESPONSE", {
                "text": f"Phrase '{text}' not recognized. Returning to standby.",
                "type": "warning"
            })
            self.state = State.STANDBY # Safe default
            await self._publish_state("Waiting for signal...")

    async def _enter_command_mode(self):
        self.state = State.COMMAND_MODE
        await self._publish_state("Command mode active! How can I help?")
        await event_bus.publish("HOME_ACTIVATED", {})
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Command mode activated. How can I help you, sir?",
            "type": "success",
        })

        # Continuous command loop
        while self.state == State.COMMAND_MODE:
            text = await self.speech_recognizer.listen_for_command(
                timeout=config.COMMAND_TIMEOUT,
                phrase_time_limit=10.0,
            )

            if not text:
                await event_bus.publish("JARVIS_RESPONSE", {
                    "text": "I didn't catch that. Still listening...",
                    "type": "info",
                })
                continue

            await event_bus.publish("SPEECH_RECOGNIZED", {"text": text})

            if config.EXIT_PHRASE in text:
                await self._exit_application()
                return

            if config.SHUTDOWN_PHRASE in text:
                await self._enter_sleep_mode()
                return

            if "help" in text.lower():
                from jarvis.skills.information import get_help
                response = await get_help()
                await event_bus.publish("JARVIS_RESPONSE", {"text": response, "type": "response"})
                continue

            await self._process_command(text)

    async def _process_command(self, command_text: str):
        self.state = State.PROCESSING
        await self._publish_state(f"Processing: '{command_text}'")

        # Let the AI Brain handle the intent and routing
        response = await self.agent.execute(command_text)

        await event_bus.publish("COMMAND_EXECUTED", {
            "command": command_text,
            "response": response,
        })

        if response:
            await event_bus.publish("JARVIS_RESPONSE", {"text": response, "type": "response"})
        else:
            msg = "I'm sorry, I couldn't process that."
            await event_bus.publish("JARVIS_RESPONSE", {"text": msg, "type": "warning"})

        self.state = State.COMMAND_MODE
        await self._publish_state("Ready for next command.")

    async def _enter_sleep_mode(self):
        """Enter Sleep mode (GUI stays visible)."""
        self.state = State.SLEEP
        await self._publish_state("Sleeping...")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Goodnight. Standing by. Snap twice to wake or exit.",
            "type": "shutdown",
        })

    async def _exit_application(self):
        """Shut down the program and close the GUI."""
        self.state = State.SHUTDOWN
        await self._publish_state("Shutting down...")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Terminating systems. Farewell.",
            "type": "shutdown",
        })
        await asyncio.sleep(1.0)
        await event_bus.publish("APP_EXIT", {})

    # Called by debug panel to simulate events
    async def simulate_snap(self):
        import time
        await self.on_snap_detected({"time": time.time()})

    async def simulate_wake_phrase(self):
        if self.state in (State.WAITING_WAKE_WORD, State.SNAP_DETECTED, State.STANDBY):
            asyncio.create_task(self._enter_command_mode())

    async def simulate_shutdown(self):
        if self.state == State.COMMAND_MODE:
            asyncio.create_task(self._exit_application())

    # ── Vision Handlers ───────────────────────────────────────────────────────

    async def on_gesture_detected(self, data: dict):
        gesture = data.get("gesture")
        confidence = data.get("confidence", 0.0)

        if confidence < 0.7:
            return

        if gesture == "open_palm":
            # Wake up Jarvis
            if self.state in (State.STANDBY, State.SLEEP, State.SNAP_DETECTED):
                asyncio.create_task(self._enter_command_mode())
        elif gesture == "fist":
            # Go to sleep
            if self.state == State.COMMAND_MODE:
                asyncio.create_task(self._enter_sleep_mode())
        
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": f"[Vision] Detected gesture: {gesture} ({confidence:.2f})",
            "type": "info"
        })

    async def on_motion_detected(self, data: dict):
        motion = data.get("motion")
        confidence = data.get("confidence", 0.0)
        
        if confidence < 0.4:
            return
            
        # For now, just echo motion to the UI
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": f"[Vision] Detected motion: {motion} ({confidence:.2f})",
            "type": "info"
        })
