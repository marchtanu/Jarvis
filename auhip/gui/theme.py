# auhip GUI Theme — Synthesized Design (Apple + Claude + Notion)
# Core concept: Claude's warm cream canvas, Apple's minimal typography,
# Notion's clean card borders, one warm coral-to-navy accent.

COLORS = {
    # === Surfaces ===
    "bg":            "#F8F5F0",   # Warm cream canvas (Claude)
    "surface":       "#FFFFFF",   # Pure white for elevated cards (Notion)
    "panel":         "#FFFFFF",   # Card background
    "panel_soft":    "#F0EBE3",   # Slightly darker cream for feature cards (Claude)
    "nav":           "#141413",   # Near-black nav bar (Apple)
    "dark_card":     "#1C1A18",   # Warm dark navy for code/log panels (Claude)

    # === Borders ===
    "border":        "#E6DFD8",   # Warm hairline (Claude — same as primary-disabled)
    "border_soft":   "#EBE6DF",   # Softer divider
    "border_dark":   "#2E2B27",   # Dark surface hairline

    # === Accent ===
    "accent":        "#CC785C",   # Coral primary (Claude) — warm, editorial
    "accent_hover":  "#A9583E",   # Coral active/press
    "accent_dim":    "#F0E8E2",   # Light coral tint for selections
    "accent_yellow": "#E8A55A",   # Amber companion (Claude)

    # === Text on light ===
    "text":          "#141413",   # Ink — warm near-black (Claude)
    "text_body":     "#3D3D3A",   # Body text
    "text_muted":    "#6C6A64",   # Muted labels (Claude)
    "text_soft":     "#8E8B82",   # Captions, fine print

    # === Text on dark ===
    "text_on_dark":  "#FAF9F5",   # Cream white on dark surfaces (Claude)
    "text_on_dark_muted": "#A09D96", # Muted on dark

    # === Semantic ===
    "success":       "#5DB872",   # Green (Claude semantic)
    "warning":       "#E8A55A",   # Amber
    "danger":        "#C64545",   # Red

    # Legacy aliases used in older code
    "processing":    "#CC785C",
    "shutdown":      "#C64545",
}

STATE_COLORS = {
    "STANDBY":           "#8E8B82",   # Soft muted
    "SNAP_DETECTED":     "#E8A55A",   # Amber — attention
    "WAITING_WAKE_WORD": "#CC785C",   # Coral — listening
    "VOICE_MODE":        "#141413",   # Ink — active voice
    "CAMERA_MODE":       "#5DB872",   # Green — camera/gesture
    "CONTROL_MODE":      "#3B82F6",   # Blue — cursor control
    "PROCESSING":        "#CC785C",   # Coral — working
    "SLEEP":             "#8E8B82",   # Soft muted
    "SHUTDOWN":          "#C64545",   # Red
    # Legacy alias
    "COMMAND_MODE":      "#141413",
}

RESPONSE_COLORS = {
    "info":     "#6C6A64",
    "success":  "#5DB872",
    "warning":  "#E8A55A",
    "response": "#141413",
    "shutdown": "#C64545",
    "greeting": "#CC785C",
}

STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F8F5F0;
    color: #141413;
    font-family: 'Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Helvetica', 'sans-serif';
    font-size: 14px;
}
QFrame {
    background-color: #FFFFFF;
    border: 1px solid #E6DFD8;
    border-radius: 12px;
}
QLabel {
    background-color: transparent;
    border: none;
    color: #141413;
}
QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #E6DFD8;
    border-radius: 8px;
    color: #3D3D3A;
    padding: 12px;
    font-size: 14px;
    line-height: 1.55;
    selection-background-color: #F0E8E2;
    selection-color: #141413;
}
QListWidget {
    background-color: transparent;
    border: none;
    color: #3D3D3A;
    font-size: 14px;
}
QListWidget::item {
    padding: 10px 0;
    border-bottom: 1px solid #EBE6DF;
}
QListWidget::item:selected {
    background: transparent;
    color: #CC785C;
}
QPushButton {
    background-color: #CC785C;
    border: none;
    border-radius: 8px;
    color: #FFFFFF;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #A9583E;
}
QPushButton:pressed {
    background-color: #8E4A32;
}
QCheckBox {
    color: #6C6A64;
    font-size: 13px;
    spacing: 6px;
}
QScrollBar:vertical {
    background: transparent;
    width: 5px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #E6DFD8;
    min-height: 20px;
    border-radius: 2px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QSplitter::handle {
    background: transparent;
}
"""
