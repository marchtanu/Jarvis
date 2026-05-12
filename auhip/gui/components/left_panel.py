from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PyQt6.QtCore import QTimer
from auhip.gui.theme import COLORS
from .state_panel import StatePanel

class LeftPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self.setStyleSheet(
            f"QFrame {{ background: {COLORS['panel']}; border: 1px solid {COLORS['border']};"
            "border-radius: 12px; }"
        )
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(0)

        # State panel (custom painted)
        self.state_panel = StatePanel()
        layout.addWidget(self.state_panel)

        # Divider
        layout.addWidget(self._make_divider())

        # Mic status row
        self._mic_dot = QLabel("●")
        self._mic_dot.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px; border: none;")
        
        mic_row = QWidget()
        mic_row.setStyleSheet("background: transparent; border: none;")
        mic_layout = QHBoxLayout(mic_row)
        mic_layout.setContentsMargins(0, 8, 0, 0)
        mic_layout.setSpacing(6)
        mic_layout.addWidget(self._mic_dot)
        
        mic_lbl = QLabel("Microphone")
        mic_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 13px; border: none;")
        mic_layout.addWidget(mic_lbl)
        mic_layout.addStretch()
        layout.addWidget(mic_row)

        # Snap detector
        layout.addSpacing(8)
        snap_label = QLabel("Snap detector")
        snap_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; border: none;")
        layout.addWidget(snap_label)

        snap_dots_row = QWidget()
        snap_dots_row.setStyleSheet("background: transparent; border: none;")
        snap_dots_layout = QHBoxLayout(snap_dots_row)
        snap_dots_layout.setContentsMargins(0, 4, 0, 0)
        snap_dots_layout.setSpacing(6)

        self.snap_dot_1 = QLabel("○")
        self.snap_dot_1.setStyleSheet(f"color: {COLORS['border']}; font-size: 16px; border: none;")
        self.snap_dot_2 = QLabel("○")
        self.snap_dot_2.setStyleSheet(f"color: {COLORS['border']}; font-size: 16px; border: none;")
        
        snap_dots_layout.addWidget(self.snap_dot_1)
        snap_dots_layout.addWidget(self.snap_dot_2)
        snap_dots_layout.addStretch()
        layout.addWidget(snap_dots_row)

        layout.addStretch()

    def _make_divider(self) -> QWidget:
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background: {COLORS['border_soft']}; border: none; border-radius: 0;")
        container = QWidget()
        container.setStyleSheet("background: transparent; border: none;")
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 16, 0, 12)
        l.addWidget(line)
        return container

    def set_mic_active(self, active: bool):
        color = COLORS["success"] if active else COLORS["text_soft"]
        self._mic_dot.setStyleSheet(f"color: {color}; font-size: 10px; border: none;")

    def update_snaps(self, count: int):
        coral = COLORS["accent"]
        soft = COLORS["border"]
        if count == 0:
            self.snap_dot_1.setText("○")
            self.snap_dot_1.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
            self.snap_dot_2.setText("○")
            self.snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        elif count == 1:
            self.snap_dot_1.setText("●")
            self.snap_dot_1.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self.snap_dot_2.setText("○")
            self.snap_dot_2.setStyleSheet(f"color: {soft}; font-size: 16px; border: none;")
        else:
            self.snap_dot_1.setText("●")
            self.snap_dot_1.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
            self.snap_dot_2.setText("●")
            self.snap_dot_2.setStyleSheet(f"color: {coral}; font-size: 16px; border: none;")
        
        if count > 0:
            QTimer.singleShot(1000, lambda: self.update_snaps(0))
