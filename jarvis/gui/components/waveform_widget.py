import math
from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen
from jarvis.gui.theme import COLORS


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(48)
        self._data = deque(maxlen=120)
        self._idle_phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(40)

    def add_energy(self, energy: float):
        self._data.append(min(energy * 5.0, 1.0))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mid = h // 2

        # Transparent bg — blends with card
        painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 0))

        # Center line — warm hairline
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawLine(0, mid, w, mid)

        # Coral accent for bars
        accent = QColor(COLORS["accent"])

        if len(self._data) < 2:
            # Idle gentle sine
            self._idle_phase += 0.04
            for x in range(0, w, 3):
                t = x / max(w, 1)
                y = mid + int(5 * math.sin(t * 3 * math.pi + self._idle_phase))
                color = QColor(COLORS["border"])
                painter.setPen(QPen(color, 1.5))
                painter.drawPoint(x, y)
            return

        # Live bars
        bar_w = max(2, w // len(self._data))
        for i, energy in enumerate(self._data):
            x = int(i * w / len(self._data))
            bar_h = int(energy * (mid - 3))
            alpha = int(80 + 175 * energy)
            color = QColor(accent)
            color.setAlpha(alpha)
            painter.fillRect(x, mid - bar_h, max(bar_w - 1, 1), bar_h * 2, color)
