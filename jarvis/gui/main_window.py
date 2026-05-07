import asyncio
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSplitter, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from jarvis.core.event_bus import event_bus
from jarvis.gui.theme import COLORS, STATE_COLORS, STYLESHEET
from jarvis.gui.components.state_panel import StatePanel
from jarvis.gui.components.waveform_widget import WaveformWidget
from jarvis.gui.components.transcript_panel import TranscriptPanel
from jarvis.gui.components.response_panel import ResponsePanel
from jarvis.gui.components.history_panel import HistoryPanel
from jarvis.gui.components.debug_panel import DebugPanel


def _card(widget: QWidget, stretch: int = 0) -> QFrame:
    """Wrap a widget in a styled card frame."""
    frame = QFrame()
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.addWidget(widget)
    return frame


class JarvisMainWindow(QMainWindow):
    def __init__(self, fsm, mic=None):
        super().__init__()
        self._fsm = fsm
        self._mic = mic
        self._snap_count = 0

        self.setWindowTitle("JARVIS ASSISTANT")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_events()

    # ── UI Construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        # ── Title bar ────────────────────────────────────────────────────────
        title_bar = self._make_title_bar()
        root_layout.addWidget(title_bar)

        # ── Main content ─────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel
        left = self._make_left_panel()
        left.setFixedWidth(220)
        splitter.addWidget(left)

        # Center panel
        center = self._make_center_panel()
        splitter.addWidget(center)

        # Right panel
        right = self._make_right_panel()
        right.setFixedWidth(210)
        splitter.addWidget(right)

        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, 1)

        # ── Debug panel ──────────────────────────────────────────────────────
        self._debug_panel = DebugPanel(self._fsm)
        debug_frame = QFrame()
        debug_layout = QVBoxLayout(debug_frame)
        debug_layout.setContentsMargins(0, 0, 0, 0)
        debug_layout.addWidget(self._debug_panel)
        root_layout.addWidget(debug_frame)

        self.setCentralWidget(root)

    def _make_title_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"background: {COLORS['panel']}; border-radius: 8px;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        # Logo + title
        logo = QLabel("◈")
        logo.setStyleSheet(f"color: {COLORS['accent']}; font-size: 20px; border: none;")
        layout.addWidget(logo)

        title = QLabel("JARVIS ASSISTANT")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: bold; letter-spacing: 3px; border: none;")
        layout.addWidget(title)
        layout.addStretch()

        # Clock
        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-family: Consolas; font-size: 12px; border: none;")
        self._update_clock()
        from PyQt6.QtCore import QTimer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        layout.addWidget(self._clock_label)

        return bar

    def _make_left_panel(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # State indicator
        self._state_panel = StatePanel()
        layout.addWidget(self._state_panel)

        # Mic status
        mic_frame = QFrame()
        mic_layout = QHBoxLayout(mic_frame)
        mic_layout.setContentsMargins(8, 6, 8, 6)
        self._mic_dot = QLabel("●")
        self._mic_dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 14px; border: none;")
        mic_layout.addWidget(self._mic_dot)
        mic_label = QLabel("MICROPHONE")
        mic_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 1px; border: none;")
        mic_layout.addWidget(mic_label)
        layout.addWidget(mic_frame)

        # Snap indicator
        snap_frame = QFrame()
        snap_layout = QVBoxLayout(snap_frame)
        snap_layout.setContentsMargins(8, 6, 8, 6)
        snap_label = QLabel("SNAP DETECTOR")
        snap_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 1px; border: none;")
        snap_layout.addWidget(snap_label)
        self._snap_dots = QLabel("○  ○")
        self._snap_dots.setStyleSheet(f"color: {COLORS['border']}; font-size: 18px; border: none;")
        snap_layout.addWidget(self._snap_dots)
        layout.addWidget(snap_frame)

        layout.addStretch()
        return frame

    def _make_center_panel(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Waveform
        wave_label = QLabel("AUDIO INPUT")
        wave_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 2px; border: none;")
        layout.addWidget(wave_label)
        self._waveform = WaveformWidget()
        self._waveform.setFixedHeight(90)
        layout.addWidget(self._waveform)

        # Transcript
        self._transcript = TranscriptPanel()
        layout.addWidget(self._transcript, 1)

        # Response
        self._response = ResponsePanel()
        layout.addWidget(self._response, 1)

        return frame

    def _make_right_panel(self) -> QFrame:
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 10, 10, 10)
        self._history = HistoryPanel()
        layout.addWidget(self._history)
        return frame

    # ── Event Bus Bridge ─────────────────────────────────────────────────────

    def _connect_events(self):
        event_bus.subscribe("STATE_CHANGED",    self._on_state_changed)
        event_bus.subscribe("SPEECH_RECOGNIZED",self._on_speech_recognized)
        event_bus.subscribe("JARVIS_RESPONSE",  self._on_jarvis_response)
        event_bus.subscribe("COMMAND_EXECUTED", self._on_command_executed)
        event_bus.subscribe("SNAP_DETECTED",    self._on_snap)
        event_bus.subscribe("HOME_ACTIVATED",   self._on_home_activated)
        event_bus.subscribe("APP_EXIT",         self._on_app_exit)

    async def _on_state_changed(self, data: dict):
        self._state_panel.set_state(data["state"], data["label"], data.get("message", ""))
        # Hide the GUI when returning to standby
        if data["state"] == "STANDBY":
            self.hide()

    async def _on_speech_recognized(self, data: dict):
        self._transcript.add_text(data["text"], "USER")

    async def _on_jarvis_response(self, data: dict):
        self._response.add_response(data["text"], data.get("type", "response"))
        self._transcript.add_text(data["text"], "JARVIS")

    async def _on_command_executed(self, data: dict):
        self._history.add_entry(data["command"], data.get("response"))

    async def _on_home_activated(self, data: dict):
        """Bring the GUI to the foreground when 'daddy home' is recognised."""
        self.showNormal()
        self.raise_()
        self.activateWindow()

    async def _on_app_exit(self, data: dict):
        """Close the application and exit the loop."""
        self.close()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    async def _on_snap(self, data: dict):
        self._snap_count = (self._snap_count % 2) + 1
        if self._snap_count == 1:
            self._snap_dots.setStyleSheet(f"color: {COLORS['warning']}; font-size: 18px; border: none;")
            self._snap_dots.setText("●  ○")
        else:
            self._snap_dots.setStyleSheet(f"color: {COLORS['success']}; font-size: 18px; border: none;")
            self._snap_dots.setText("●  ●")
        # Reset after 1s
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, lambda: (
            self._snap_dots.setStyleSheet(f"color: {COLORS['border']}; font-size: 18px; border: none;"),
            self._snap_dots.setText("○  ○"),
        ))

    # ── Misc ─────────────────────────────────────────────────────────────────

    def _update_clock(self):
        self._clock_label.setText(datetime.now().strftime("%H:%M:%S"))

    def feed_audio(self, chunk):
        """Called from audio loop to update waveform."""
        import numpy as np
        energy = float(np.sqrt(np.mean(chunk ** 2)))
        self._waveform.add_energy(energy)
