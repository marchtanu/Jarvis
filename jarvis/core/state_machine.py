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

# Behavioral States from Vision Subsystem
class BehavioralState(Enum):
    USER_PRESENT = auto()
    USER_ENGAGED = auto()
    USER_DISTRACTED = auto()
    USER_FOCUSED = auto()
    USER_IDLE = auto()
    USER_ABSENT = auto()



class JarvisStateMachine:
    def __init__(self, speech_recognizer, agent):
        self.state = State.STANDBY
        self.behavioral_state = BehavioralState.USER_ABSENT
        self.speech_recognizer = speech_recognizer
        self.agent = agent
        self.last_snap_time = 0.0
        
        self.current_gaze = "unknown"
        self.current_gesture = "none"
        self.last_open_palm_time = 0.0
        self.last_pause_time = 0.0
        self.last_exit_time = 0.0
        
        self.next_command_is_search = False
        self.search_prompt_given = False

    async def start(self):
        event_bus.subscribe("SNAP_DETECTED", self.on_snap_detected)
        event_bus.subscribe("GESTURE_DETECTED", self.on_gesture_detected)
        event_bus.subscribe("MOTION_DETECTED", self.on_motion_detected)
        event_bus.subscribe("ATTENTION_CHANGED", self.on_attention_changed)
        event_bus.subscribe("GAZE_CHANGED", self.on_gaze_changed)
        event_bus.subscribe("CANCEL_ALL", self.on_cancel_all)
        
        asyncio.create_task(self._volume_control_loop())
        
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
                if not self.next_command_is_search:
                    await event_bus.publish("JARVIS_RESPONSE", {
                        "text": "I didn't catch that. Still listening...",
                        "type": "info",
                    })
                else:
                    self.next_command_is_search = False
                    self.search_prompt_given = False
                    await self._publish_state("Search cancelled (timeout).")
                continue

            await event_bus.publish("SPEECH_RECOGNIZED", {"text": text})

            if self.next_command_is_search:
                text = f"search {text}"
                self.next_command_is_search = False
                self.search_prompt_given = False

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

    async def on_gaze_changed(self, data: dict):
        self.current_gaze = data.get("direction", "unknown")

    async def on_gesture_detected(self, data: dict):
        gesture = data.get("gesture")
        confidence = data.get("confidence", 0.0)

        if confidence < 0.7:
            return

        self.current_gesture = gesture

        import time
        current_time = time.time()

        # 1. Exit command: eye look directly at camera + open palm -> fist within 1s
        if self.state in (State.SLEEP, State.STANDBY):
            if gesture == "open_palm":
                self.last_open_palm_time = current_time
            elif gesture == "fist":
                if (current_time - self.last_open_palm_time <= 1.0) and self.current_gaze == "center":
                    if current_time - getattr(self, "last_exit_time", 0.0) > 2.0:
                        self.last_exit_time = current_time
                        asyncio.create_task(self._exit_application())

        # 2. Search with voice (thumb_index_up)
        if gesture == "thumb_index_up":
            if not getattr(self, "search_prompt_given", False):
                self.search_prompt_given = True
                self.next_command_is_search = True
                await self._publish_state("Listening for search query...")
                asyncio.create_task(event_bus.publish("JARVIS_RESPONSE", {
                    "text": "Search mode active. What would you like to find?", 
                    "type": "info"
                }))
                # If Jarvis is asleep, wake him up to listen
                if self.state not in (State.COMMAND_MODE, State.PROCESSING):
                    asyncio.create_task(self._enter_command_mode())
                
        # 3. Fist to pause music
        if gesture == "fist":
            if current_time - getattr(self, "last_pause_time", 0.0) > 2.0:
                self.last_pause_time = current_time
                import pyautogui
                pyautogui.press('playpause')
                asyncio.create_task(event_bus.publish("JARVIS_RESPONSE", {"text": "Media paused/played.", "type": "info"}))

    async def _volume_control_loop(self):
        import pyautogui
        # Background task for continuous volume control
        while True:
            # 3. Volume up: three_fingers_up
            if self.current_gesture == "three_fingers_up":
                pyautogui.press('volumeup')
                pyautogui.press('volumeup') # Approximate +2%
            
            # 4. Volume down: three_fingers_down
            elif self.current_gesture == "three_fingers_down":
                pyautogui.press('volumedown')
                pyautogui.press('volumedown')
                
            await asyncio.sleep(0.5)



    async def on_cancel_all(self, data: dict):
        """Triggered by two-hand open palm gesture. Resets active processing."""
        if self.state == State.PROCESSING:
            self.state = State.COMMAND_MODE
            await self._publish_state("All operations cancelled.")
            await event_bus.publish("JARVIS_RESPONSE", {
                "text": "Operations cancelled by user gesture.",
                "type": "warning"
            })
        elif self.state == State.WAITING_WAKE_WORD:
            self.state = State.STANDBY
            await self._publish_state("Cancelled. Returning to standby.")

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

    async def on_attention_changed(self, data: dict):
        state_str = data.get("attention_state")
        try:
            new_state = BehavioralState[state_str]
            self.behavioral_state = new_state
            logger.debug(f"Behavioral state updated to: {self.behavioral_state.name}")
        except KeyError:
            logger.warning(f"Unknown attention state: {state_str}")

