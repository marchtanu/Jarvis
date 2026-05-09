import math
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
from jarvis.gui.theme import COLORS
from jarvis.core.event_bus import event_bus


# Map event labels to a display-friendly short name + colour
COMMAND_STYLE = {
    "▲ Volume Up":    COLORS["success"],
    "▼ Volume Down":  COLORS["warning"],
    "⏭⏭ Next Track":   COLORS["accent"],
    "⏮⏮ Prev Track":   COLORS["accent"],
    "⏯ Play / Pause": COLORS["accent_yellow"],
}


class LastCommandWidget(QWidget):
    """
    Compact always-visible strip that shows the last activated gesture/command.
    Fades out after a short delay.
    """
    FADE_DURATION_MS = 2500   # how long the label stays fully visible
    FADE_STEPS       = 20     # animation steps

    def __init__(self, parent=None):
        super().__init__(parent)
        self._label_text  = ""
        self._alpha       = 0.0          # 0 = invisible, 1 = fully opaque
        self._fade_step   = 0
        self._color       = COLORS["accent"]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {COLORS['accent']}; font-size: 10px; border: none;")

        self._lbl = QLabel("—")
        self._lbl.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 13px; font-weight: 500; border: none;"
        )

        layout.addWidget(self._dot)
        layout.addWidget(self._lbl)
        layout.addStretch()

        # Fade timer
        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(self.FADE_DURATION_MS // self.FADE_STEPS)
        self._fade_timer.timeout.connect(self._fade_tick)

        event_bus.subscribe("LAST_COMMAND",      self._on_last_command)
        event_bus.subscribe("COMMAND_EXECUTED",  self._on_command_executed)
        event_bus.subscribe("JARVIS_RESPONSE",   self._on_response)

    async def _on_last_command(self, data: dict):
        label = data.get("label", "")
        color = COMMAND_STYLE.get(label, COLORS["accent"])
        self._show(label, color)

    async def _on_command_executed(self, data: dict):
        cmd = data.get("command", "")
        if cmd:
            self._show(f'🎙 "{cmd}"', COLORS["text"])

    async def _on_response(self, data: dict):
        # Only update for non-trivial info responses (gesture feedback)
        if data.get("type") == "info":
            text = data.get("text", "")
            if text and len(text) < 40:
                self._show(f"↳ {text}", COLORS["text_muted"])

    def _show(self, text: str, color: str):
        self._label_text = text
        self._color      = color
        self._alpha      = 1.0
        self._dot.setStyleSheet(f"color: {color}; font-size: 10px; border: none;")
        self._lbl.setText(text)
        self._lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 500; border: none;"
        )
        self._fade_timer.stop()
        self._fade_timer.start()

    def _fade_tick(self):
        self._alpha = max(0.0, self._alpha - 1.0 / self.FADE_STEPS)
        opacity = max(30, int(255 * self._alpha))
        hex_opacity = f"{opacity:02x}"
        base = self._color.lstrip("#")
        faded = f"#{base}{hex_opacity}" if len(base) == 6 else self._color
        self._lbl.setStyleSheet(
            f"color: {faded}; font-size: 13px; font-weight: 500; border: none;"
        )
        self._dot.setStyleSheet(f"color: {faded}; font-size: 10px; border: none;")
        if self._alpha <= 0.0:
            self._fade_timer.stop()
            self._lbl.setText("—")
            self._dot.setStyleSheet(
                f"color: {COLORS['border']}; font-size: 10px; border: none;"
            )
            self._lbl.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 13px; border: none;"
            )
