import math
from collections import deque
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QLinearGradient
from jarvis.gui.theme import COLORS


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._data = deque(maxlen=200)
        self._idle_phase = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update)
        self._timer.start(40)  # ~25fps

    def add_energy(self, energy: float):
        self._data.append(min(energy * 4.0, 1.0))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        mid = h // 2

        # Background
        painter.fillRect(0, 0, w, h, QColor(COLORS["surface"]))

        # Center line
        painter.setPen(QPen(QColor(COLORS["border"]), 1))
        painter.drawLine(0, mid, w, mid)

        if len(self._data) < 2:
            # Draw idle sine wave
            self._idle_phase += 0.05
            points_x = range(0, w, 2)
            for i, x in enumerate(points_x):
                t = i / max(len(list(points_x)), 1)
                y = mid + int(8 * math.sin(t * 4 * math.pi + self._idle_phase))
                alpha = int(80 + 40 * math.sin(t * math.pi))
                painter.setPen(QPen(QColor(0, 200, 255, alpha), 1))
                painter.drawPoint(x, y)
            return

        # Draw waveform bars
        bar_w = max(1, w // len(self._data))
        accent = QColor(COLORS["accent"])

        for i, energy in enumerate(self._data):
            x = int(i * w / len(self._data))
            bar_h = int(energy * (mid - 4))

            # Gradient intensity
            alpha = int(120 + 135 * energy)
            color = QColor(accent)
            color.setAlpha(alpha)

            painter.fillRect(x, mid - bar_h, bar_w - 1, bar_h * 2, color)
