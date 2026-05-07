import math
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QFont, QRadialGradient
from jarvis.gui.theme import COLORS, STATE_COLORS


class StatePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 240)
        self._state_name = "STANDBY"
        self._state_label = "Standby"
        self._message = "Jarvis initialized."
        self._pulse = 0.0
        self._pulse_speed = 0.03

        # Pulse timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def set_state(self, state_name: str, label: str, message: str):
        self._state_name = state_name
        self._state_label = label
        self._message = message
        # Faster pulse when active
        self._pulse_speed = 0.08 if state_name == "COMMAND_MODE" else 0.03
        self.update()

    def _tick(self):
        self._pulse = (self._pulse + self._pulse_speed) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2 - 20

        # State color
        hex_color = STATE_COLORS.get(self._state_name, "#0066CC")
        base = QColor(hex_color)

        # Pulse alpha
        pulse_alpha = int(40 + 30 * math.sin(self._pulse))
        glow_size = int(70 + 10 * math.sin(self._pulse))

        # Outer glow
        glow_color = QColor(base)
        glow_color.setAlpha(pulse_alpha)
        grad = QRadialGradient(cx, cy, glow_size)
        grad.setColorAt(0, glow_color)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - glow_size, cy - glow_size, glow_size * 2, glow_size * 2)

        # Main circle
        r = 48
        painter.setBrush(QColor(COLORS["panel"]))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Circle border (color)
        border_color = QColor(base)
        border_color.setAlpha(200)
        from PyQt6.QtGui import QPen
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Inner dot
        inner_r = int(20 + 4 * math.sin(self._pulse))
        inner_color = QColor(base)
        inner_color.setAlpha(180)
        painter.setBrush(inner_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2)

        # State label text
        painter.setPen(QColor(COLORS["text"]))
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(0, cy + r + 16, w, 22, Qt.AlignmentFlag.AlignHCenter, self._state_label)

        # Message text (muted, smaller)
        painter.setPen(QColor(COLORS["text_muted"]))
        font2 = QFont("Segoe UI", 9)
        painter.setFont(font2)
        painter.drawText(8, cy + r + 40, w - 16, 40,
                         Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextWordWrap,
                         self._message)
