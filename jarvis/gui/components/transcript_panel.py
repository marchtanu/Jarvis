from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCursor
from jarvis.gui.theme import COLORS


class TranscriptPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("LIVE TRANSCRIPT")
        title.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px; letter-spacing: 2px; border: none; padding: 0;")
        layout.addWidget(title)

        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setPlaceholderText("Recognized speech will appear here...")
        self._text.setMinimumHeight(80)
        layout.addWidget(self._text)

    def add_text(self, text: str, speaker: str = "USER"):
        color = COLORS["accent"] if speaker == "USER" else COLORS["success"]
        self._text.append(
            f'<span style="color:{COLORS["text_muted"]};font-size:9px;">{speaker}</span>'
            f'<br><span style="color:{color};font-size:12px;">&ldquo;{text}&rdquo;</span><br>'
        )
        self._text.moveCursor(QTextCursor.MoveOperation.End)
