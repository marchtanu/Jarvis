# Jarvis GUI Theme — Dark Navy + Electric Cyan

COLORS = {
    "bg":          "#070B14",
    "surface":     "#0D1526",
    "panel":       "#111E35",
    "border":      "#1A3055",
    "accent":      "#00C8FF",
    "accent_dim":  "#005577",
    "text":        "#E8EBF4",
    "text_muted":  "#5577AA",
    "success":     "#00FF88",
    "warning":     "#FFB800",
    "danger":      "#FF4444",
    "processing":  "#CC44FF",
    "shutdown":    "#FF4444",
}

STATE_COLORS = {
    "STANDBY":          "#0066CC",
    "SNAP_DETECTED":    "#FFB800",
    "WAITING_WAKE_WORD": "#FF8C00",
    "COMMAND_MODE":     "#00FF88",
    "PROCESSING":       "#CC44FF",
    "SHUTDOWN":         "#FF4444",
}

RESPONSE_COLORS = {
    "info":     "#00C8FF",
    "success":  "#00FF88",
    "warning":  "#FFB800",
    "response": "#E8EBF4",
    "shutdown": "#FF4444",
    "greeting": "#00FF88",
}

FONTS = {
    "title":  ("Segoe UI", 22, "bold"),
    "state":  ("Segoe UI", 13, "bold"),
    "body":   ("Segoe UI", 11),
    "small":  ("Segoe UI", 9),
    "mono":   ("Consolas", 9),
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Segoe UI';
    font-size: 11px;
}}
QFrame {{
    background-color: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
}}
QLabel {{
    background-color: transparent;
    border: none;
    color: {COLORS['text']};
}}
QTextEdit, QListWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    color: {COLORS['text']};
    font-family: 'Segoe UI';
    font-size: 11px;
    padding: 6px;
}}
QPushButton {{
    background-color: {COLORS['panel']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    color: {COLORS['text']};
    padding: 6px 12px;
    font-size: 10px;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_dim']};
    border-color: {COLORS['accent']};
    color: {COLORS['accent']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent']};
    color: {COLORS['bg']};
}}
QScrollBar:vertical {{
    background: {COLORS['surface']};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 4px;
}}
QSplitter::handle {{
    background: {COLORS['border']};
}}
"""
