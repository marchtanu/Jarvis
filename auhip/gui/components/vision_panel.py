import cv2
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap

from auhip.gui.theme import COLORS

class VisionPanel(QFrame):
    """
    Panel to display the camera feed and vision subsystem data (gaze, attention).
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
        title = QLabel("Vision & Attention")
        title.setStyleSheet(f"""
            color: {COLORS['text']}; 
            font-size: 15px; 
            font-weight: 600;
            letter-spacing: -0.1px; 
            border: none;
        """)
        header_layout.addWidget(title)
        
        self._fps_lbl = QLabel("FPS: 0")
        self._fps_lbl.setStyleSheet(f"""
            color: {COLORS['text_muted']}; 
            font-size: 12px; 
            border: none;
        """)
        header_layout.addWidget(self._fps_lbl, 0, Qt.AlignmentFlag.AlignRight)
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

        # Data Display layout
        data_layout = QHBoxLayout()
        
        # Gaze & Blink Info
        self._gaze_lbl = QLabel("Gaze: -")
        self._gaze_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 500; border: none;")
        data_layout.addWidget(self._gaze_lbl)
        
        self._blink_lbl = QLabel("Blink: -")
        self._blink_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; font-weight: 500; border: none;")
        data_layout.addWidget(self._blink_lbl)
        
        # Attention state
        self._attention_lbl = QLabel("State: -")
        self._attention_lbl.setStyleSheet(f"color: {COLORS['success']}; font-size: 13px; font-weight: 600; border: none;")
        data_layout.addWidget(self._attention_lbl, 0, Qt.AlignmentFlag.AlignRight)

        # Hand tracking info
        self._hand_lbl = QLabel("Hand: -")
        self._hand_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 500; border: none;")
        data_layout.addWidget(self._hand_lbl)

        layout.addLayout(data_layout)

        # Calibration button
        self.calib_btn = QPushButton("Calibrate Center Gaze")
        self.calib_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['panel_soft']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }}
            QPushButton:hover {{ background: {COLORS['border_soft']}; }}
        """)
        layout.addWidget(self.calib_btn)

    def update_frame(self, frame: np.ndarray):
        # Frame is already RGB from the HandTracker in VisionWorker
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Keep aspect ratio
        pixmap = QPixmap.fromImage(q_img).scaled(
            self._feed_lbl.width(), 
            self._feed_lbl.height(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self._feed_lbl.setPixmap(pixmap)

    def update_data(self, data: dict):
        self._fps_lbl.setText(f"FPS: {data.get('fps', 0):.1f}")
        
        has_face = data.get("has_face", False)
        if not has_face:
            self._gaze_lbl.setText("No Face Detected")
            self._blink_lbl.setText("")
            self._attention_lbl.setText("State: ABSENT")
        else:
            gaze = data.get("gaze", {})
            blink = data.get("blink", {})
            attention = data.get("attention", {})
            
            # Format strings
            calib_text = " (Calibrating...)" if data.get("is_calibrating") else ""
            self._gaze_lbl.setText(f"Gaze: {gaze.get('direction', '-').upper()}{calib_text}")
            
            if blink.get("blink"):
                self._blink_lbl.setText(f"Blink: {blink.get('type', '-')} ({blink.get('duration_ms', 0)}ms)")
            else:
                self._blink_lbl.setText("Blink: None")
                
            state_str = attention.get("attention_state", "-").replace("USER_", "")
            self._attention_lbl.setText(f"State: {state_str} ({attention.get('confidence', 0.0):.2f})")
            
        gesture_data = data.get("gesture", {"type": "none", "confidence": 0.0})
        motion_data = data.get("motion", {"type": "none", "confidence": 0.0})
        
        if motion_data["type"] != "none":
            self._hand_lbl.setText(f"Hand: {motion_data['type']} ({motion_data['confidence']:.2f})")
        elif gesture_data["type"] != "none":
            self._hand_lbl.setText(f"Hand: {gesture_data['type']} ({gesture_data['confidence']:.2f})")
        else:
            self._hand_lbl.setText("Hand: None")
