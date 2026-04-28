import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from utils.config import Config
from utils.hotkey import HotkeyManager
from ui.overlay import OverlayWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WhisperOverlay")
    app.setFont(QFont("Segoe UI", 10))

    config = Config()
    hotkeys = HotkeyManager()

    window = OverlayWindow(config, hotkeys)
    window.show()

    result = app.exec()
    sys.exit(result)


if __name__ == "__main__":
    main()
