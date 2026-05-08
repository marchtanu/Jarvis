import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt
from jarvis.gui.theme import COLORS


class DebugPanel(QWidget):
    def __init__(self, fsm, parent=None):
        super().__init__(parent)
        self._fsm = fsm
        self._mic_instance = None # Set later
        self._mic_enabled = True

        # Dark card styling (Claude code-window-card aesthetic)
        self.setStyleSheet(
            f"QWidget {{ background: {COLORS['dark_card']}; border-top: 1px solid {COLORS['border_dark']};"
            "border-radius: 0; }"
        )
        self.setFixedHeight(180) # Increased height for hardware selectors

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 20, 14)
        layout.setSpacing(20)

        # Left: title + mic toggle
        left = QWidget()
        left.setStyleSheet("background: transparent; border: none;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        title = QLabel("Developer tools")
        title.setStyleSheet(
            f"color: {COLORS['text_on_dark']}; font-size: 13px; font-weight: 600;"
            "letter-spacing: -0.1px;"
        )
        left_layout.addWidget(title)

        self._mic_check = QCheckBox("Microphone enabled")
        self._mic_check.setChecked(True)
        self._mic_check.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 12px; spacing: 6px;"
        )
        self._mic_check.toggled.connect(self._toggle_mic)
        left_layout.addWidget(self._mic_check)
        
        # Hardware Selection
        hw_label = QLabel("Hardware")
        hw_label.setStyleSheet(f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; margin-top: 5px;")
        left_layout.addWidget(hw_label)
        
        self.cam_select = QComboBox()
        self.cam_select.setStyleSheet(self._combo_style())
        left_layout.addWidget(self.cam_select)
        
        self.mic_select = QComboBox()
        self.mic_select.setStyleSheet(self._combo_style())
        left_layout.addWidget(self.mic_select)
        
        self._populate_hardware()
        
        self.cam_select.currentIndexChanged.connect(self._on_cam_changed)
        self.mic_select.currentIndexChanged.connect(self._on_mic_changed)

        left_layout.addStretch()
        left.setFixedWidth(160)
        layout.addWidget(left)

        # Divider
        div = QWidget()
        div.setFixedWidth(1)
        div.setStyleSheet(f"background: {COLORS['border_dark']}; border: none;")
        layout.addWidget(div)

        # Center: action buttons
        btn_area = QWidget()
        btn_area.setStyleSheet("background: transparent; border: none;")
        btn_layout_outer = QVBoxLayout(btn_area)
        btn_layout_outer.setContentsMargins(0, 0, 0, 0)
        btn_layout_outer.setSpacing(6)

        btn_label = QLabel("Simulate")
        btn_label.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; letter-spacing: 0.3px;"
        )
        btn_layout_outer.addWidget(btn_label)

        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent; border: none;")
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(8)

        self._add_btn(btn_row_layout, "Snap",       self._sim_snap,         primary=False)
        self._add_btn(btn_row_layout, "2× Snap",    self._sim_double_snap,  primary=False)
        self._add_btn(btn_row_layout, "Wake word",  self._sim_wake,         primary=False)
        self._add_btn(btn_row_layout, "Daddy home", self._sim_cmd_daddy,    primary=True)
        self._add_btn(btn_row_layout, "Vision",     self._sim_toggle_vision,primary=False)
        self._add_btn(btn_row_layout, "Shutdown",   self._sim_shutdown,     primary=False)
        btn_row_layout.addStretch()
        btn_layout_outer.addWidget(btn_row)
        btn_layout_outer.addStretch()
        layout.addWidget(btn_area, 1)

        # Divider
        div2 = QWidget()
        div2.setFixedWidth(1)
        div2.setStyleSheet(f"background: {COLORS['border_dark']}; border: none;")
        layout.addWidget(div2)

        # Right: event log
        log_area = QWidget()
        log_area.setStyleSheet("background: transparent; border: none;")
        log_layout = QVBoxLayout(log_area)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(4)

        log_title = QLabel("Event log")
        log_title.setStyleSheet(
            f"color: {COLORS['text_on_dark_muted']}; font-size: 11px; letter-spacing: 0.3px;"
        )
        log_layout.addWidget(log_title)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text_on_dark_muted']};
                font-family: 'Consolas', 'JetBrains Mono', monospace;
                font-size: 11px;
                padding: 0;
            }}
        """)
        log_layout.addWidget(self._log, 1)
        log_area.setFixedWidth(300)
        layout.addWidget(log_area)

    def _add_btn(self, layout, text: str, callback, primary: bool = False):
        btn = QPushButton(text)
        if primary:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    border: none;
                    border-radius: 6px;
                    color: #FFFFFF;
                    padding: 6px 14px;
                    font-size: 12px;
                    font-weight: 500;
                }}
                QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
                QPushButton:pressed {{ background-color: #8E4A32; }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['border_dark']};
                    border: 1px solid {COLORS['border_dark']};
                    border-radius: 6px;
                    color: {COLORS['text_on_dark_muted']};
                    padding: 6px 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #2E2B27;
                    color: {COLORS['text_on_dark']};
                }}
                QPushButton:pressed {{ color: {COLORS['accent']}; }}
            """)
        btn.clicked.connect(callback)
        layout.addWidget(btn)

    def _log_event(self, msg: str):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.append(
            f'<span style="color:{COLORS["text_on_dark_muted"]};">[{ts}]</span> '
            f'<span style="color:{COLORS["text_on_dark"]};">{msg}</span>'
        )

    def _run_async(self, coro):
        asyncio.create_task(coro)

    def _sim_snap(self):
        self._log_event("Simulated: SNAP")
        self._run_async(self._fsm.simulate_snap())

    def _sim_double_snap(self):
        self._log_event("Simulated: DOUBLE SNAP")
        async def _double():
            await self._fsm.simulate_snap()
            import asyncio as _a; await _a.sleep(0.4)
            await self._fsm.simulate_snap()
        self._run_async(_double())

    def _sim_wake(self):
        self._log_event("Simulated: WAKE PHRASE")
        self._run_async(self._fsm.simulate_wake_phrase())

    def _sim_cmd_daddy(self):
        self._log_event('Simulated: "daddy home"')
        self._run_async(self._fsm._process_command("daddy home"))

    def _sim_toggle_vision(self):
        self._log_event("Simulated: TOGGLE VISION")
        from jarvis.core.event_bus import event_bus
        self._run_async(event_bus.publish("TOGGLE_VISION", {}))

    def _sim_shutdown(self):
        self._log_event("Simulated: SHUTDOWN")
        self._run_async(self._fsm.simulate_shutdown())

    def _toggle_mic(self, enabled: bool):
        self._mic_enabled = enabled
        self._log_event(f"Microphone: {'ON' if enabled else 'OFF'}")

    def _combo_style(self):
        return f"""
            QComboBox {{
                background-color: {COLORS['border_dark']};
                border: 1px solid {COLORS['border_dark']};
                border-radius: 4px;
                color: {COLORS['text_on_dark']};
                padding: 2px 8px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['dark_card']};
                color: {COLORS['text_on_dark']};
                selection-background-color: {COLORS['accent']};
            }}
        """

    def _populate_hardware(self):
        # Mics
        import sounddevice as sd
        try:
            devices = sd.query_devices()
            for i, d in enumerate(devices):
                if d['max_input_channels'] > 0:
                    self.mic_select.addItem(f"Mic {i}: {d['name'][:20]}...", i)
        except Exception as e:
            self.mic_select.addItem("No Mics Found", -1)

        # Cameras
        import cv2
        for i in range(3): # Probe first 3
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.cam_select.addItem(f"Camera {i}", i)
                cap.release()
        if self.cam_select.count() == 0:
            self.cam_select.addItem("No Cameras Found", -1)

    def _on_cam_changed(self, index):
        cam_idx = self.cam_select.currentData()
        if cam_idx != -1:
            from jarvis.core.event_bus import event_bus
            self._run_async(event_bus.publish("SET_CAMERA_INDEX", {"index": cam_idx}))
            self._log_event(f"Switched to Camera {cam_idx}")

    def _on_mic_changed(self, index):
        mic_idx = self.mic_select.currentData()
        if mic_idx != -1 and self._mic_instance:
            self._log_event(f"Switching Microphone to index {mic_idx}...")
            self._mic_instance.stop()
            self._mic_instance.start(device_index=mic_idx)

    def set_mic_instance(self, mic):
        self._mic_instance = mic

    def log(self, msg: str):
        self._log_event(msg)

    @property
    def mic_enabled(self) -> bool:
        return self._mic_enabled
