OVERLAY_STYLE = """
/* ── Root ────────────────────────────────────────────── */
QWidget#OverlayRoot {
    background: transparent;
}

/* ── Main Card ──────────────────────────────────────── */
QFrame#Card {
    background-color: rgba(7, 5, 16, 252);
    border-radius: 16px;
    border: 1px solid rgba(108, 74, 255, 0.22);
}

/* ── Mic Button ─────────────────────────────────────── */
QPushButton#MicBtn {
    background: rgba(40, 28, 100, 235);
    border: 2px solid rgba(108, 74, 255, 0.38);
    border-radius: 24px;
    color: #ffffff;
    font-size: 20px;
    min-width: 48px; max-width: 48px;
    min-height: 48px; max-height: 48px;
}
QPushButton#MicBtn:hover {
    background: rgba(60, 42, 140, 245);
    border-color: rgba(140, 100, 255, 0.60);
}
QPushButton#MicBtn[state="recording"] {
    background: rgba(200, 30, 60, 240);
    border-color: rgba(255, 70, 100, 0.80);
}
QPushButton#MicBtn[state="processing"] {
    background: rgba(160, 100, 15, 240);
    border-color: rgba(230, 160, 35, 0.80);
}

/* ── Loopback Button ────────────────────────────────── */
QPushButton#LoopbackBtn {
    background: rgba(15, 10, 35, 220);
    border: 2px solid rgba(20, 200, 170, 0.20);
    border-radius: 20px;
    color: rgba(20, 200, 170, 0.45);
    font-size: 17px;
    min-width: 40px; max-width: 40px;
    min-height: 40px; max-height: 40px;
}
QPushButton#LoopbackBtn:hover {
    background: rgba(15, 50, 45, 230);
    border-color: rgba(20, 200, 170, 0.45);
    color: rgba(30, 220, 185, 0.80);
}
QPushButton#LoopbackBtn[active="true"] {
    background: rgba(10, 80, 70, 225);
    border-color: rgba(20, 210, 180, 0.70);
    color: rgba(40, 230, 195, 1.0);
}

/* ── Icon Buttons ────────────────────────────────────── */
QPushButton#IconBtn {
    background: transparent;
    border: none;
    border-radius: 12px;
    color: rgba(140, 130, 185, 0.45);
    font-size: 14px;
    min-width: 26px; max-width: 26px;
    min-height: 26px; max-height: 26px;
    padding: 0px;
}
QPushButton#IconBtn:hover {
    background-color: rgba(108, 80, 230, 0.12);
    color: rgba(195, 185, 240, 0.95);
}
QPushButton#IconBtn:pressed {
    background-color: rgba(90, 65, 200, 0.22);
}

/* ── Status / Labels ─────────────────────────────────── */
QLabel#StatusLbl {
    color: rgba(130, 120, 175, 0.65);
    font-size: 11px;
    font-family: "Segoe UI";
    padding-left: 4px;
}
QLabel#ModeBadge {
    background: rgba(70, 48, 175, 0.18);
    border: 1px solid rgba(100, 72, 220, 0.22);
    border-radius: 7px;
    color: rgba(150, 128, 255, 0.75);
    font-size: 9px;
    font-family: "Segoe UI";
    font-weight: bold;
    letter-spacing: 1px;
    padding: 1px 6px;
}

/* ── Divider ─────────────────────────────────────────── */
QFrame#Divider {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 transparent,
        stop:0.25 rgba(108, 74, 255, 0.18),
        stop:0.75 rgba(20, 200, 170, 0.14),
        stop:1 transparent);
    max-height: 1px;
    min-height: 1px;
    margin: 2px 0px;
}

/* ── Transcript ──────────────────────────────────────── */
QTextEdit#Transcript {
    background-color: rgba(5, 3, 12, 210);
    border: none;
    color: #ddd8f0;
    font-family: "Segoe UI", "Inter", Arial;
    font-size: 12.5px;
    padding: 8px 12px 4px 12px;
    line-height: 1.5;
    selection-background-color: rgba(100, 70, 220, 0.28);
}
QTextEdit#Transcript QScrollBar:vertical {
    background: transparent;
    width: 4px;
}
QTextEdit#Transcript QScrollBar::handle:vertical {
    background: rgba(100, 72, 220, 0.28);
    border-radius: 2px;
    min-height: 20px;
}
QTextEdit#Transcript QScrollBar::add-line:vertical,
QTextEdit#Transcript QScrollBar::sub-line:vertical,
QTextEdit#Transcript QScrollBar::add-page:vertical,
QTextEdit#Transcript QScrollBar::sub-page:vertical {
    height: 0px; background: transparent;
}

/* ── Live label ──────────────────────────────────────── */
QLabel#LiveLbl {
    color: rgba(160, 145, 210, 0.45);
    font-family: "Segoe UI";
    font-size: 12px;
    font-style: italic;
    padding: 3px 14px 4px 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.04);
}

/* ── AI Suggestions ──────────────────────────────────── */
QScrollArea#SuggestionsScroll {
    background: transparent;
    border: none;
    border-top: 1px solid rgba(108, 74, 255, 0.10);
}
QWidget#SuggestionsWidget {
    background: transparent;
}
QPushButton#AIPill {
    background: rgba(55, 40, 120, 0.28);
    border: 1px solid rgba(100, 70, 220, 0.28);
    border-radius: 11px;
    color: rgba(180, 165, 245, 0.88);
    font-family: "Segoe UI";
    font-size: 11px;
    padding: 3px 11px;
    min-height: 22px;
}
QPushButton#AIPill:hover {
    background: rgba(75, 55, 165, 0.48);
    border-color: rgba(120, 92, 255, 0.58);
    color: rgba(210, 198, 255, 1.0);
}
QPushButton#AIPill:pressed {
    background: rgba(55, 40, 130, 0.65);
}

/* ── Target window indicator ─────────────────────────── */
QLabel#TargetLbl {
    color: rgba(100, 190, 150, 0.55);
    font-size: 10px;
    font-family: "Segoe UI";
    padding: 0px 6px;
}
QLabel#TargetLbl[active="true"] {
    color: rgba(50, 220, 160, 0.80);
}

QSizeGrip { background: transparent; }
"""


SETTINGS_STYLE = """
QDialog {
    background-color: #06040e;
    color: #d0cce8;
}
QTabWidget::pane {
    border: 1px solid rgba(100, 70, 220, 0.14);
    border-radius: 11px;
    background-color: rgba(12, 8, 28, 225);
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: rgba(135, 125, 180, 0.62);
    padding: 7px 15px;
    font-family: "Segoe UI";
    font-size: 12px;
    border-bottom: 2px solid transparent;
    margin-right: 2px;
}
QTabBar::tab:selected {
    color: #c4bcf0;
    border-bottom: 2px solid #7b5fff;
}
QTabBar::tab:hover:!selected {
    color: rgba(185, 175, 225, 0.90);
}
QLabel {
    color: #a0a0c0;
    font-family: "Segoe UI";
    font-size: 12px;
}
QLabel#SectionHeader {
    color: #7868c8;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: rgba(20, 15, 45, 215);
    border: 1px solid rgba(85, 62, 175, 0.28);
    border-radius: 8px;
    color: #d0cce8;
    padding: 5px 10px;
    font-family: "Segoe UI";
    font-size: 12px;
    min-height: 30px;
}
QLineEdit:focus, QComboBox:focus {
    border-color: rgba(110, 82, 225, 0.62);
}
QComboBox::drop-down { border: none; padding-right: 8px; }
QComboBox QAbstractItemView {
    background-color: #0c081c;
    border: 1px solid rgba(85, 62, 175, 0.28);
    color: #d0cce8;
    selection-background-color: rgba(85, 62, 200, 0.38);
    outline: none;
}
QPushButton {
    background-color: rgba(48, 35, 108, 215);
    border: 1px solid rgba(85, 62, 175, 0.22);
    border-radius: 8px;
    color: #d0cce8;
    padding: 6px 16px;
    font-family: "Segoe UI";
    font-size: 12px;
    min-height: 30px;
}
QPushButton:hover {
    background-color: rgba(65, 48, 148, 230);
    border-color: rgba(105, 78, 215, 0.42);
}
QPushButton:pressed { background-color: rgba(38, 28, 88, 215); }
QPushButton#SaveBtn {
    background-color: rgba(65, 46, 195, 225);
    border-color: rgba(95, 72, 228, 0.48);
    font-weight: bold;
}
QPushButton#SaveBtn:hover { background-color: rgba(82, 58, 218, 235); }
QPushButton#TestBtn {
    background-color: rgba(22, 88, 75, 200);
    border-color: rgba(40, 175, 150, 0.32);
    color: rgba(65, 215, 185, 0.88);
    padding: 4px 11px;
    min-height: 26px;
    font-size: 11px;
}
QPushButton#TestBtn:hover {
    background-color: rgba(28, 108, 92, 220);
    border-color: rgba(50, 195, 168, 0.52);
}
QCheckBox {
    color: #a0a0c0;
    spacing: 8px;
    font-family: "Segoe UI";
    font-size: 12px;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid rgba(85, 62, 175, 0.42);
    background: rgba(14, 10, 32, 195);
}
QCheckBox::indicator:checked {
    background: rgba(85, 60, 208, 228);
    border-color: rgba(105, 80, 232, 0.78);
}
QRadioButton {
    color: #a0a0c0;
    spacing: 8px;
    font-family: "Segoe UI";
    font-size: 12px;
}
QRadioButton::indicator {
    width: 15px; height: 15px;
    border-radius: 7px;
    border: 1px solid rgba(85, 62, 175, 0.42);
    background: rgba(14, 10, 32, 195);
}
QRadioButton::indicator:checked {
    background: rgba(85, 60, 208, 228);
    border-color: rgba(105, 80, 232, 0.78);
}
QGroupBox {
    border: 1px solid rgba(85, 62, 175, 0.16);
    border-radius: 10px;
    margin-top: 13px;
    font-family: "Segoe UI";
    font-size: 11px;
    color: #6e5ec8;
    padding: 9px 8px 8px 8px;
}
QGroupBox::title { subcontrol-origin: margin; left: 11px; padding: 0 5px; }
QListWidget {
    background-color: rgba(14, 10, 32, 205);
    border: 1px solid rgba(85, 62, 175, 0.22);
    border-radius: 8px;
    color: #d0cce8;
    font-family: "Segoe UI";
    font-size: 12px;
    outline: none;
}
QListWidget::item { padding: 5px 10px; border-radius: 4px; }
QListWidget::item:selected { background: rgba(85, 60, 210, 0.38); color: #e0d8ff; }
QListWidget::item:hover:!selected { background: rgba(65, 48, 150, 0.18); }
QSlider::groove:horizontal {
    height: 4px;
    background: rgba(55, 42, 112, 0.42);
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: rgba(95, 70, 218, 0.88);
    border: 1px solid rgba(115, 88, 238, 0.58);
    width: 14px; height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: rgba(95, 70, 218, 0.52);
    border-radius: 2px;
}
QPushButton#HotkeyBtn {
    background-color: rgba(20, 15, 45, 215);
    border: 1px solid rgba(85, 62, 175, 0.36);
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
    letter-spacing: 1px;
    min-width: 168px;
    color: #c0b4f0;
}
QPushButton#HotkeyBtn[listening="true"] {
    border-color: rgba(228, 185, 45, 0.78);
    color: rgba(238, 208, 65, 0.95);
    background-color: rgba(48, 36, 10, 205);
}
QScrollBar:vertical { background: transparent; width: 4px; }
QScrollBar::handle:vertical {
    background: rgba(95, 72, 200, 0.28);
    border-radius: 2px;
    min-height: 20px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""
