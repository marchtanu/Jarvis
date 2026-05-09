import asyncio
import logging
import time
import threading
import pyautogui
from enum import Enum, auto
from .event_bus import event_bus
from .config import config

logger = logging.getLogger(__name__)


class State(Enum):
    STANDBY = auto()
    SNAP_DETECTED = auto()       # Snap 1 heard, waiting for snap 2
    WAITING_WAKE_WORD = auto()   # Double snap done, listening for "daddy home"
    VOICE_MODE = auto()          # Activated — continuous voice command loop
    PROCESSING = auto()          # Executing a command (sub-state of VOICE_MODE)
    CAMERA_MODE = auto()         # Gesture-driven mode — voice disabled by default
    CONTROL_MODE = auto()        # Cursor/mouse control mode
    SLEEP = auto()               # Passive — waiting for 2 snaps (wake or exit)
    SHUTDOWN = auto()            # Terminating


STATE_LABELS = {
    State.STANDBY:          "Standby",
    State.SNAP_DETECTED:    "Snap Detected",
    State.WAITING_WAKE_WORD: "Say 'Daddy Home'",
    State.VOICE_MODE:       "Voice Mode",
    State.PROCESSING:       "Processing",
    State.CAMERA_MODE:      "Camera Mode",
    State.CONTROL_MODE:     "Control Mode",
    State.SLEEP:            "Sleeping",
    State.SHUTDOWN:         "Shutting Down",
}


class BehavioralState(Enum):
    USER_PRESENT = auto()
    USER_ENGAGED = auto()
    USER_DISTRACTED = auto()
    USER_FOCUSED = auto()
    USER_IDLE = auto()
    USER_ABSENT = auto()


class JarvisStateMachine:
    def __init__(self, speech_recognizer, agent, mic=None, snap_detector=None):
        self.state = State.STANDBY
        self.behavioral_state = BehavioralState.USER_ABSENT
        self.speech_recognizer = speech_recognizer
        self.agent = agent
        self.mic = mic
        self.snap_detector = snap_detector

        # Task tracking for cleanup
        self._voice_task = None
        self._active_tasks = set()
        
        # Cooldowns
        self.last_snap_time = 0.0
        self.last_open_palm_time = 0.0
        self.last_exit_time = 0.0
        self._last_exit_gesture_time = 0.0  # Shared for peace_sign / rock_sign exits
        self._last_play_pause_time = 0.0
        self._last_track_time = 0.0
        self._last_volume_time = 0.0
        self.last_camera_open_palm_time = 0.0

        # Control mode state
        self._temp_voice_active = False  # While one_index_up is held in CAMERA_MODE
        self._temp_voice_cancel_event = threading.Event()
        self._voice_cancel_event = threading.Event()

    # ── Startup ──────────────────────────────────────────────────────────────

    async def start(self):
        event_bus.subscribe("SNAP_DETECTED", self.on_snap_detected)
        event_bus.subscribe("GESTURE_DETECTED", self.on_gesture_detected)
        event_bus.subscribe("MOTION_DETECTED", self.on_motion_detected)
        event_bus.subscribe("ATTENTION_CHANGED", self.on_attention_changed)
        event_bus.subscribe("GAZE_CHANGED", self.on_gaze_changed)
        event_bus.subscribe("CANCEL_ALL", self.on_cancel_all)

        event_bus.subscribe("ENTER_CAMERA_MODE", self._on_enter_camera_mode)
        event_bus.subscribe("ENTER_CONTROL_MODE", self._on_enter_control_mode)
        event_bus.subscribe("ENTER_SLEEP_MODE", self._on_enter_sleep_mode)
        event_bus.subscribe("EXIT_SUB_MODE", self._on_exit_sub_mode)

        # Temp voice in Camera mode (raised by VisionWorker)
        event_bus.subscribe("TEMP_VOICE_START", self._on_temp_voice_start)
        event_bus.subscribe("TEMP_VOICE_END", self._on_temp_voice_end)

        await self._publish_state("Jarvis initialized. Waiting for activation.")
        logger.info("State Machine started in STANDBY.")

    async def stop(self):
        """Cancel all pending tasks for clean shutdown."""
        self._stop_voice_loop()
        if self._voice_task:
            self._voice_task.cancel()
        for task in self._active_tasks:
            if not task.done():
                task.cancel()
        logger.info("State Machine cleanup complete.")

    def _stop_voice_loop(self):
        """Signal the voice loop to terminate immediately."""
        self._voice_cancel_event.set()
        logger.debug("Voice loop stop signal sent.")

    # ── State Publishing ──────────────────────────────────────────────────────

    async def _publish_state(self, message: str = ""):
        await event_bus.publish("STATE_CHANGED", {
            "state": self.state.name,
            "label": STATE_LABELS[self.state],
            "message": message,
        })
        await event_bus.publish("MODE_CHANGED", {"mode": self.state.name})

    # ── Snap Detection ────────────────────────────────────────────────────────

    async def on_snap_detected(self, data: dict):
        current_time = data["time"]

        # Snaps accepted in STANDBY and SLEEP only
        if self.state in (State.STANDBY, State.SLEEP):
            self.pre_snap_state = self.state # Track if we came from SLEEP
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
            # Return to whichever state we came from (STANDBY or SLEEP)
            fallback = getattr(self, 'pre_snap_state', State.STANDBY)
            self.state = fallback
            if self.snap_detector:
                self.snap_detector.start() # Ensure detector is running
            label = "Sleeping..." if fallback == State.SLEEP else "Window expired. Back to standby."
            await self._publish_state(label)

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
            grammar=[config.WAKE_PHRASE, config.EXIT_PHRASE],
            validator=self.agent.is_valid_command,
            mic=self.mic
        )

        if text:
            await event_bus.publish("SPEECH_RECOGNIZED", {"text": text})

        if text and config.WAKE_PHRASE in text.lower():
            await self._enter_voice_mode()
        elif text and (text.strip().lower() == config.EXIT_PHRASE or "terminate program" in text.lower()):
            # Only allow exit if we came from SLEEP mode as per user request
            if getattr(self, 'pre_snap_state', None) == State.SLEEP:
                logger.info(f"Exit command accepted from Sleep Mode.")
                await self._exit_application()
            else:
                await event_bus.publish("JARVIS_RESPONSE", {
                    "text": "Exit command ignored. Program can only be closed from Sleep Mode.",
                    "type": "warning"
                })
                self.state = State.STANDBY
                await self._publish_state("Returning to standby.")
        else:
            await event_bus.publish("JARVIS_RESPONSE", {
                "text": f"Phrase '{text}' not recognized. Returning to standby.",
                "type": "warning"
            })
            self.state = State.STANDBY
            await self._publish_state("Waiting for signal...")

    # ── Voice Mode ────────────────────────────────────────────────────────────

    async def _enter_voice_mode(self):
        # Cancel any existing voice task before starting new one
        if self._voice_task and not self._voice_task.done():
            self._voice_task.cancel()
            try: await self._voice_task
            except asyncio.CancelledError: pass

        self._voice_task = asyncio.current_task()
        self.state = State.VOICE_MODE
        if self.snap_detector:
            self.snap_detector.stop() # Silence snaps during voice interaction
        await event_bus.publish("SET_VISION_MODE", {"mode": "none"}) # Optimization: Stop camera hardware
        await self._publish_state("Voice Mode — How can I help?")
        await event_bus.publish("HOME_ACTIVATED", {})
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Voice mode activated. How can I help you, sir?",
            "type": "success",
        })

        self._voice_cancel_event.clear()
        try:
            # Continuous voice command loop — VOICE_MODE only.
            while self.state == State.VOICE_MODE:
                text = await self.speech_recognizer.listen_for_command(
                    timeout=config.COMMAND_TIMEOUT,
                    phrase_time_limit=10.0,
                    validator=self.agent.is_valid_command,
                    cancel_event=self._voice_cancel_event,
                    mic=self.mic
                )
                
                if self._voice_cancel_event.is_set():
                    break

                if not text:
                    await event_bus.publish("JARVIS_RESPONSE", {
                        "text": "I didn't catch that. Still listening...",
                        "type": "info",
                    })
                    continue

                await event_bus.publish("SPEECH_RECOGNIZED", {"text": text})

                if text and (text.strip().lower() == config.EXIT_PHRASE or "terminate program" in text.lower()):
                    await event_bus.publish("JARVIS_RESPONSE", {
                        "text": "Exit command ignored. You must put me to sleep ('goodbye jojo') before exiting.",
                        "type": "warning"
                    })
                    continue

                if config.SHUTDOWN_PHRASE in text or config.GOODNIGHT_PHRASE in text.lower():
                    await self._on_enter_sleep_mode({})
                    return

                # Delegate to agent (which publishes ENTER_CAMERA_MODE / ENTER_CONTROL_MODE etc.)
                await self._process_command(text)

        except asyncio.CancelledError:
            logger.debug("Voice mode loop cancelled.")
            raise
        finally:
            logger.info(f"Voice mode loop ended. Current state: {self.state.name}")

    async def _process_command(self, command_text: str):
        prev_state = self.state
        self.state = State.PROCESSING
        await self._publish_state(f"Processing: '{command_text}'")

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

        # Return to previous state if no new state was set by the command/agent
        if self.state == State.PROCESSING:
            self.state = prev_state
            if self.state == State.VOICE_MODE:
                await self._publish_state("Ready for next command.")
                # Ensure voice loop is running if we return to voice mode
                if not self._voice_task or self._voice_task.done():
                    self._voice_task = asyncio.create_task(self._voice_loop())
            else:
                await self._publish_state(f"Back to {self.state.name}.")

    # ── Camera Mode ───────────────────────────────────────────────────────────

    async def _on_enter_camera_mode(self, data: dict):
        """Triggered by voice command 'vision up / open camera'."""
        if self.state not in (State.VOICE_MODE, State.PROCESSING, State.CONTROL_MODE):
            return
        
        self._stop_voice_loop()
        self.state = State.CAMERA_MODE
        if self.snap_detector:
            self.snap_detector.stop() # Silence snaps during vision control
        await self._publish_state("Camera Mode — gesture control active.")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Camera mode activated. Raise index finger to speak.",
            "type": "success",
        })
        # Signal VisionWorker to enter camera mode processing
        await event_bus.publish("SET_VISION_MODE", {"mode": "camera"})

    async def _on_temp_voice_start(self, data: dict):
        """One index finger raised in Camera Mode — temporarily enable voice."""
        if self.state != State.CAMERA_MODE:
            return
        if not self._temp_voice_active:
            self._temp_voice_active = True
            self._temp_voice_cancel_event.clear()
            logger.info("Temp voice listening activated in Camera Mode.")
            asyncio.create_task(self._temp_voice_listen())

    async def _on_temp_voice_end(self, data: dict):
        """Index finger lowered — end temporary voice listening."""
        if self._temp_voice_active:
            self._temp_voice_active = False
            self._temp_voice_cancel_event.set()
            logger.info("Temp voice listening deactivated.")

    async def _temp_voice_listen(self):
        """Looping voice capture while index finger is raised in Camera Mode."""
        while self._temp_voice_active and self.state == State.CAMERA_MODE:
            await event_bus.publish("JARVIS_RESPONSE", {
                "text": "Listening...",
                "type": "info",
            })
            text = await self.speech_recognizer.listen_for_command(
                timeout=5.0,
                phrase_time_limit=5.0,
                validator=self.agent.is_valid_command,
                cancel_event=self._temp_voice_cancel_event,
                mic=self.mic
            )
            
            if self._temp_voice_cancel_event.is_set():
                logger.info("Ignoring temp voice result — finger was lowered.")
                break

            if text and self.state == State.CAMERA_MODE:
                await event_bus.publish("SPEECH_RECOGNIZED", {"text": text})
                if config.SHUTDOWN_PHRASE in text or "goodnight" in text.lower():
                    await self._on_enter_sleep_mode({})
                    break
                elif any(kw in text.lower() for kw in ["camera off", "vision off", "close camera", "stop camera"]):
                    await self._on_exit_sub_mode({})
                    break
                else:
                    logger.info(f"Processing temp voice command: {text}")
                    await self._process_command(text)
                    # Loop continues if we are still in CAMERA_MODE
            
            # Small delay before next listen to avoid tight loops
            await asyncio.sleep(0.2)

    # ── Control Mode ──────────────────────────────────────────────────────────

    async def _on_enter_control_mode(self, data: dict):
        """Triggered by voice command 'control on'."""
        if self.state not in (State.VOICE_MODE, State.PROCESSING):
            return
        
        self._stop_voice_loop()
        self.state = State.CONTROL_MODE
        if self.snap_detector:
            self.snap_detector.stop() # Silence snaps during cursor control
        await self._publish_state("Control Mode — cursor active.")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Control mode activated. Use hand to move cursor. Rock sign to exit.",
            "type": "success",
        })
        await event_bus.publish("SET_VISION_MODE", {"mode": "control"})

    # ── Sub-mode Exit ─────────────────────────────────────────────────────────

    async def _on_exit_sub_mode(self, data: dict):
        """Return from CONTROL_MODE to CAMERA_MODE, or CAMERA_MODE back to VOICE_MODE."""
        if self.state == State.CONTROL_MODE:
            logger.info("Exiting Control Mode -> Falling back to Camera Mode")
            await self._on_temp_voice_end({}) # Cleanup any lingering temp voice
            await self._on_enter_camera_mode({})
        elif self.state == State.CAMERA_MODE:
            logger.info("Exiting Camera Mode -> Returning to Voice Mode")
            await self._on_temp_voice_end({}) # Cleanup
            
            # Stop vision FIRST to prevent race condition detections
            await event_bus.publish("SET_VISION_MODE", {"mode": "none"})
            
            self.state = State.VOICE_MODE
            if self.snap_detector:
                self.snap_detector.stop()  # Keep snaps silent during voice
            await self._publish_state("Voice Mode — returned from sub-mode.")
            await event_bus.publish("JARVIS_RESPONSE", {
                "text": "Exited Camera Mode. Back to voice mode.",
                "type": "info",
            })
            # Re-enter the voice loop
            asyncio.create_task(self._enter_voice_mode())

    # ── Sleep Mode ────────────────────────────────────────────────────────────

    async def _on_enter_sleep_mode(self, data: dict):
        self._stop_voice_loop()
        self.state = State.SLEEP
        if self.snap_detector:
            self.snap_detector.start() # Ensure snaps are active to wake up
        await self._publish_state("Sleeping...")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Goodnight. Standing by. Snap twice to wake or exit.",
            "type": "shutdown",
        })
        # Low-power camera mode for emergency gesture
        await event_bus.publish("SET_VISION_MODE", {"mode": "sleep"})

    # ── Shutdown ──────────────────────────────────────────────────────────────

    async def _exit_application(self):
        self.state = State.SHUTDOWN
        await self._publish_state("Shutting down...")
        await event_bus.publish("JARVIS_RESPONSE", {
            "text": "Terminating systems. Farewell.",
            "type": "shutdown",
        })
        await asyncio.sleep(1.0)
        await event_bus.publish("APP_EXIT", {})

    # ── Global Gesture Handler ────────────────────────────────────────────────

    async def on_gesture_detected(self, data: dict):
        gesture = data.get("gesture")
        confidence = data.get("confidence", 0.0)

        if confidence < 0.7:
            return

        self.current_gesture = gesture
        logger.info(f"Gesture detected: {gesture} (conf: {confidence:.2f}, State: {self.state.name})")
        current_time = time.time()

        # ── Emergency Exit: open_palm → fist (SLEEP MODE ONLY) ────────────────
        if self.state == State.SLEEP:
            if gesture == "open_palm":
                self.last_open_palm_time = current_time
            elif gesture == "fist":
                palm_age = current_time - self.last_open_palm_time
                if 0.1 < palm_age <= 1.0:
                    exit_cooldown = current_time - self.last_exit_time
                    if exit_cooldown > 5.0:
                        self.last_exit_time = current_time
                        logger.info("Emergency exit gesture triggered in Sleep Mode.")
                        asyncio.create_task(self._exit_application())
                        return

        # ── CAMERA MODE gestures ──────────────────────────────────────────────
        if self.state == State.CAMERA_MODE:
            if gesture == "rock_sign":
                exit_cooldown = current_time - self._last_exit_gesture_time
                if exit_cooldown > 2.5:
                    self._last_exit_gesture_time = current_time
                    logger.info(f"Exit gesture '{gesture}' triggered in Camera Mode.")
                    asyncio.create_task(self._on_exit_sub_mode({}))
                    return

            await self._handle_camera_gesture(gesture, current_time)

        # ── CONTROL MODE: rock_sign exits back to Camera Mode ────────────────
        elif self.state == State.CONTROL_MODE:
            if gesture == "rock_sign":
                exit_cooldown = current_time - self._last_exit_gesture_time
                if exit_cooldown > 2.5:
                    self._last_exit_gesture_time = current_time
                    logger.info("Exit gesture 'rock_sign' triggered in Control Mode.")
                    asyncio.create_task(self._on_exit_sub_mode({}))

    async def _handle_camera_gesture(self, gesture: str, current_time: float):
        """Routes gestures valid only in CAMERA_MODE."""

        # Volume Up: Static pose (three_fingers_up) OR rapid shake
        if gesture in ("three_fingers_up", "shake_up"):
            vol_cooldown = current_time - self._last_volume_time
            if vol_cooldown > 0.2: 
                self._last_volume_time = current_time
                pyautogui.press('volumeup')
                asyncio.create_task(event_bus.publish("LAST_COMMAND", {"label": "🔊 Volume Up"}))
            return

        # Volume Down: Static pose (three_fingers_down) OR rapid shake
        elif gesture in ("three_fingers_down", "shake_down"):
            vol_cooldown = current_time - self._last_volume_time
            if vol_cooldown > 0.2:
                self._last_volume_time = current_time
                pyautogui.press('volumedown')
                asyncio.create_task(event_bus.publish("LAST_COMMAND", {"label": "🔉 Volume Down"}))
            return

        # Play/Pause: open_palm → fist sequence
        if gesture == "open_palm":
            self.last_camera_open_palm_time = current_time
            logger.debug("Palm detected for play/pause.")

        elif gesture == "fist":
            palm_age = current_time - self.last_camera_open_palm_time
            if 0.1 < palm_age <= 2.5:
                pause_cooldown = current_time - self._last_play_pause_time
                if pause_cooldown > 1.2:
                    self._last_play_pause_time = current_time
                    self.last_camera_open_palm_time = 0 # Reset
                    pyautogui.press('playpause')
                    asyncio.create_task(event_bus.publish("LAST_COMMAND", {"label": "⏯ Play / Pause"}))
                    asyncio.create_task(event_bus.publish("JARVIS_RESPONSE", {
                        "text": "Media toggled.",
                        "type": "info"
                    }))

        # Track skipping: 3 fingers pointing left/right
        elif gesture == "three_fingers_right":
            track_cooldown = current_time - self._last_track_time
            if track_cooldown > 1.5:
                self._last_track_time = current_time
                pyautogui.press('nexttrack')
                asyncio.create_task(event_bus.publish("LAST_COMMAND", {"label": "⏭⏭ Next Track"}))
                asyncio.create_task(event_bus.publish("JARVIS_RESPONSE", {
                    "text": "Next track.", "type": "info"
                }))
        elif gesture == "three_fingers_left":
            track_cooldown = current_time - self._last_track_time
            if track_cooldown > 1.5:
                self._last_track_time = current_time
                pyautogui.press('prevtrack')
                asyncio.create_task(event_bus.publish("LAST_COMMAND", {"label": "⏮⏮ Prev Track"}))
                asyncio.create_task(event_bus.publish("JARVIS_RESPONSE", {
                    "text": "Previous track.", "type": "info"
                }))

    async def on_motion_detected(self, data: dict):
        motion = data.get("motion")
        confidence = data.get("confidence", 0.0)

        if confidence < 0.4:
            return

        # Motion gestures only active in CAMERA_MODE
        if self.state != State.CAMERA_MODE:
            return

        # Motion gestures are processed here, but currently next/prev track 
        # have been moved to static gestures (three_fingers_left/right).
        pass

    # ── Volume Control Loop (Camera Mode) ────────────────────────────────────
    # NOTE: Removed _volume_control_loop — volume is handled via shake_up/shake_down
    # gestures from GestureEngine which are routed through _handle_camera_gesture.
    # The old loop caused duplicate volume presses when holding three_fingers_up/down.

    # ── Cancel All ────────────────────────────────────────────────────────────

    async def on_cancel_all(self, data: dict):
        """Triggered by two-hand open palm gesture."""
        if self.state == State.PROCESSING:
            self.state = State.VOICE_MODE
            await self._publish_state("Operations cancelled.")
            await event_bus.publish("JARVIS_RESPONSE", {
                "text": "Operations cancelled by user gesture.",
                "type": "warning"
            })
        elif self.state == State.WAITING_WAKE_WORD:
            self.state = State.STANDBY
            await self._publish_state("Cancelled. Returning to standby.")

    # ── Gaze / Attention ──────────────────────────────────────────────────────

    async def on_gaze_changed(self, data: dict):
        self.current_gaze = data.get("direction", "unknown")

    async def on_attention_changed(self, data: dict):
        state_str = data.get("attention_state")
        try:
            new_state = BehavioralState[state_str]
            self.behavioral_state = new_state
            logger.debug(f"Behavioral state: {self.behavioral_state.name}")
        except KeyError:
            logger.warning(f"Unknown attention state: {state_str}")

    # ── Debug / Simulation Helpers ────────────────────────────────────────────

    async def simulate_snap(self):
        await self.on_snap_detected({"time": time.time()})

    async def simulate_wake_phrase(self):
        if self.state in (State.WAITING_WAKE_WORD, State.SNAP_DETECTED, State.STANDBY):
            asyncio.create_task(self._enter_voice_mode())

    async def simulate_shutdown(self):
        asyncio.create_task(self._exit_application())
