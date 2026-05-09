from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt6.QtCore import QTimer
from jarvis.gui.theme import COLORS
from .last_command_widget import LastCommandWidget

class NavBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet(f"background: {COLORS['surface']}; border-bottom: 1px solid {COLORS['border']}; border-radius: 0;")
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        # Wordmark
        mark = QLabel("✦")
        mark.setStyleSheet("color: #CC785C; font-size: 16px; border: none;")
        layout.addWidget(mark)

        title = QLabel("Jarvis")
        title.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 13px; font-weight: 600;"
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
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none;"
        )
        layout.addWidget(self._status_badge)

        # Clock
        self._clock_label = QLabel()
        self._clock_label.setStyleSheet(
            f"color: {COLORS['text_muted']}; font-size: 12px; border: none; margin-left: 16px;"
        )
        self._update_clock()
        
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        layout.addWidget(self._clock_label)

    def _update_clock(self):
        self._clock_label.setText(datetime.now().strftime("%H:%M"))

    def set_status(self, label: str, color: str):
        self._status_badge.setText(f"● {label}")
        self._status_badge.setStyleSheet(f"color: {color}; font-size: 12px; border: none;")
