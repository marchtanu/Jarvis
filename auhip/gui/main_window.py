import asyncio
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt

from auhip.core.event_bus import event_bus
from auhip.gui.theme import COLORS, STATE_COLORS, STYLESHEET
from auhip.gui.components.nav_bar import NavBar
from auhip.gui.components.left_panel import LeftPanel
from auhip.gui.components.center_panel import CenterPanel
from auhip.gui.components.right_panel import RightPanel
from auhip.gui.components.debug_panel import DebugPanel


class AuhipMainWindow(QMainWindow):
    def __init__(self, fsm, mic=None, vision_worker=None):
        super().__init__()
        self._fsm = fsm
        self._vision_worker = vision_worker

        self.setWindowTitle("auhip")
        self.setMinimumSize(1200, 760)
        self.setStyleSheet(STYLESHEET)

        self._build_ui()
        self._connect_events()

    def _build_ui(self):
        root = QWidget()
        root.setStyleSheet(f"background: {COLORS['bg']}; border: none;")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Nav Bar
        self.nav_bar = NavBar()
        root_layout.addWidget(self.nav_bar)

        # 2. Main Body
        body = QWidget()
        body.setStyleSheet(f"background: {COLORS['bg']}; border: none;")
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(20, 20, 20, 20)
        body_layout.setSpacing(16)

        self.left_panel = LeftPanel()
        body_layout.addWidget(self.left_panel)

        self.center_panel = CenterPanel(self._vision_worker)
        body_layout.addWidget(self.center_panel, 1)

        self.right_panel = RightPanel()
        body_layout.addWidget(self.right_panel)

        root_layout.addWidget(body, 1)

        # 3. Debug Panel
        self.debug_panel = DebugPanel(self._fsm)
        root_layout.addWidget(self.debug_panel)

        self.setCentralWidget(root)

    def _connect_events(self):
        # UI Bridge: Mapping events to component methods
        mappings = {
            "STATE_CHANGED":     self._on_state_changed,
            "MODE_CHANGED":      self._on_mode_changed,
            "SPEECH_RECOGNIZED": self._on_speech_recognized,
            "AUHIP_RESPONSE":    self._on_auhip_response,
            "COMMAND_EXECUTED":  self._on_command_executed,
            "SNAP_DETECTED":     self._on_snap,
            "HOME_ACTIVATED":    self._on_home_activated,
            "TOGGLE_VISION":     self._on_toggle_vision,
            "SET_VISION_STATE":  self._on_set_vision_state,
            "SET_EYE_STATE":     self._on_set_eye_state,
            "SET_HAND_STATE":    self._on_set_hand_state,
            "TOGGLE_FULLSCREEN": self._on_toggle_fullscreen,
            "MINIMIZE_WINDOW":   self._on_minimize_window,
            "APP_EXIT":          self._on_app_exit
        }
        for event, handler in mappings.items():
            event_bus.subscribe(event, handler)

    async def _on_state_changed(self, data: dict):
        state, label = data["state"], data["label"]
        color = STATE_COLORS.get(state, COLORS["text_muted"])
        
        self.left_panel.state_panel.set_state(state, label, data.get("message", ""))
        self.nav_bar.set_status(label, color)
        
        if state == "STANDBY":
            self.hide()

    async def _on_mode_changed(self, data: dict):
        mode = data.get("mode", "")
        # Auto-show vision in camera/control modes
        if mode in ("CAMERA_MODE", "CONTROL_MODE") and self.center_panel.vision_panel.isHidden():
            self.center_panel.vision_panel.show()
            if self._vision_worker:
                self._vision_worker.start()

    async def _on_speech_recognized(self, data: dict):
        self.center_panel.transcript.add_text(data["text"], "USER")

    async def _on_auhip_response(self, data: dict):
        self.center_panel.response.add_response(data["text"], data.get("type", "response"))
        self.center_panel.transcript.add_text(data["text"], "auhip")

    async def _on_command_executed(self, data: dict):
        self.right_panel.history_panel.add_entry(data["command"], data.get("response"))

    async def _on_home_activated(self, data: dict):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    async def _on_toggle_vision(self, data: dict):
        panel = self.center_panel.vision_panel
        if panel.isHidden():
            panel.show()
            if self._vision_worker:
                self._vision_worker.start()
        else:
            panel.hide()

    async def _on_set_vision_state(self, data: dict):
        state = data.get("state", True)
        panel = self.center_panel.vision_panel
        if state and panel.isHidden():
            panel.show()
            if self._vision_worker:
                self._vision_worker.start()
        elif not state and not panel.isHidden():
            panel.hide()

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
            await event_bus.publish("AUHIP_RESPONSE", {"text": f"Eye tracking {status}.", "type": "info"})

    async def _on_set_hand_state(self, data: dict):
        state = data.get("state", True)
        if self._vision_worker:
            self._vision_worker.enable_hand_tracking = state
            status = "enabled" if state else "disabled"
            await event_bus.publish("AUHIP_RESPONSE", {"text": f"Hand tracking {status}.", "type": "info"})

    async def _on_app_exit(self, data: dict):
        self.close()
        QApplication.instance().quit()

    async def _on_snap(self, data: dict):
        # Just increment a counter here, the LeftPanel handles its own dots logic via internal state if we wanted,
        # but for now we'll just proxy the count or let it handle the event if it subscribed.
        # Actually, let's just use the component's method.
        if not hasattr(self, '_snap_count'): self._snap_count = 0
        self._snap_count = (self._snap_count % 2) + 1
        self.left_panel.update_snaps(self._snap_count)

    def feed_audio(self, chunk):
        energy = float(np.sqrt(np.mean(chunk ** 2)))
        self.center_panel.waveform.add_energy(energy)
