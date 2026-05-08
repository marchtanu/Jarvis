from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
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
import numpy as np
import cv2

logger = logging.getLogger(__name__)

class VisionWorker(QObject):
    # Signals for GUI updates
    frame_ready = pyqtSignal(np.ndarray)
    vision_data_ready = pyqtSignal(dict)
    
    def __init__(self, fps=30):
        super().__init__()
        self.camera = Camera(fps=fps)
        self.calibration_manager = CalibrationManager()
        self.eye_tracker = EyeTracker()
        self.blink_detector = BlinkDetector()
        self.gaze_estimator = GazeEstimator(self.calibration_manager)
        self.attention_engine = AttentionEngine()
        
        self.hand_tracker = HandTracker()
        self.gesture_engine = GestureEngine()
        self.motion_engine = MotionEngine()
        
        self.enable_eye_tracking = False # Toggled via voice command "eye up"
        self.enable_hand_tracking = True # Hand tracking is ON by default
        
        self.timer = QTimer()
        self.timer.timeout.connect(self._process_frame)
        self.interval_ms = int(1000 / fps)
        
        self.running = False
        
    def start(self):
        if not self.running:
            self.camera.start()
            self.timer.start(self.interval_ms)
            self.running = True
            logger.info("Vision Worker started.")
            # We can't easily await inside sync PyQt slots, but we can schedule tasks
            asyncio.create_task(event_bus.publish("VISION_READY", {}))

    def stop(self):
        if self.running:
            try:
                self.timer.stop()
            except RuntimeError:
                pass # Timer may have already been deleted by Qt
            self.camera.stop()
            try:
                self.eye_tracker.close()
            except Exception:
                pass
            self.running = False
            logger.info("Vision Worker stopped.")

    def calibrate(self):
        self.calibration_manager.start_calibration()

    def _process_frame(self):
        if not self.running:
            return
            
        frame = self.camera.get_frame()
        if frame is None:
            return
            
        # 1. Process hand tracking (returns RGB annotated frame and landmarks)
        rgb_annotated_frame = frame.copy()
        hand_landmarks = []
        
        gesture = "none"
        g_conf = 0.0
        motion = "none"
        m_conf = 0.0
        two_hands_open = False
        
        if self.enable_hand_tracking:
            rgb_annotated_frame, hand_landmarks = self.hand_tracker.process_frame(rgb_annotated_frame)
            
            # Check for two hands
            if len(hand_landmarks) == 2:
                g1, c1 = self.gesture_engine.detect_static_gesture(hand_landmarks[0])
                g2, c2 = self.gesture_engine.detect_static_gesture(hand_landmarks[1])
                if g1 == "open_palm" and g2 == "open_palm":
                    two_hands_open = True
                    gesture = "double_open_palm"
                    g_conf = min(c1, c2)
            
            if hand_landmarks and not two_hands_open:
                lms = hand_landmarks[0] # Take first hand
                gesture, g_conf = self.gesture_engine.detect_static_gesture(lms)
                motion, m_conf = self.motion_engine.process_landmarks(lms)
            
        # 2. Process eye tracking (expects BGR, use original frame)
        eye_results = None
        if self.enable_eye_tracking:
            eye_results = self.eye_tracker.process(frame)
        
        has_face = eye_results is not None
        left_eye = eye_results["left_eye"] if has_face else None
        right_eye = eye_results["right_eye"] if has_face else None
        
        # 3. Draw eye tracking debug on the RGB frame from hand tracker
        debug_frame = rgb_annotated_frame
        
        # Blink Detection
        blink_data = self.blink_detector.process(left_eye, right_eye)
        
        # Gaze Estimation
        gaze_data = self.gaze_estimator.process(left_eye, right_eye)
        if self.calibration_manager._collecting and has_face:
            self.calibration_manager.add_sample(gaze_data["raw_horizontal_ratio"], gaze_data["raw_vertical_ratio"])
            
        # Attention Inference
        attention_data = self.attention_engine.process(has_face, gaze_data, blink_data)
        
        # Prepare GUI Data
        vision_dict = {
            "fps": self.camera.get_fps(),
            "has_face": has_face,
            "blink": blink_data,
            "gaze": gaze_data,
            "attention": attention_data,
            "is_calibrating": self.calibration_manager._collecting,
            "gesture": {"type": gesture, "confidence": g_conf},
            "motion": {"type": motion, "confidence": m_conf}
        }
        
        # Draw basic landmarks for debug preview if face is present
        if has_face and "face_landmarks" in eye_results:
            h, w, _ = debug_frame.shape
            for lm in eye_results["face_landmarks"]:
                cv2.circle(debug_frame, (int(lm["x"] * w), int(lm["y"] * h)), 1, (0, 255, 0), -1)
                
            # Draw iris center
            for eye_key in ["left_eye", "right_eye"]:
                iris = eye_results[eye_key]["iris_center"]
                cv2.circle(debug_frame, (int(iris["x"] * w), int(iris["y"] * h)), 3, (255, 0, 0), -1) # Blue in RGB
        
        self.frame_ready.emit(debug_frame)
        self.vision_data_ready.emit(vision_dict)
        
        # Publish events to Event Bus async
        self._publish_events(has_face, blink_data, gaze_data, attention_data, gesture, g_conf, motion, m_conf)

    def _publish_events(self, has_face, blink_data, gaze_data, attention_data, gesture, g_conf, motion, m_conf):
        # Tracking state changes to prevent spamming the event bus
        if not hasattr(self, '_last_face_state'):
            self._last_face_state = False
            self._last_attention = ""
            self._last_gaze = ""

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
            
        # Hand tracking events
        if not hasattr(self, '_last_gesture'):
            self._last_gesture = "none"
        
        if gesture != "none" and gesture != self._last_gesture:
            if gesture == "double_open_palm" and gaze_data.get("direction") == "center":
                # Only cancel if gaze is center (or if eye tracking is disabled, we assume they might be looking)
                # But the requirement says "when look at center camera".
                # If eye tracking is off, gaze_data["direction"] == "unknown", so it won't cancel.
                # To be user friendly, if eye tracking is off, we still cancel.
                pass # logic handled below
                
            if g_conf >= 0.7:
                if gesture == "double_open_palm" and (gaze_data.get("direction") in ("center", "unknown")):
                    asyncio.create_task(event_bus.publish("CANCEL_ALL", {}))
                else:
                    asyncio.create_task(event_bus.publish("GESTURE_DETECTED", {"gesture": gesture, "confidence": g_conf}))
                self._last_gesture = gesture
        elif gesture == "none":
            self._last_gesture = "none"
            
        if motion != "none":
            if m_conf >= 0.4:
                asyncio.create_task(event_bus.publish("MOTION_DETECTED", {"motion": motion, "confidence": m_conf}))
