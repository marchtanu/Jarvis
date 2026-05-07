import asyncio
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt
from jarvis.gui.theme import COLORS


class DebugPanel(QWidget):
    def __init__(self, fsm, parent=None):
        super().__init__(parent)
        self._fsm = fsm
        self._mic_enabled = True

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Title
        title = QLabel("⚙  DEVELOPER TEST PANEL")
        title.setStyleSheet(f"color: {COLORS['accent']}; font-size: 10px; font-weight: bold; border: none; padding: 0; letter-spacing: 2px;")
        layout.addWidget(title)

        # Buttons row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        self._add_btn(btn_layout, "⚡ Snap",         self._sim_snap,       COLORS["warning"])
        self._add_btn(btn_layout, "⚡⚡ 2× Snap",    self._sim_double_snap, COLORS["warning"])
        self._add_btn(btn_layout, "👋 Wake Word",    self._sim_wake,       COLORS["success"])
        self._add_btn(btn_layout, '💬 "Daddy Home"', self._sim_cmd_daddy,  COLORS["accent"])
        self._add_btn(btn_layout, "🌙 Shutdown",     self._sim_shutdown,   COLORS["danger"])
        layout.addLayout(btn_layout)

        # Mic toggle
        mic_layout = QHBoxLayout()
        self._mic_check = QCheckBox("Real Microphone ON")
        self._mic_check.setChecked(True)
        self._mic_check.setStyleSheet(f"color: {COLORS['text']}; border: none;")
        self._mic_check.toggled.connect(self._toggle_mic)
        mic_layout.addWidget(self._mic_check)
        mic_layout.addStretch()
        layout.addLayout(mic_layout)

        # Event log
        log_title = QLabel("EVENT LOG")
        log_title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 2px; border: none;")
        layout.addWidget(log_title)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(90)
        self._log.setStyleSheet(f"""
            background: {COLORS['surface']};
            border: 1px solid {COLORS['border']};
            border-radius: 4px;
            color: {COLORS['text_muted']};
            font-family: Consolas;
            font-size: 9px;
        """)
        layout.addWidget(self._log)

    def _add_btn(self, layout, text, callback, color):
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['panel']};
                border: 1px solid {color};
                border-radius: 5px;
                color: {color};
                padding: 5px 10px;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background: {color};
                color: {COLORS['bg']};
            }}
        """)
        btn.clicked.connect(callback)
        layout.addWidget(btn)

    def _log_event(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(f'<span style="color:{COLORS["text_muted"]};">[{ts}]</span> '
                         f'<span style="color:{COLORS["accent"]};">{msg}</span>')

    def _run_async(self, coro):
        asyncio.create_task(coro)

    def _sim_snap(self):
        self._log_event("Simulated: SNAP")
        self._run_async(self._fsm.simulate_snap())

    def _sim_double_snap(self):
        self._log_event("Simulated: DOUBLE SNAP")
        async def _double():
            await self._fsm.simulate_snap()
            await asyncio.sleep(0.4)
            await self._fsm.simulate_snap()
        self._run_async(_double())

    def _sim_wake(self):
        self._log_event("Simulated: WAKE PHRASE")
        self._run_async(self._fsm.simulate_wake_phrase())

    def _sim_cmd_daddy(self):
        self._log_event('Simulated: COMMAND "daddy home"')
        self._run_async(self._fsm._process_command("daddy home"))

    def _sim_shutdown(self):
        self._log_event("Simulated: SHUTDOWN")
        self._run_async(self._fsm.simulate_shutdown())

    def _toggle_mic(self, enabled: bool):
        self._mic_enabled = enabled
        status = "ON" if enabled else "OFF"
        self._log_event(f"Microphone: {status}")

    def log(self, msg: str):
        self._log_event(msg)

    @property
    def mic_enabled(self) -> bool:
        return self._mic_enabled
