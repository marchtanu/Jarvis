from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from jarvis.gui.theme import COLORS

class ActiveCommandsPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"QFrame {{ background: transparent; border: none; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QLabel("Active Vision Commands")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: 600; letter-spacing: -0.1px; border: none;")
        layout.addWidget(header)

        self.commands_layout = QVBoxLayout()
        self.commands_layout.setSpacing(8)
        layout.addLayout(self.commands_layout)
        
        self._populate_commands()

    def _populate_commands(self):
        commands = [
            ("Volume Loop", "Adjust PC volume continuously", "3 fingers up/down"),
            ("Camera Zoom", "Zoom camera feed in/out", "Rock sign / Thumb & Index"),
            ("Cancel All", "Stop current operations", "2 open palms + Center gaze"),
            ("Pause Media", "Play/Pause PC audio", "Open palm -> Fist"),
            ("Exit Jarvis", "Close application", "Open palm -> Fist (Sleep mode)"),
        ]
        
        for name, desc, trigger in commands:
            cmd_widget = QWidget()
            cmd_widget.setStyleSheet(f"background: {COLORS['panel_soft']}; border-radius: 6px;")
            cl = QVBoxLayout(cmd_widget)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(2)
            
            name_lbl = QLabel(name)
            name_lbl.setStyleSheet(f"color: {COLORS['accent']}; font-size: 13px; font-weight: 600;")
            
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color: {COLORS['text_body']}; font-size: 12px;")
            
            trigger_lbl = QLabel(f"Trigger: {trigger}")
            trigger_lbl.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic;")
            
            cl.addWidget(name_lbl)
            cl.addWidget(desc_lbl)
            cl.addWidget(trigger_lbl)
            
            self.commands_layout.addWidget(cmd_widget)
