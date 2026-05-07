from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtGui import QTextCursor
from jarvis.gui.theme import COLORS


class TranscriptPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("Recognized speech appears here…")
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

    def add_text(self, text: str, speaker: str = "USER"):
        if speaker == "USER":
            tag_color = COLORS["accent"]
            text_color = COLORS["text"]
        else:
            tag_color = COLORS["text_soft"]
            text_color = COLORS["text_muted"]

        self._text.append(
            f'<span style="color:{tag_color}; font-size:11px; font-weight:500; '
            f'letter-spacing:0.5px;">{speaker}</span>'
            f'<br>'
            f'<span style="color:{text_color}; font-size:14px;">{text}</span>'
            f'<br>'
        )
        self._text.moveCursor(QTextCursor.MoveOperation.End)
