import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

from jarvis.gui.theme import COLORS
from jarvis.vision.camera import Camera
from jarvis.vision.tracker import HandTracker
from jarvis.vision.gesture_engine import GestureEngine
from jarvis.vision.motion_engine import MotionEngine

class VisionPanel(QFrame):
    """
    Panel to display the camera feed and gesture recognition status.
    Designed to fit within the synthesized Apple/Claude/Notion aesthetic.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{ 
                background: {COLORS['panel']}; 
                border: 1px solid {COLORS['border']};
                border-radius: 12px; 
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Vision")
        title.setStyleSheet(f"""
            color: {COLORS['text']}; 
            font-size: 15px; 
            font-weight: 600;
            letter-spacing: -0.1px; 
            border: none;
        """)
        header_layout.addWidget(title)
        
        self._status_lbl = QLabel("Inactive")
        self._status_lbl.setStyleSheet(f"""
            color: {COLORS['text_muted']}; 
            font-size: 12px; 
            border: none;
        """)
        header_layout.addWidget(self._status_lbl, 0, Qt.AlignmentFlag.AlignRight)
        layout.addLayout(header_layout)

        # Camera Feed
        self._feed_lbl = QLabel()
        self._feed_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._feed_lbl.setMinimumHeight(240)
        self._feed_lbl.setStyleSheet(f"""
            background: {COLORS['dark_card']};
            border-radius: 8px;
            color: {COLORS['text_on_dark_muted']};
        """)
        self._feed_lbl.setText("Camera Feed Offline")
        layout.addWidget(self._feed_lbl, 1)

        # Bottom info (gesture text)
        self._gesture_lbl = QLabel("No gesture")
        self._gesture_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._gesture_lbl.setStyleSheet(f"""
            color: {COLORS['accent']};
            font-size: 13px;
            font-weight: 500;
            border: none;
        """)
        layout.addWidget(self._gesture_lbl)

        # Vision Core
        self.camera = Camera(camera_index=0, fps=30)
        self.tracker = HandTracker()
        self.gesture_engine = GestureEngine()
        self.motion_engine = MotionEngine()
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)

    def start(self):
        self.camera.start()
        self._timer.start(33) # ~30fps
        self._status_lbl.setText("Active")

    def stop(self):
        self._timer.stop()
        self.camera.stop()
        self._status_lbl.setText("Inactive")
        self._feed_lbl.clear()
        self._feed_lbl.setText("Camera Feed Offline")

    def toggle(self):
        if self._timer.isActive():
            self.stop()
            return False
        else:
            self.start()
            return True

    def _update_frame(self):
        frame = self.camera.get_frame()
        if frame is None:
            return

        # Process frame
        rgb_frame, landmarks = self.tracker.process_frame(frame)
        
        # Display image
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Keep aspect ratio
        pixmap = QPixmap.fromImage(q_img).scaled(
            self._feed_lbl.width(), 
            self._feed_lbl.height(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self._feed_lbl.setPixmap(pixmap)

        if landmarks:
            lms = landmarks[0] # Take first hand
            gesture, conf = self.gesture_engine.detect_static_gesture(lms)
            motion, m_conf = self.motion_engine.process_landmarks(lms)
            
            display_text = ""
            if motion != "none":
                display_text = f"Motion: {motion} ({m_conf:.2f})"
            elif gesture != "none":
                display_text = f"Gesture: {gesture} ({conf:.2f})"
            else:
                display_text = "Hand detected"
                
            self._gesture_lbl.setText(display_text)
        else:
            self._gesture_lbl.setText("No gesture")
