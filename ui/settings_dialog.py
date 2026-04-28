from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QSlider, QSpinBox, QSizePolicy,
    QButtonGroup, QRadioButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ui.styles import SETTINGS_STYLE
from utils.config import Config
from utils.hotkey import HotkeyManager
from core.audio import AudioCapture


class SettingsDialog(QDialog):
    saved = pyqtSignal()

    def __init__(self, config: Config, hotkeys: HotkeyManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.hotkeys = hotkeys
        self._listening_hotkey = False
        self._new_hotkey = ""

        self.setWindowTitle("Настройки — WhisperOverlay")
        self.setStyleSheet(SETTINGS_STYLE)
        self.setMinimumWidth(440)
        self.setMinimumHeight(460)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint
        )
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), "Основные")
        tabs.addTab(self._tab_audio(), "Аудио")
        tabs.addTab(self._tab_azure(), "Azure")
        tabs.addTab(self._tab_hotkeys(), "Хоткей")
        layout.addWidget(tabs)

        # buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("SaveBtn")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def _tab_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        self._cb_backend = QComboBox()
        self._cb_backend.addItems(["Локально (faster-whisper)", "Azure Speech Services"])
        form.addRow("Бэкенд:", self._cb_backend)

        self._cb_model = QComboBox()
        self._cb_model.addItems(["tiny", "base", "small", "medium", "large-v3"])
        form.addRow("Модель:", self._cb_model)

        self._cb_device = QComboBox()
        self._cb_device.addItems(["cuda", "cpu"])
        form.addRow("Устройство:", self._cb_device)

        self._cb_language = QComboBox()
        self._cb_language.addItems(["ru", "en", "de", "uk"])
        form.addRow("Язык речи:", self._cb_language)

        self._chk_translate = QCheckBox("Включить перевод")
        form.addRow("", self._chk_translate)

        self._chk_en = QCheckBox("Переводить на EN")
        self._chk_de = QCheckBox("Переводить на DE")
        form.addRow("", self._chk_en)
        form.addRow("", self._chk_de)

        # Recording mode
        mode_group = QGroupBox("Режим записи")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(6)
        self._rb_toggle = QRadioButton("Toggle — нажал один раз для старта, ещё раз для стопа")
        self._rb_ptt = QRadioButton("Push-to-talk — зажми и говори, отпусти — стоп")
        self._bg_mode = QButtonGroup(self)
        self._bg_mode.addButton(self._rb_toggle, 0)
        self._bg_mode.addButton(self._rb_ptt, 1)
        mode_layout.addWidget(self._rb_toggle)
        mode_layout.addWidget(self._rb_ptt)
        form.addRow(mode_group)

        self._chk_inject = QCheckBox("Вставлять текст в активное окно")
        form.addRow("", self._chk_inject)

        # opacity
        opacity_row = QHBoxLayout()
        self._sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self._sld_opacity.setRange(40, 100)
        self._sld_opacity.setTickInterval(10)
        self._opacity_lbl = QLabel("94%")
        self._sld_opacity.valueChanged.connect(
            lambda v: self._opacity_lbl.setText(f"{v}%")
        )
        opacity_row.addWidget(self._sld_opacity)
        opacity_row.addWidget(self._opacity_lbl)
        form.addRow("Прозрачность:", opacity_row)

        return w

    def _tab_audio(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        self._cb_device_audio = QComboBox()
        self._cb_device_audio.addItem("По умолчанию", userData=None)
        try:
            for d in AudioCapture.list_devices():
                self._cb_device_audio.addItem(d["name"], userData=d["index"])
        except Exception:
            pass
        form.addRow("Микрофон:", self._cb_device_audio)

        return w

    def _tab_azure(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        grp_stt = QGroupBox("Azure Speech Services (STT)")
        stt_form = QFormLayout(grp_stt)
        self._le_speech_key = QLineEdit()
        self._le_speech_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._le_speech_key.setPlaceholderText("Ключ подписки")
        self._le_speech_region = QLineEdit()
        self._le_speech_region.setPlaceholderText("westeurope")
        stt_form.addRow("API Key:", self._le_speech_key)
        stt_form.addRow("Region:", self._le_speech_region)
        form.addRow(grp_stt)

        grp_tr = QGroupBox("Azure Translator (перевод)")
        tr_form = QFormLayout(grp_tr)
        self._le_tr_key = QLineEdit()
        self._le_tr_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._le_tr_key.setPlaceholderText("Ключ подписки")
        self._le_tr_region = QLineEdit()
        self._le_tr_region.setPlaceholderText("westeurope")
        tr_form.addRow("API Key:", self._le_tr_key)
        tr_form.addRow("Region:", self._le_tr_region)
        form.addRow(grp_tr)

        info = QLabel(
            "Azure Speech: portal.azure.com → Cognitive Services → Speech\n"
            "Azure Translator: portal.azure.com → Cognitive Services → Translator"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: rgba(120,120,160,0.7); font-size: 11px;")
        form.addRow(info)

        return w

    def _tab_hotkeys(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Глобальный хоткей (запись/стоп):"))

        key_row = QHBoxLayout()
        self._hotkey_btn = QPushButton()
        self._hotkey_btn.setObjectName("HotkeyBtn")
        self._hotkey_btn.setFixedWidth(140)
        self._hotkey_btn.clicked.connect(self._start_listening_hotkey)
        key_row.addWidget(self._hotkey_btn)
        self._hotkey_hint = QLabel("Нажми кнопку и нажми нужную клавишу")
        self._hotkey_hint.setStyleSheet("color: rgba(120,120,160,0.7); font-size: 11px;")
        key_row.addWidget(self._hotkey_hint)
        key_row.addStretch()
        layout.addLayout(key_row)

        info2 = QLabel(
            "Хоткей работает глобально (даже когда окно свёрнуто).\n"
            "Нажать = начать запись / отпустить = остановить (PTT).\n"
            "Быстрое нажатие + отпуск = режим Toggle."
        )
        info2.setWordWrap(True)
        info2.setStyleSheet("color: rgba(120,120,160,0.7); font-size: 11px;")
        layout.addWidget(info2)
        layout.addStretch()
        return w

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_values(self):
        # General
        backend = self.config.get("backend", default="local")
        self._cb_backend.setCurrentIndex(0 if backend == "local" else 1)

        model = self.config.get("model", default="small")
        idx = self._cb_model.findText(model)
        if idx >= 0:
            self._cb_model.setCurrentIndex(idx)

        device = self.config.get("device", default="cuda")
        self._cb_device.setCurrentIndex(0 if device == "cuda" else 1)

        lang = self.config.get("language", default="ru")
        lidx = self._cb_language.findText(lang)
        if lidx >= 0:
            self._cb_language.setCurrentIndex(lidx)

        mode = self.config.get("recording_mode", default="toggle")
        self._rb_ptt.setChecked(mode == "ptt")
        self._rb_toggle.setChecked(mode != "ptt")

        self._chk_translate.setChecked(bool(self.config.get("translate_enabled", default=True)))
        targets = self.config.get("translate_to", default=["en", "de"])
        self._chk_en.setChecked("en" in targets)
        self._chk_de.setChecked("de" in targets)
        self._chk_inject.setChecked(bool(self.config.get("auto_inject", default=True)))

        opacity_pct = int(self.config.get("window", "opacity", default=0.94) * 100)
        self._sld_opacity.setValue(opacity_pct)
        self._opacity_lbl.setText(f"{opacity_pct}%")

        # Audio device
        saved_device = self.config.get("audio", "device_index")
        if saved_device is not None:
            for i in range(self._cb_device_audio.count()):
                if self._cb_device_audio.itemData(i) == saved_device:
                    self._cb_device_audio.setCurrentIndex(i)
                    break

        # Azure
        self._le_speech_key.setText(self.config.get("azure", "speech_key", default=""))
        self._le_speech_region.setText(
            self.config.get("azure", "speech_region", default="westeurope")
        )
        self._le_tr_key.setText(self.config.get("azure", "translator_key", default=""))
        self._le_tr_region.setText(
            self.config.get("azure", "translator_region", default="westeurope")
        )

        # Hotkey
        current_key = self.config.get("hotkey", default="f9")
        self._hotkey_btn.setText(current_key.upper())
        self._new_hotkey = current_key

    def _save(self):
        backend = "local" if self._cb_backend.currentIndex() == 0 else "azure"
        self.config["backend"] = backend
        self.config["model"] = self._cb_model.currentText()
        self.config["device"] = self._cb_device.currentText()
        self.config["language"] = self._cb_language.currentText()
        self.config["recording_mode"] = "ptt" if self._rb_ptt.isChecked() else "toggle"
        self.config["translate_enabled"] = self._chk_translate.isChecked()

        targets = []
        if self._chk_en.isChecked():
            targets.append("en")
        if self._chk_de.isChecked():
            targets.append("de")
        self.config["translate_to"] = targets
        self.config["auto_inject"] = self._chk_inject.isChecked()
        self.config.set("window", "opacity", self._sld_opacity.value() / 100.0)

        audio_device = self._cb_device_audio.currentData()
        self.config.set("audio", "device_index", audio_device)

        self.config.set("azure", "speech_key", self._le_speech_key.text().strip())
        self.config.set("azure", "speech_region", self._le_speech_region.text().strip())
        self.config.set("azure", "translator_key", self._le_tr_key.text().strip())
        self.config.set("azure", "translator_region", self._le_tr_region.text().strip())

        if self._new_hotkey:
            self.config["hotkey"] = self._new_hotkey

        self.config.save()
        self.saved.emit()
        self.accept()

    # ── Hotkey capture ────────────────────────────────────────────────────────

    def _start_listening_hotkey(self):
        self._listening_hotkey = True
        self._hotkey_btn.setText("Нажми клавишу...")
        self._hotkey_btn.setProperty("listening", "true")
        self._hotkey_btn.style().unpolish(self._hotkey_btn)
        self._hotkey_btn.style().polish(self._hotkey_btn)
        self.grabKeyboard()

    def keyPressEvent(self, event):
        if self._listening_hotkey:
            key_text = event.text().lower()
            if not key_text:
                from PyQt6.QtCore import Qt as _Qt
                key = event.key()
                special = {
                    _Qt.Key.Key_F1: "f1", _Qt.Key.Key_F2: "f2", _Qt.Key.Key_F3: "f3",
                    _Qt.Key.Key_F4: "f4", _Qt.Key.Key_F5: "f5", _Qt.Key.Key_F6: "f6",
                    _Qt.Key.Key_F7: "f7", _Qt.Key.Key_F8: "f8", _Qt.Key.Key_F9: "f9",
                    _Qt.Key.Key_F10: "f10", _Qt.Key.Key_F11: "f11", _Qt.Key.Key_F12: "f12",
                    _Qt.Key.Key_Insert: "insert", _Qt.Key.Key_Home: "home",
                    _Qt.Key.Key_End: "end", _Qt.Key.Key_PageUp: "page_up",
                    _Qt.Key.Key_PageDown: "page_down",
                    _Qt.Key.Key_Escape: None,
                }
                key_text = special.get(key, "")
                if key_text is None:  # Escape = cancel
                    self._listening_hotkey = False
                    self._hotkey_btn.setText(self._new_hotkey.upper())
                    self._hotkey_btn.setProperty("listening", "false")
                    self._hotkey_btn.style().unpolish(self._hotkey_btn)
                    self._hotkey_btn.style().polish(self._hotkey_btn)
                    self.releaseKeyboard()
                    return
            if key_text:
                self._new_hotkey = key_text
                self._hotkey_btn.setText(key_text.upper())
                self._hotkey_btn.setProperty("listening", "false")
                self._hotkey_btn.style().unpolish(self._hotkey_btn)
                self._hotkey_btn.style().polish(self._hotkey_btn)
            self._listening_hotkey = False
            self.releaseKeyboard()
            return
        super().keyPressEvent(event)
