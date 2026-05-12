from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from auhip.gui.theme import COLORS
from .history_panel import HistoryPanel
from .active_commands_panel import ActiveCommandsPanel

class RightPanel(QFrame):
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
        layout.setSpacing(10)

        header = QLabel("Command history")
        header.setStyleSheet(
            f"color: {COLORS['text']}; font-size: 15px; font-weight: 600;"
            "letter-spacing: -0.1px; border: none;"
        )
        layout.addWidget(header)
        layout.addWidget(self._make_divider())

        self.history_panel = HistoryPanel()
        layout.addWidget(self.history_panel, 1)

        layout.addWidget(self._make_divider())
        
        self.active_commands = ActiveCommandsPanel()
        layout.addWidget(self.active_commands)

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
