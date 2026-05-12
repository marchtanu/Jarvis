from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from auhip.gui.theme import COLORS
from .waveform_widget import WaveformWidget
from .vision_panel import VisionPanel
from .transcript_panel import TranscriptPanel
from .response_panel import ResponsePanel

class CenterPanel(QWidget):
    def __init__(self, vision_worker=None, parent=None):
        super().__init__(parent)
        self._vision_worker = vision_worker
        self.setStyleSheet("background: transparent; border: none;")
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # Audio waveform card
        wave_card = QFrame()
        wave_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        wave_card.setFixedHeight(100)
        wl = QVBoxLayout(wave_card)
        wl.setContentsMargins(16, 10, 16, 10)
        wl.setSpacing(4)

        wave_header = QLabel("Audio input")
        wave_header.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 11px; font-weight: 500;"
            "letter-spacing: 0.3px; text-transform: uppercase; border: none;"
        )
        wl.addWidget(wave_header)

        self.waveform = WaveformWidget()
        wl.addWidget(self.waveform, 1)
        layout.addWidget(wave_card)

        # Vision Panel (Hidden by default)
        self.vision_panel = VisionPanel()
        self.vision_panel.hide()
        layout.addWidget(self.vision_panel)
        
        if self._vision_worker:
            self._vision_worker.frame_ready.connect(self.vision_panel.update_frame)
            self._vision_worker.vision_data_ready.connect(self.vision_panel.update_data)
            self.vision_panel.calib_btn.clicked.connect(self._vision_worker.calibrate)

        # Transcript + Response split
        split = QWidget()
        split.setStyleSheet("background: transparent; border: none;")
        split_layout = QHBoxLayout(split)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(14)

        # Transcript card
        transcript_card = QFrame()
        transcript_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        tl = QVBoxLayout(transcript_card)
        tl.setContentsMargins(16, 16, 16, 16)
        tl.setSpacing(10)
        t_header = QLabel("Live transcript")
        t_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        tl.addWidget(t_header)
        self.transcript = TranscriptPanel()
        tl.addWidget(self.transcript, 1)
        split_layout.addWidget(transcript_card, 1)

        # Response card
        response_card = QFrame()
        response_card.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel_soft']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        rl = QVBoxLayout(response_card)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(10)
        r_header = QLabel("auhip response")
        r_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        rl.addWidget(r_header)
        self.response = ResponsePanel()
        rl.addWidget(self.response, 1)
        split_layout.addWidget(response_card, 1)

        layout.addWidget(split, 1)
