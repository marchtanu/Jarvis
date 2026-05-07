import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
from jarvis.gui.theme import COLORS, STATE_COLORS


class StatePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 140)
        self.setMaximumHeight(180)
        self._state_name = "STANDBY"
        self._state_label = "Standby"
        self._message = "Jarvis initialized."
        self._pulse = 0.0
        self._pulse_speed = 0.025

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)  # ~30fps

    def set_state(self, state_name: str, label: str, message: str):
        self._state_name = state_name
        self._state_label = label
        self._message = message
        # Active states breathe faster
        if state_name in ("COMMAND_MODE", "PROCESSING"):
            self._pulse_speed = 0.07
        elif state_name == "SNAP_DETECTED":
            self._pulse_speed = 0.12
        else:
            self._pulse_speed = 0.025
        self.update()

    def _tick(self):
        self._pulse = (self._pulse + self._pulse_speed) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx = w // 2

        hex_color = STATE_COLORS.get(self._state_name, COLORS["accent"])
        base = QColor(hex_color)

        # Breathing glow ring (subtle, only on active states)
        if self._state_name in ("COMMAND_MODE", "PROCESSING", "SNAP_DETECTED", "WAITING_WAKE_WORD"):
            glow_alpha = int(18 + 14 * math.sin(self._pulse))
            glow_r = 22
            glow_color = QColor(base)
            glow_color.setAlpha(glow_alpha)
            from PyQt6.QtGui import QRadialGradient
            grad = QRadialGradient(cx, 28, glow_r + 8)
            grad.setColorAt(0, glow_color)
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.setBrush(grad)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(cx - glow_r - 8, 28 - glow_r - 8,
                                (glow_r + 8) * 2, (glow_r + 8) * 2)

        # Dot indicator
        dot_r = 9
        pulse_bump = int(2 * math.sin(self._pulse)) if self._state_name not in ("STANDBY", "SLEEP") else 0
        painter.setBrush(base)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - dot_r - pulse_bump, 28 - dot_r - pulse_bump,
                            (dot_r + pulse_bump) * 2, (dot_r + pulse_bump) * 2)

        # State name
        painter.setPen(QColor(COLORS["text"]))
        font = QFont("Inter", 16, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -0.3)
        painter.setFont(font)
        painter.drawText(0, 56, w, 24, Qt.AlignmentFlag.AlignHCenter, self._state_label)

        # Message
        painter.setPen(QColor(COLORS["text_muted"]))
        font2 = QFont("Inter", 12)
        painter.setFont(font2)
        painter.drawText(10, 84, w - 20, 48,
                         Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                         self._message)
