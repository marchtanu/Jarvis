from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor
from jarvis.gui.theme import COLORS, RESPONSE_COLORS


class ResponsePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("JARVIS RESPONSE")
        title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 2px; border: none; padding: 0;")
        layout.addWidget(title)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("Jarvis responses will appear here...")
        self._text.setMinimumHeight(100)
        layout.addWidget(self._text)

    def add_response(self, text: str, response_type: str = "response"):
        color = RESPONSE_COLORS.get(response_type, COLORS["text"])
        icon = {
            "info":     "ℹ",
            "success":  "✔",
            "warning":  "⚠",
            "response": "◈",
            "shutdown": "◉",
            "greeting": "✦",
        }.get(response_type, "◈")

        self._text.append(
            f'<span style="color:{color};font-size:14px;">{icon} </span>'
            f'<span style="color:{color};font-size:12px;">{text}</span><br>'
        )
        self._text.moveCursor(QTextCursor.MoveOperation.End)
