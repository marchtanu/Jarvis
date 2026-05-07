from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem
from PyQt6.QtCore import Qt
from jarvis.gui.theme import COLORS


class HistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("COMMAND HISTORY")
        title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 2px; border: none; padding: 0;")
        layout.addWidget(title)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text']};
                font-size: 10px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QListWidget::item:selected {{
                background: {COLORS['accent_dim']};
                color: {COLORS['accent']};
            }}
        """)
        layout.addWidget(self._list)

    def add_entry(self, command: str, response: str | None):
        ts = datetime.now().strftime("%H:%M:%S")
        label = f"[{ts}]\n▶ {command}"
        if response:
            label += f"\n◈ {response[:60]}{'...' if len(response) > 60 else ''}"
        item = QListWidgetItem(label)
        item.setForeground(Qt.GlobalColor.white)
        self._list.insertItem(0, item)  # Newest at top
