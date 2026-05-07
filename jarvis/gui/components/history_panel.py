from datetime import datetime
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem
from PyQt6.QtGui import QColor
from jarvis.gui.theme import COLORS


class HistoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {COLORS['text_body']};
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 10px 0;
                border-bottom: 1px solid {COLORS['border_soft']};
            }}
            QListWidget::item:selected {{
                background: transparent;
                color: {COLORS['accent']};
            }}
        """)
        layout.addWidget(self._list, 1)

    def add_entry(self, command: str, response: str | None):
        ts = datetime.now().strftime("%H:%M")
        label = f"{ts}  {command}"
        if response:
            label += f"\n{response[:55]}{'…' if len(response) > 55 else ''}"
        item = QListWidgetItem(label)
        item.setForeground(QColor(COLORS["text_body"]))
        self._list.insertItem(0, item)
