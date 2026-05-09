import asyncio
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from jarvis.core.event_bus import event_bus
from jarvis.gui.theme import COLORS, STATE_COLORS, STYLESHEET
from jarvis.gui.components.state_panel import StatePanel
from jarvis.gui.components.waveform_widget import WaveformWidget
from jarvis.gui.components.transcript_panel import TranscriptPanel
from jarvis.gui.components.response_panel import ResponsePanel
from jarvis.gui.components.history_panel import HistoryPanel
from jarvis.gui.components.debug_panel import DebugPanel
from jarvis.gui.components.vision_panel import VisionPanel
from jarvis.gui.components.active_commands_panel import ActiveCommandsPanel
from jarvis.gui.components.last_command_widget import LastCommandWidget


class JarvisMainWindow(QMainWindow):
    def __init__(self, fsm, mic=None, vision_worker=None):
        super().__init__()
        self._fsm = fsm
        self._mic = mic
        self._vision_worker = vision_worker
        self._snap_count = 0

        self.setWindowTitle("Jarvis")
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_events()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(f"background: {COLORS['bg']}; border: none;")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Global nav bar (Apple-style black bar)
        root_layout.addWidget(self._make_nav_bar())

        # Main 3-column content area
        body = QWidget()
        body.setStyleSheet(f"background: {COLORS['bg']}; border: none;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(16)

        left = self._make_left_panel()
        left.setFixedWidth(220)
        body_layout.addWidget(left)

        center = self._make_center_panel()
        body_layout.addWidget(center, 1)

        right = self._make_right_panel()
        right.setFixedWidth(220)
        body_layout.addWidget(right)

        root_layout.addWidget(body, 1)

        # Developer tools bar at bottom
        self._debug_panel = DebugPanel(self._fsm)
        root_layout.addWidget(self._debug_panel)

        self.setCentralWidget(root)

    # ── Nav Bar ───────────────────────────────────────────────────────────────

    def _make_nav_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background: {COLORS['nav']}; border: none; border-radius: 0;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Wordmark
        mark = QLabel("✦")
        mark.setStyleSheet("color: #CC785C; font-size: 16px; border: none;")
        layout.addWidget(mark)

        title = QLabel("Jarvis")
        title.setStyleSheet(
            f"color: {COLORS['text_on_dark']}; font-size: 13px; font-weight: 500;"
            "letter-spacing: -0.1px; border: none;"
        )
        layout.addWidget(title)
        layout.addStretch()

        # Last activated command indicator
        self._last_cmd_widget = LastCommandWidget()
        layout.addWidget(self._last_cmd_widget)

        # Separator
        sep = QLabel("│")
        sep.setStyleSheet(f"color: {COLORS['border_dark']}; font-size: 14px; border: none; margin: 0 6px;")
        layout.addWidget(sep)

        # Status badge
        self._status_badge = QLabel("● Standby")
        self._status_badge.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 12px; border: none;"
        )
        layout.addWidget(self._status_badge)

        # Clock
        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 12px; border: none; margin-left: 16px;"
        )
        self._update_clock()
        clock_timer = QTimer(self)
        clock_timer.timeout.connect(self._update_clock)
        clock_timer.start(1000)
        layout.addWidget(self._clock_label)

        return bar

    # ── Left Panel ────────────────────────────────────────────────────────────

    def _make_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(0)

        # State panel (custom painted)
        self._state_panel = StatePanel()
        layout.addWidget(self._state_panel)

        # Divider
        layout.addWidget(self._make_divider())

        # Mic status row
        layout.addWidget(self._make_status_row("mic", "Microphone", active=True))

        # Snap detector
        layout.addSpacing(8)
        snap_label = QLabel("Snap detector")
        snap_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none;"
        )
        layout.addWidget(snap_label)

        snap_dots_row = QWidget()
        snap_dots_row.setStyleSheet("background: transparent; border: none;")
        snap_dots_layout = QHBoxLayout(snap_dots_row)
        snap_dots_layout.setContentsMargins(0, 4, 0, 0)
        snap_dots_layout.setSpacing(6)

        self._snap_dot_1 = QLabel("○")
        self._snap_dot_1.setStyleSheet(
            f"color: {COLORS['border']}; font-size: 16px; border: none;"
        )
        self._snap_dot_2 = QLabel("○")
        self._snap_dot_2.setStyleSheet(
            f"color: {COLORS['border']}; font-size: 16px; border: none;"
        )
        snap_dots_layout.addWidget(self._snap_dot_1)
        snap_dots_layout.addWidget(self._snap_dot_2)
        snap_dots_layout.addStretch()
        layout.addWidget(snap_dots_row)

        layout.addStretch()
        return frame

    def _make_status_row(self, kind: str, label: str, active: bool = True) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent; border: none;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 8, 0, 0)
        row_layout.setSpacing(6)

        dot = QLabel("●")
        color = COLORS["success"] if active else COLORS["text_soft"]
        dot.setStyleSheet(f"color: {color}; font-size: 10px; border: none;")
        row_layout.addWidget(dot)

        lbl = QLabel(label)
        lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 13px; border: none;"
        )
        row_layout.addWidget(lbl)
        row_layout.addStretch()

        if kind == "mic":
            self._mic_dot = dot

        return row

    def _make_divider(self) -> QWidget:
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {COLORS['border_soft']}; border: none; border-radius: 0;")
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 16, 0, 12)
        l.addWidget(line)
        return container

    # ── Center Panel ──────────────────────────────────────────────────────────

    def _make_center_panel(self) -> QWidget:
        col = QWidget()
        col.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(col)
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

        self._waveform = WaveformWidget()
        wl.addWidget(self._waveform, 1)
        layout.addWidget(wave_card)

        # Vision Panel (Hidden by default)
        self._vision_panel = VisionPanel()
        self._vision_panel.hide()
        layout.addWidget(self._vision_panel)
        
        if self._vision_worker:
            self._vision_worker.frame_ready.connect(self._vision_panel.update_frame)
            self._vision_worker.vision_data_ready.connect(self._vision_panel.update_data)
            self._vision_panel.calib_btn.clicked.connect(self._vision_worker.calibrate)

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
        self._transcript = TranscriptPanel()
        tl.addWidget(self._transcript, 1)
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
        r_header = QLabel("Jarvis response")
        r_header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        rl.addWidget(r_header)
        self._response = ResponsePanel()
        rl.addWidget(self._response, 1)
        split_layout.addWidget(response_card, 1)

        layout.addWidget(split, 1)
        return col

    # ── Right Panel ───────────────────────────────────────────────────────────

    def _make_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(10)

        header = QLabel("Command history")
        header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        layout.addWidget(header)
        layout.addWidget(self._make_divider())

        self._history = HistoryPanel()
        layout.addWidget(self._history, 1)

        layout.addWidget(self._make_divider())
        
        self._active_commands = ActiveCommandsPanel()
        layout.addWidget(self._active_commands)
        
        return frame

    # ── Event Wiring ──────────────────────────────────────────────────────────

    def _connect_events(self):
        event_bus.subscribe("STATE_CHANGED",    self._on_state_changed)
        event_bus.subscribe("MODE_CHANGED",     self._on_mode_changed)
        event_bus.subscribe("SPEECH_RECOGNIZED",self._on_speech_recognized)
        event_bus.subscribe("JARVIS_RESPONSE",  self._on_jarvis_response)
        event_bus.subscribe("COMMAND_EXECUTED", self._on_command_executed)
        event_bus.subscribe("SNAP_DETECTED",    self._on_snap)
        event_bus.subscribe("HOME_ACTIVATED",   self._on_home_activated)
        event_bus.subscribe("TOGGLE_VISION",    self._on_toggle_vision)
        event_bus.subscribe("SET_VISION_STATE", self._on_set_vision_state)
        event_bus.subscribe("SET_EYE_STATE",    self._on_set_eye_state)
        event_bus.subscribe("SET_HAND_STATE",   self._on_set_hand_state)
        event_bus.subscribe("TOGGLE_FULLSCREEN", self._on_toggle_fullscreen)
        event_bus.subscribe("MINIMIZE_WINDOW",  self._on_minimize_window)
        event_bus.subscribe("APP_EXIT",         self._on_app_exit)

    async def _on_state_changed(self, data: dict):
        state = data["state"]
        label = data["label"]
        self._state_panel.set_state(state, label, data.get("message", ""))
        color = STATE_COLORS.get(state, COLORS["text_muted"])
        self._status_badge.setText(f"● {label}")
        self._status_badge.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
        if state == "STANDBY":
            self.hide()

    async def _on_mode_changed(self, data: dict):
        """Show/hide vision panel automatically when entering/leaving camera or control mode."""
        mode = data.get("mode", "")
        if mode in ("CAMERA_MODE", "CONTROL_MODE"):
            if self._vision_panel.isHidden():
                self._vision_panel.show()
                if self._vision_worker:
                    self._vision_worker.start()
        elif mode in ("VOICE_MODE", "STANDBY", "SLEEP"):
            # Don't auto-hide — user may have manually opened camera; only hide on explicit off
            pass

    async def _on_speech_recognized(self, data: dict):
        self._transcript.add_text(data["text"], "USER")

    async def _on_jarvis_response(self, data: dict):
        self._response.add_response(data["text"], data.get("type", "response"))
        self._transcript.add_text(data["text"], "JARVIS")

    async def _on_command_executed(self, data: dict):
        self._history.add_entry(data["command"], data.get("response"))

    async def _on_home_activated(self, data: dict):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    async def _on_toggle_vision(self, data: dict):
        if self._vision_panel.isHidden():
            self._vision_panel.show()
            if self._vision_worker:
                self._vision_worker.start()
        else:
            self._vision_panel.hide()

    async def _on_set_vision_state(self, data: dict):
        state = data.get("state", True)
        if state and self._vision_panel.isHidden():
            self._vision_panel.show()
            if self._vision_worker:
                self._vision_worker.start()
        elif not state and not self._vision_panel.isHidden():
            self._vision_panel.hide()

    async def _on_toggle_fullscreen(self, data: dict):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    async def _on_minimize_window(self, data: dict):
        self.showMinimized()

    async def _on_set_eye_state(self, data: dict):
        state = data.get("state", True)
        if self._vision_worker:
            self._vision_worker.enable_eye_tracking = state
            status = "enabled" if state else "disabled"
            await event_bus.publish("JARVIS_RESPONSE", {"text": f"Eye tracking {status}.", "type": "info"})
            
    async def _on_set_hand_state(self, data: dict):
        state = data.get("state", True)
        if self._vision_worker:
            self._vision_worker.enable_hand_tracking = state
            status = "enabled" if state else "disabled"
            await event_bus.publish("JARVIS_RESPONSE", {"text": f"Hand tracking {status}.", "type": "info"})

    async def _on_app_exit(self, data: dict):
        self.close()
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().quit()

    async def _on_snap(self, data: dict):
        self._snap_count = (self._snap_count % 2) + 1
        coral = COLORS["accent"]
        soft = COLORS["border"]

        if self._snap_count == 1:
            self._snap_dot_1.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self._snap_dot_1.setText("●")
            self._snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
            self._snap_dot_2.setText("○")
        else:
            self._snap_dot_1.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self._snap_dot_1.setText("●")
            self._snap_dot_2.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self._snap_dot_2.setText("●")

        QTimer.singleShot(1000, self._reset_snap_dots)

    def _reset_snap_dots(self):
        soft = COLORS["border"]
        self._snap_dot_1.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        self._snap_dot_1.setText("○")
        self._snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        self._snap_dot_2.setText("○")

    # ── Misc ──────────────────────────────────────────────────────────────────

    def _update_clock(self):
        self._clock_label.setText(datetime.now().strftime("%H:%M"))

    def feed_audio(self, chunk):
        import numpy as np
        energy = float(np.sqrt(np.mean(chunk ** 2)))
        self._waveform.add_energy(energy)
