OVERLAY_STYLE = """
QWidget#OverlayRoot {
    background: transparent;
}

QFrame#Card {
    background-color: rgba(14, 14, 26, 240);
    border-radius: 18px;
    border: 1px solid rgba(255, 255, 255, 0.07);
}

QPushButton#MicBtn {
    background-color: rgba(28, 28, 52, 220);
    border: 2px solid rgba(90, 90, 180, 0.45);
    border-radius: 22px;
    color: #ffffff;
    font-size: 20px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
}
QPushButton#MicBtn:hover {
    background-color: rgba(45, 45, 80, 230);
    border-color: rgba(120, 120, 220, 0.65);
}
QPushButton#MicBtn[state="recording"] {
    background-color: rgba(200, 35, 55, 215);
    border-color: rgba(255, 70, 90, 0.85);
}
QPushButton#MicBtn[state="processing"] {
    background-color: rgba(160, 100, 20, 215);
    border-color: rgba(220, 150, 40, 0.85);
}

QPushButton#IconBtn {
    background: transparent;
    border: none;
    border-radius: 13px;
    color: rgba(160, 160, 195, 0.65);
    font-size: 15px;
    min-width: 26px;
    max-width: 26px;
    min-height: 26px;
    max-height: 26px;
    padding: 0px;
}
QPushButton#IconBtn:hover {
    background-color: rgba(255, 255, 255, 0.07);
    color: rgba(210, 210, 240, 0.95);
}

QLabel#StatusLbl {
    color: rgba(150, 150, 185, 0.75);
    font-size: 11px;
    font-family: "Segoe UI";
    padding-left: 4px;
}

QFrame#Divider {
    background: rgba(255, 255, 255, 0.06);
    max-height: 1px;
    min-height: 1px;
}

QLabel#LiveLbl {
    color: rgba(180, 180, 210, 0.55);
    font-family: "Segoe UI";
    font-size: 12px;
    font-style: italic;
    padding: 4px 14px 6px 14px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

QTextEdit#Transcript {
    background-color: rgba(8, 8, 18, 190);
    border: none;
    border-radius: 0px;
    color: #d8d8e8;
    font-family: "Segoe UI", Arial;
    font-size: 12px;
    padding: 10px 14px;
    selection-background-color: rgba(90, 90, 220, 0.35);
}
QTextEdit#Transcript QScrollBar:vertical {
    background: transparent;
    width: 5px;
}
QTextEdit#Transcript QScrollBar::handle:vertical {
    background: rgba(120, 120, 170, 0.4);
    border-radius: 2px;
    min-height: 18px;
}
QTextEdit#Transcript QScrollBar::add-line:vertical,
QTextEdit#Transcript QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

SETTINGS_STYLE = """
QDialog {
    background-color: #0b0b18;
    color: #d8d8e8;
}
QTabWidget::pane {
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    background-color: rgba(16, 16, 30, 210);
    top: -1px;
}
QTabBar::tab {
    background: transparent;
    color: rgba(150, 150, 185, 0.7);
    padding: 8px 18px;
    font-family: "Segoe UI";
    font-size: 12px;
    border-bottom: 2px solid transparent;
}
QTabBar::tab:selected {
    color: #d8d8f0;
    border-bottom: 2px solid #6868cc;
}
QTabBar::tab:hover:!selected {
    color: #b8b8d8;
}
QLabel {
    color: #aaaac8;
    font-family: "Segoe UI";
    font-size: 12px;
}
QLabel#SectionHeader {
    color: #8888cc;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: rgba(28, 28, 50, 200);
    border: 1px solid rgba(90, 90, 170, 0.35);
    border-radius: 7px;
    color: #d8d8e8;
    padding: 6px 10px;
    font-family: "Segoe UI";
    font-size: 12px;
    min-height: 28px;
}
QLineEdit:focus, QComboBox:focus {
    border-color: rgba(110, 110, 210, 0.7);
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #12121e;
    border: 1px solid rgba(90, 90, 170, 0.35);
    color: #d8d8e8;
    selection-background-color: rgba(80, 80, 200, 0.4);
}
QPushButton {
    background-color: rgba(55, 55, 115, 200);
    border: none;
    border-radius: 7px;
    color: #d8d8f0;
    padding: 8px 20px;
    font-family: "Segoe UI";
    font-size: 12px;
    min-height: 32px;
}
QPushButton:hover {
    background-color: rgba(75, 75, 155, 220);
}
QPushButton:pressed {
    background-color: rgba(45, 45, 95, 200);
}
QPushButton#SaveBtn {
    background-color: rgba(60, 120, 200, 210);
    font-weight: bold;
}
QPushButton#SaveBtn:hover {
    background-color: rgba(75, 140, 225, 230);
}
QCheckBox {
    color: #aaaac8;
    spacing: 8px;
    font-family: "Segoe UI";
    font-size: 12px;
}
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border-radius: 4px;
    border: 1px solid rgba(90, 90, 170, 0.5);
    background: rgba(18, 18, 35, 180);
}
QCheckBox::indicator:checked {
    background: rgba(75, 75, 200, 220);
    border-color: rgba(100, 100, 220, 0.8);
}
QGroupBox {
    border: 1px solid rgba(90, 90, 170, 0.2);
    border-radius: 8px;
    margin-top: 12px;
    font-family: "Segoe UI";
    font-size: 12px;
    color: #8888cc;
    padding: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
QPushButton#HotkeyBtn {
    background-color: rgba(30, 30, 55, 200);
    border: 1px solid rgba(90, 90, 170, 0.4);
    font-family: "Consolas", monospace;
    font-size: 13px;
    letter-spacing: 1px;
    min-width: 120px;
}
QPushButton#HotkeyBtn[listening="true"] {
    border-color: rgba(220, 180, 40, 0.8);
    color: rgba(220, 200, 80, 0.9);
}
"""
