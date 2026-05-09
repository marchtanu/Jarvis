from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGraphicsDropShadowEffect
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from jarvis.gui.theme import COLORS
from jarvis.core.event_bus import event_bus
import asyncio

class CommandWidget(QFrame):
    def __init__(self, name, desc, trigger):
        super().__init__()
        self.base_style = f"background: {COLORS['panel_soft']}; border-radius: 8px; border: 1px solid {COLORS['border']};"
        self.setStyleSheet(self.base_style)
        
        # Premium Glow Effect (QGraphicsDropShadowEffect)
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setOffset(0, 0)
        self._shadow.setColor(QColor(COLORS['accent']))
        self.setGraphicsEffect(self._shadow)
        
        cl = QVBoxLayout(self)
        cl.setContentsMargins(10, 8, 10, 8)
        cl.setSpacing(2)
        
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600; border: none;")
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color: {COLORS['text_body']}; font-size: 12px; border: none;")
        
        trigger_lbl = QLabel(f"Trigger: {trigger}")
        trigger_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic; border: none;")
        
        cl.addWidget(name_lbl)
        cl.addWidget(desc_lbl)
        cl.addWidget(trigger_lbl)

        # Pulse highlight animation state (for one-off triggers)
        self._highlight_step = 0
        self._highlight_timer = QTimer(self)
        self._highlight_timer.setInterval(30)
        self._highlight_timer.timeout.connect(self._animate_highlight)

        # Continuous glow animation state (for held gestures)
        self._glowing = False
        self._glow_step = 2.0
        self._glow_increasing = True
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(40)
        self._glow_timer.timeout.connect(self._animate_glow)

    def trigger_highlight(self):
        if not self._glowing:
            self._highlight_step = 6 # Max border width
            self._highlight_timer.start()

    def set_glowing(self, active: bool):
        if active == self._glowing:
            return
        self._glowing = active
        if active:
            self._highlight_timer.stop()
            self._glow_step = 2.0
            self._glow_increasing = True
            self._glow_timer.start()
        else:
            self._glow_timer.stop()
            self._shadow.setBlurRadius(0)
            self.setStyleSheet(self.base_style)

    def _animate_glow(self):
        if self._glow_increasing:
            self._glow_step += 0.3
            if self._glow_step >= 5.0:
                self._glow_increasing = False
        else:
            self._glow_step -= 0.3
            if self._glow_step <= 2.0:
                self._glow_increasing = True
                
        # Use the Coral accent color with varying blur and opacity for a soft glow
        alpha = int(40 + 100 * (self._glow_step / 5.0))
        glow_color = QColor(COLORS['accent'])
        glow_color.setAlpha(alpha)
        
        self._shadow.setBlurRadius(self._glow_step * 4)
        self._shadow.setColor(glow_color)
        
        # Also highlight the border slightly
        self.setStyleSheet(self.base_style + f" border: 1px solid {COLORS['accent']};")

    def _animate_highlight(self):
        if self._highlight_step <= 0:
            self._highlight_timer.stop()
            self._shadow.setBlurRadius(0)
            self.setStyleSheet(self.base_style)
            return
            
        # Draw border
        if not self._glowing:
            alpha = int(200 * (self._highlight_step / 6.0))
            glow_color = QColor(COLORS['accent'])
            glow_color.setAlpha(alpha)
            self._shadow.setBlurRadius(self._highlight_step * 3)
            self._shadow.setColor(glow_color)
            self.setStyleSheet(self.base_style + f" border: 1px solid {COLORS['accent']};")
        
        self._highlight_step -= 1

class ActiveCommandsPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background: transparent; border: none; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.header = QLabel("Active Commands")
        self.header.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: 600; letter-spacing: -0.1px; border: none;")
        layout.addWidget(self.header)

        self.commands_layout = QVBoxLayout()
        self.commands_layout.setSpacing(8)
        layout.addLayout(self.commands_layout)
        
        self._cmd_widgets = {}
        
        self._populate_commands("STANDBY")
        
        event_bus.subscribe("MODE_CHANGED", self._on_mode_changed)
        event_bus.subscribe("LAST_COMMAND", self._on_last_command)
        
        # Continuous command subscriptions
        event_bus.subscribe("TEMP_VOICE_START", lambda _: self._set_glow("Temp Voice", True))
        event_bus.subscribe("TEMP_VOICE_END",   lambda _: self._set_glow("Temp Voice", False))
        event_bus.subscribe("CURSOR_HOLD_START",lambda _: self._set_glow("Hold / Drag", True))
        event_bus.subscribe("CURSOR_HOLD_END",  lambda _: self._set_glow("Hold / Drag", False))

    async def _on_mode_changed(self, data: dict):
        mode = data.get("mode", "STANDBY")
        self._populate_commands(mode)

    def _set_glow(self, key: str, active: bool):
        if key in self._cmd_widgets:
            self._cmd_widgets[key].set_glowing(active)

    async def _on_last_command(self, data: dict):
        label = data.get("label", "")
        
        key = None
        if "Volume" in label:
            key = "Volume Up/Down"
        elif "Track" in label:
            key = "Next / Prev Track"
        elif "Play" in label or "Pause" in label:
            key = "Play / Pause"
        elif "Click" in label:
            key = "Click"
            
        if key and key in self._cmd_widgets:
            # We must trigger it on the main thread via QTimer, but QTimer.singleShot is easiest
            # or just call it if we are already in the UI thread context. qasync usually runs slots in UI thread.
            self._cmd_widgets[key].trigger_highlight()

    def _populate_commands(self, mode: str):
        # Clear existing commands
        while self.commands_layout.count():
            item = self.commands_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        mode_commands = {
            "STANDBY": [
                ("Activate", "Start voice mode", "2 Snaps + 'daddy home'"),
                ("Exit", "Close application", "2 Snaps + 'exit'"),
                ("Emergency Exit", "Close application", "Open Palm -> Fist"),
            ],
            "SLEEP": [
                ("Activate", "Start voice mode", "2 Snaps + 'daddy home'"),
                ("Exit", "Close application", "2 Snaps + 'exit'"),
                ("Emergency Exit", "Close application", "Open Palm -> Fist"),
            ],
            "VOICE_MODE": [
                ("Camera Mode", "Enable gesture control", "'open camera'"),
                ("Control Mode", "Enable cursor control", "'control on'"),
                ("Sleep Mode", "Enter standby", "'goodbye jojo' / 'goodnight'"),
                ("Help", "List all voice commands", "'help'"),
            ],
            "CAMERA_MODE": [
                ("Temp Voice", "Listen while held", "Index finger up"),
                ("Play / Pause", "Toggle media", "Open Palm -> Fist"),
                ("Volume Up/Down", "Adjust volume", "3 fingers up/down (Shake to speed up)"),
                ("Next / Prev Track", "Skip media", "3 fingers Point Left/Right"),
            ],
            "CONTROL_MODE": [
                ("Move Cursor", "Follow hand position", "3 fingers up"),
                ("Click", "Mouse click", "Tap Index & Middle to Thumb"),
                ("Hold / Drag", "Mouse drag", "Hold Index & Middle to Thumb"),
                ("Exit", "Return to Voice Mode", "Rock Sign"),
            ],
        }

        # Handle transient or processing states by showing the closest parent mode
        # or just leaving the previous commands if processing.
        if mode in ("PROCESSING", "WAITING_WAKE_WORD", "SNAP_DETECTED"):
            # Don't update, keep previous commands
            return

        commands = mode_commands.get(mode, [])
        
        mode_label = mode.replace('_', ' ').title()
        self.header.setText(f"Active Commands ({mode_label})")

        self._cmd_widgets.clear()

        for name, desc, trigger in commands:
            cmd_widget = CommandWidget(name, desc, trigger)
            self._cmd_widgets[name] = cmd_widget
            self.commands_layout.addWidget(cmd_widget)

