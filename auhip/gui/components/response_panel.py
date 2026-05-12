from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QTextCursor
from auhip.gui.theme import COLORS, RESPONSE_COLORS


class ResponsePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("auhip responses appear here…")
        self._text.setStyleSheet(f"""
            QTextEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text_body']};
                font-size: 14px;
                line-height: 1.55;
                padding: 0;
            }}
        """)
        layout.addWidget(self._text)

    def add_response(self, text: str, response_type: str = "response"):
        color = RESPONSE_COLORS.get(response_type, COLORS["text_body"])
        self._text.append(
            f'<span style="color:{color}; font-size:14px; line-height:1.55;">{text}</span>'
            f'<br>'
        )
        self._text.moveCursor(QTextCursor.MoveOperation.End)
