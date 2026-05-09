from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from jarvis.core.event_bus import event_bus
from .camera import Camera
from .eye_tracker import EyeTracker
from .blink_detector import BlinkDetector
from .gaze_estimator import GazeEstimator
from .attention_engine import AttentionEngine
from .calibration import CalibrationManager
from .tracker import HandTracker
from .gesture_engine import GestureEngine
from .motion_engine import MotionEngine
import asyncio
import logging
import time
import numpy as np
import cv2

logger = logging.getLogger(__name__)


class VisionWorker(QObject):
    """
    Processes camera frames on a QTimer, routes gesture/motion events
    based on the current mode (CAMERA_MODE vs CONTROL_MODE vs other).
    """
    frame_ready = pyqtSignal(np.ndarray)
    vision_data_ready = pyqtSignal(dict)

    # Mode constants (mirrors State enum names)
    MODE_NONE    = "none"
    MODE_CAMERA  = "camera"
    MODE_CONTROL = "control"
    MODE_SLEEP   = "sleep"

    def __init__(self, fps=30):
        super().__init__()
        self.camera              = Camera(fps=fps)
        self.calibration_manager = CalibrationManager()
        self.eye_tracker         = EyeTracker()
        self.blink_detector      = BlinkDetector()
        self.gaze_estimator      = GazeEstimator(self.calibration_manager)
        self.attention_engine    = AttentionEngine()

        self.hand_tracker   = HandTracker()
        self.gesture_engine = GestureEngine()
        self.motion_engine  = MotionEngine()

        self.enable_eye_tracking  = False
        self.enable_hand_tracking = True

        # Active vision mode — controlled by SET_VISION_MODE event
        self._vision_mode = self.MODE_NONE

        # Control mode state
        self._cursor_pos   = None
        self._is_clicking  = False
        self._hold_start   = None   # Timestamp when pinch was detected
        self._holding      = False

        # Camera mode: track whether index finger is currently raised
        self._index_up_active    = False
        self._last_gesture_state = "none"

        self.timer       = QTimer()
        self.timer.timeout.connect(self._process_frame)
        self.interval_ms = int(1000 / fps)
        self.running     = False

        # Event subscriptions
        event_bus.subscribe("SET_ZOOM",          self._on_set_zoom)
        event_bus.subscribe("SET_CAMERA_INDEX",  self._on_set_camera_index)
        event_bus.subscribe("SET_VISION_MODE",   self._on_set_vision_mode)
        event_bus.subscribe("SET_EYE_STATE",     self._on_set_eye_state)
        event_bus.subscribe("SET_HAND_STATE",    self._on_set_hand_state)

    # ── Event Handlers ────────────────────────────────────────────────────────

    def _on_set_zoom(self, data: dict):
        self.camera.set_zoom(data.get("level", 1.0))

    def _on_set_camera_index(self, data: dict):
        self.camera.restart(data.get("index", 0))

    def _on_set_eye_state(self, data: dict):
        self.enable_eye_tracking = data.get("state", False)
        logger.info(f"Eye tracking: {self.enable_eye_tracking}")

    def _on_set_hand_state(self, data: dict):
        self.enable_hand_tracking = data.get("state", True)
        logger.info(f"Hand tracking: {self.enable_hand_tracking}")

    def _on_set_vision_mode(self, data: dict):
        mode = data.get("mode", self.MODE_NONE)
        prev_mode = self._vision_mode
        self._vision_mode = mode
        
        # Reset per-mode state when switching
        self._cursor_pos      = None
        self._is_clicking     = False
        self._hold_start      = None
        self._holding         = False
        self._index_up_active = False
        
        logger.info(f"Vision mode set to: {self._vision_mode}")

        # Hardware Management: Start/Stop/Throttle Camera based on mode
        if mode == self.MODE_NONE:
            if self.running:
                self.stop()
        elif mode == self.MODE_SLEEP:
            # Low-power mode for emergency gesture detection
            self.interval_ms = 100 # 10 FPS
            if not self.running:
                self.start()
            else:
                self.timer.setInterval(self.interval_ms)
        else:
            # Active modes (Camera/Control)
            self.interval_ms = 33 # ~30 FPS
            if not self.running:
                self.start()
            else:
                self.timer.setInterval(self.interval_ms)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if not self.running:
            self.camera.start()
            self.timer.start(self.interval_ms)
            self.running = True
            logger.info("Vision Worker started.")
            asyncio.create_task(event_bus.publish("VISION_READY", {}))

    def stop(self):
        if self.running:
            try:
                self.timer.stop()
            except RuntimeError:
                pass
            self.camera.stop()
            try:
                self.eye_tracker.close()
            except Exception:
                pass
            self.running = False
            logger.info("Vision Worker stopped.")

    def calibrate(self):
        self.calibration_manager.start_calibration()

    # ── Frame Processing ──────────────────────────────────────────────────────

    def _process_frame(self):
        if not self.running:
            return

        frame = self.camera.get_frame()
        if frame is None:
            return

        rgb_annotated_frame = frame.copy()
        hand_landmarks = []

        gesture    = "none"
        g_conf     = 0.0
        motion     = "none"
        m_conf     = 0.0
        two_hands_open = False

        if self.enable_hand_tracking:
            rgb_annotated_frame, hand_landmarks = self.hand_tracker.process_frame(rgb_annotated_frame)

            # Two-hand open palm check (CANCEL_ALL — works in any mode)
            if len(hand_landmarks) == 2:
                g1, c1 = self.gesture_engine.detect_static_gesture(hand_landmarks[0])
                g2, c2 = self.gesture_engine.detect_static_gesture(hand_landmarks[1])
                if g1 == "open_palm" and g2 == "open_palm":
                    two_hands_open = True
                    gesture        = "double_open_palm"
                    g_conf         = min(c1, c2)

            if hand_landmarks and not two_hands_open:
                lms = hand_landmarks[0]

                if self._vision_mode == self.MODE_CONTROL:
                    # ── CONTROL MODE: cursor gestures + rock_sign for exit ────
                    self._handle_cursor_control(lms)
                    gesture, g_conf = self.gesture_engine.detect_static_gesture(lms)
                    if gesture != "rock_sign":
                        gesture = "cursor_mode"
                        g_conf  = 1.0

                elif self._vision_mode == self.MODE_CAMERA:
                    # ── CAMERA MODE: gesture + motion, plus one_index_up voice
                    gesture, g_conf = self.gesture_engine.detect_static_gesture(lms)
                    motion,  m_conf = self.motion_engine.process_landmarks(lms)
                    self._handle_camera_mode_index(gesture)

                else:
                    # ── DEFAULT / VOICE MODE: still detect gestures for global
                    #    emergency (open_palm → fist) and state machine routing
                    gesture, g_conf = self.gesture_engine.detect_static_gesture(lms)
                    motion,  m_conf = self.motion_engine.process_landmarks(lms)
        
        debug_frame = rgb_annotated_frame

        # ── Eye Tracking & Attention (Optimized: Skip if disabled) ────────────
        eye_results = None
        has_face = False
        blink_data = {"blink": False}
        gaze_data = {"direction": "unknown", "raw_horizontal_ratio": 0.5, "raw_vertical_ratio": 0.5}
        attention_data = {"attention_state": "UNKNOWN"}

        if self.enable_eye_tracking:
            eye_results = self.eye_tracker.process(frame)
            has_face = eye_results is not None
            
            if has_face:
                left_eye  = eye_results["left_eye"]
                right_eye = eye_results["right_eye"]
                blink_data   = self.blink_detector.process(left_eye, right_eye)
                gaze_data    = self.gaze_estimator.process(left_eye, right_eye)

                if self.calibration_manager._collecting:
                    self.calibration_manager.add_sample(
                        gaze_data["raw_horizontal_ratio"],
                        gaze_data["raw_vertical_ratio"]
                    )
            
            attention_data = self.attention_engine.process(has_face, gaze_data, blink_data)

        # ── Debug Drawing ─────────────────────────────────────────────────────
        if has_face and "face_landmarks" in eye_results:
            h, w, _ = debug_frame.shape
            for lm in eye_results["face_landmarks"]:
                cv2.circle(debug_frame, (int(lm["x"] * w), int(lm["y"] * h)), 1, (0, 255, 0), -1)
            for eye_key in ["left_eye", "right_eye"]:
                iris = eye_results[eye_key]["iris_center"]
                cv2.circle(debug_frame, (int(iris["x"] * w), int(iris["y"] * h)), 3, (255, 0, 0), -1)

        vision_dict = {
            "fps":           self.camera.get_fps(),
            "has_face":      has_face,
            "blink":         blink_data,
            "gaze":          gaze_data,
            "attention":     attention_data,
            "is_calibrating": self.calibration_manager._collecting,
            "gesture":       {"type": gesture, "confidence": g_conf},
            "motion":        {"type": motion, "confidence": m_conf},
            "vision_mode":   self._vision_mode,
        }

        self.frame_ready.emit(debug_frame)
        self.vision_data_ready.emit(vision_dict)

        self._publish_events(has_face, blink_data, gaze_data, attention_data, gesture, g_conf, motion, m_conf)

    # ── Camera Mode: one_index_up voice trigger ───────────────────────────────

    def _handle_camera_mode_index(self, gesture: str):
        """Publish TEMP_VOICE_START / TEMP_VOICE_END when index is raised/lowered."""
        currently_up = (gesture == "one_index_up")

        if currently_up and not self._index_up_active:
            self._index_up_active = True
            asyncio.create_task(event_bus.publish("TEMP_VOICE_START", {}))

        elif not currently_up and self._index_up_active:
            self._index_up_active = False
            asyncio.create_task(event_bus.publish("TEMP_VOICE_END", {}))

    # ── Control Mode: cursor + click + hold ──────────────────────────────────

    def _handle_cursor_control(self, landmarks):
        """
        Robust Cursor control:
        - Move: index/middle up OR currently dragging
        - Click: index/middle pinch thumb (tap)
        - Drag: index/middle pinch thumb (hold)
        """
        import pyautogui
        pyautogui.FAILSAFE = False

        thumb_tip  = landmarks[4]
        index_tip  = landmarks[8]
        middle_tip = landmarks[12]
        wrist      = landmarks[0]

        def get_dist(p1, p2):
            return ((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2) ** 0.5

        def is_up(tip_idx, base_idx):
            d_tip = get_dist(landmarks[tip_idx], wrist)
            d_base = get_dist(landmarks[base_idx], wrist)
            return d_tip > d_base * 1.15 # 15% further than base = "up"

        index_up  = is_up(8, 5)
        middle_up = is_up(12, 9)
        ring_up   = is_up(16, 13)
        pinky_up  = is_up(20, 17)

        # ── Pinch Detection ──
        d_index  = get_dist(index_tip,  thumb_tip)
        d_middle = get_dist(middle_tip, thumb_tip)
        pinching = (d_index < 0.06 and d_middle < 0.06)

        # ── Movement Logic ──
        # Movement is allowed if fingers are up, OR we are in a 'holding' state (dragging)
        should_move = (index_up and middle_up and not pinky_up) or self._holding or pinching

        if should_move:
            screen_w, screen_h = pyautogui.size()
            # Expanded margins for easier edge access
            mx, my = 0.15, 0.2
            x = np.interp(index_tip['x'], [mx, 1.0 - mx], [0, screen_w])
            y = np.interp(index_tip['y'], [my, 1.0 - my], [0, screen_h])

            if self._cursor_pos is None:
                self._cursor_pos = (x, y)
            else:
                # Responsive smoothing: higher alpha when dragging for precision
                alpha = 0.45 if self._holding else 0.35
                self._cursor_pos = (
                    self._cursor_pos[0] * (1 - alpha) + x * alpha,
                    self._cursor_pos[1] * (1 - alpha) + y * alpha,
                )
            pyautogui.moveTo(int(self._cursor_pos[0]), int(self._cursor_pos[1]), _pause=False)

        # ── Interaction Logic (Click/Drag) ──
        current_time = time.time()
        if pinching:
            if self._hold_start is None:
                self._hold_start = current_time
            
            duration = current_time - self._hold_start
            if duration >= 0.5 and not self._holding:
                self._holding = True
                pyautogui.mouseDown()
                asyncio.create_task(event_bus.publish("CURSOR_HOLD_START", {}))
                logger.info("Drag started.")
        else:
            if self._hold_start is not None:
                duration = current_time - self._hold_start
                if self._holding:
                    pyautogui.mouseUp()
                    asyncio.create_task(event_bus.publish("CURSOR_HOLD_END", {}))
                    logger.info("Drag released.")
                elif duration < 0.5:
                    pyautogui.click()
                    asyncio.create_task(event_bus.publish("LAST_COMMAND", {"label": "🖱 Click"}))
                    logger.info("Click.")
                
                self._hold_start = None
                self._holding = False
            self._is_clicking = False

    # ── Event Publishing ──────────────────────────────────────────────────────

    def _publish_events(self, has_face, blink_data, gaze_data, attention_data, gesture, g_conf, motion, m_conf):
        if not hasattr(self, '_last_face_state'):
            self._last_face_state  = False
            self._last_attention   = ""
            self._last_gaze        = ""
            self._last_gesture_pub = "none"

        if has_face and not self._last_face_state:
            asyncio.create_task(event_bus.publish("FACE_DETECTED", {}))
        elif not has_face and self._last_face_state:
            asyncio.create_task(event_bus.publish("FACE_LOST", {}))
        self._last_face_state = has_face

        if blink_data["blink"]:
            asyncio.create_task(event_bus.publish("BLINK_DETECTED", blink_data))

        if gaze_data["direction"] != self._last_gaze:
            asyncio.create_task(event_bus.publish("GAZE_CHANGED", gaze_data))
            self._last_gaze = gaze_data["direction"]

        if attention_data["attention_state"] != self._last_attention:
            asyncio.create_task(event_bus.publish("ATTENTION_CHANGED", attention_data))
            if attention_data["attention_state"] == "USER_PRESENT":
                asyncio.create_task(event_bus.publish("USER_PRESENT", attention_data))
            elif attention_data["attention_state"] == "USER_ABSENT":
                asyncio.create_task(event_bus.publish("USER_ABSENT", attention_data))
            self._last_attention = attention_data["attention_state"]

        # Gesture events — skip cursor_mode placeholder
        if gesture not in ("none", "cursor_mode"):
            if gesture != self._last_gesture_pub:
                if g_conf >= 0.7:
                    if gesture == "double_open_palm":
                        asyncio.create_task(event_bus.publish("CANCEL_ALL", {}))
                    else:
                        asyncio.create_task(event_bus.publish("GESTURE_DETECTED", {
                            "gesture": gesture, "confidence": g_conf
                        }))
                    self._last_gesture_pub = gesture
        elif gesture == "none":
            self._last_gesture_pub = "none"

        # Motion events — only publish in CAMERA_MODE to keep bus clean
        if motion != "none" and self._vision_mode == self.MODE_CAMERA:
            if m_conf >= 0.4:
                asyncio.create_task(event_bus.publish("MOTION_DETECTED", {
                    "motion": motion, "confidence": m_conf
                }))
