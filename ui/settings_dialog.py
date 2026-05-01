import os
import subprocess
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QSlider, QSizePolicy,
    QButtonGroup, QRadioButton, QListWidget, QListWidgetItem,
    QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from ui.styles import SETTINGS_STYLE
from utils.config import Config
from utils.hotkey import HotkeyManager, parse_hotkey, MODIFIER_KEYS
from core.audio import AudioCapture

AVAILABLE_LANGS = [
    ("auto", "Auto-detect"),
    ("ru", "Русский (RU)"),
    ("en", "English (EN)"),
    ("de", "Deutsch (DE)"),
    ("uk", "Українська (UK)"),
    ("fr", "Français (FR)"),
    ("es", "Español (ES)"),
    ("it", "Italiano (IT)"),
    ("pl", "Polski (PL)"),
    ("zh", "中文 (ZH)"),
    ("ja", "日本語 (JA)"),
]

TRANSLATE_LANGS = [
    ("ru", "RU — Русский"),
    ("en", "EN — English"),
    ("de", "DE — Deutsch"),
    ("uk", "UK — Українська"),
    ("fr", "FR — Français"),
    ("es", "ES — Español"),
    ("it", "IT — Italiano"),
    ("pl", "PL — Polski"),
]


class SettingsDialog(QDialog):
    saved = pyqtSignal()

    def __init__(self, config: Config, hotkeys: HotkeyManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.hotkeys = hotkeys
        self._listening_hotkey = False
        self._new_hotkey = ""
        self._held_mods: set = set()

        self.setWindowTitle("Настройки — WhisperOverlay")
        self.setStyleSheet(SETTINGS_STYLE)
        self.setMinimumWidth(500)
        self.setMinimumHeight(520)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._tab_general(), "Основные")
        tabs.addTab(self._tab_sources(), "Источники")
        tabs.addTab(self._tab_azure(), "Azure")
        tabs.addTab(self._tab_ai(), "AI Подсказки")
        tabs.addTab(self._tab_hotkeys(), "Хоткей")
        tabs.addTab(self._tab_logs(), "Логи")
        layout.addWidget(tabs)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Сохранить")
        save_btn.setObjectName("SaveBtn")
        save_btn.clicked.connect(self._save)
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
        for code, label in AVAILABLE_LANGS:
            self._cb_language.addItem(label, userData=code)
        form.addRow("Мой язык:", self._cb_language)

        # Recording mode
        mode_group = QGroupBox("Режим записи")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(6)
        self._rb_toggle = QRadioButton("Toggle — нажал один раз старт, ещё раз стоп")
        self._rb_ptt = QRadioButton("Push-to-talk — зажми и говори, отпусти — стоп")
        self._bg_mode = QButtonGroup(self)
        self._bg_mode.addButton(self._rb_toggle, 0)
        self._bg_mode.addButton(self._rb_ptt, 1)
        mode_layout.addWidget(self._rb_toggle)
        mode_layout.addWidget(self._rb_ptt)
        form.addRow(mode_group)

        self._chk_inject = QCheckBox("Вставлять текст в активное окно (clipboard)")
        form.addRow("", self._chk_inject)

        # Opacity
        opacity_row = QHBoxLayout()
        self._sld_opacity = QSlider(Qt.Orientation.Horizontal)
        self._sld_opacity.setRange(40, 100)
        self._sld_opacity.setTickInterval(10)
        self._opacity_lbl = QLabel("95%")
        self._sld_opacity.valueChanged.connect(lambda v: self._opacity_lbl.setText(f"{v}%"))
        opacity_row.addWidget(self._sld_opacity)
        opacity_row.addWidget(self._opacity_lbl)
        form.addRow("Прозрачность:", opacity_row)

        return w

    def _tab_sources(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # My microphone
        mic_group = QGroupBox("Мой микрофон")
        mic_form = QFormLayout(mic_group)
        self._cb_mic = QComboBox()
        self._cb_mic.addItem("По умолчанию", userData=None)
        try:
            for d in AudioCapture.list_devices():
                self._cb_mic.addItem(d["name"], userData=d["index"])
        except Exception:
            pass

        # Translation for my voice
        self._chk_translate = QCheckBox("Переводить мой голос")
        self._lw_translate = QListWidget()
        self._lw_translate.setFixedHeight(110)
        self._lw_translate.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for code, label in TRANSLATE_LANGS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._lw_translate.addItem(item)

        mic_form.addRow("Устройство:", self._cb_mic)
        mic_form.addRow("", self._chk_translate)
        mic_form.addRow("Переводить на:", self._lw_translate)
        layout.addWidget(mic_group)

        # System audio (loopback)
        lb_group = QGroupBox("Системный звук (Zoom / собеседник)")
        lb_form = QFormLayout(lb_group)

        self._chk_loopback = QCheckBox("Захватывать системный аудио (WASAPI loopback)")
        lb_form.addRow("", self._chk_loopback)

        self._cb_loopback_dev = QComboBox()
        self._cb_loopback_dev.addItem("По умолчанию", userData=None)
        try:
            from core.audio_loopback import LoopbackCapture
            for d in LoopbackCapture.list_devices():
                self._cb_loopback_dev.addItem(d["name"], userData=d["name"])
        except Exception:
            pass
        lb_form.addRow("Динамик/выход:", self._cb_loopback_dev)

        self._cb_loopback_lang = QComboBox()
        for code, label in AVAILABLE_LANGS:
            self._cb_loopback_lang.addItem(label, userData=code)
        lb_form.addRow("Язык собеседника:", self._cb_loopback_lang)

        self._chk_lb_translate = QCheckBox("Переводить речь собеседника")
        lb_form.addRow("", self._chk_lb_translate)

        self._lw_lb_translate = QListWidget()
        self._lw_lb_translate.setFixedHeight(110)
        self._lw_lb_translate.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for code, label in TRANSLATE_LANGS:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, code)
            self._lw_lb_translate.addItem(item)
        lb_form.addRow("Переводить на:", self._lw_lb_translate)

        note = QLabel("⚠ Для захвата Zoom требуется WASAPI loopback.\nЗапусти приложение от имени администратора если не работает.")
        note.setWordWrap(True)
        note.setStyleSheet("color: rgba(180,160,80,0.75); font-size: 10px; padding-top: 4px;")
        lb_form.addRow(note)

        layout.addWidget(lb_group)
        layout.addStretch()
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

        info = QLabel("portal.azure.com → Cognitive Services → Speech / Translator")
        info.setWordWrap(True)
        info.setStyleSheet("color: rgba(120,120,160,0.65); font-size: 10px;")
        form.addRow(info)
        return w

    def _tab_ai(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        self._chk_ai = QCheckBox("Включить AI подсказки")
        form.addRow("", self._chk_ai)

        backend_group = QGroupBox("Бэкенд")
        backend_layout = QVBoxLayout(backend_group)
        self._rb_ollama = QRadioButton("Ollama (локально, бесплатно)")
        self._rb_openai = QRadioButton("OpenAI-совместимый (Azure, OpenAI, и др.)")
        self._bg_ai = QButtonGroup(self)
        self._bg_ai.addButton(self._rb_ollama, 0)
        self._bg_ai.addButton(self._rb_openai, 1)
        backend_layout.addWidget(self._rb_ollama)
        backend_layout.addWidget(self._rb_openai)
        form.addRow(backend_group)

        self._le_ai_endpoint = QLineEdit()
        self._le_ai_endpoint.setPlaceholderText("http://localhost:11434")
        form.addRow("Endpoint:", self._le_ai_endpoint)

        self._le_ai_model = QLineEdit()
        self._le_ai_model.setPlaceholderText("llama3.2:3b")
        form.addRow("Модель:", self._le_ai_model)

        self._le_ai_key = QLineEdit()
        self._le_ai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._le_ai_key.setPlaceholderText("(пусто для Ollama)")
        form.addRow("API Key:", self._le_ai_key)

        test_row = QHBoxLayout()
        test_btn = QPushButton("Проверить соединение")
        test_btn.setObjectName("TestBtn")
        test_btn.clicked.connect(self._test_ai)
        self._ai_test_lbl = QLabel("")
        self._ai_test_lbl.setStyleSheet("font-size: 11px;")
        test_row.addWidget(test_btn)
        test_row.addWidget(self._ai_test_lbl)
        test_row.addStretch()
        form.addRow("", test_row)

        info = QLabel("Ollama: ollama.ai — установи и запусти модель: ollama pull llama3.2:3b")
        info.setWordWrap(True)
        info.setStyleSheet("color: rgba(120,120,160,0.65); font-size: 10px;")
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
        self._hotkey_btn.setFixedWidth(180)
        self._hotkey_btn.clicked.connect(self._start_listening_hotkey)
        key_row.addWidget(self._hotkey_btn)
        key_row.addStretch()
        layout.addLayout(key_row)

        hint = QLabel(
            "Нажми кнопку выше, затем нажми нужную комбинацию клавиш.\n"
            "Поддерживаются: F1–F12, Ctrl+Shift+X, Alt+X и другие.\n"
            "Escape — отмена."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: rgba(130,120,175,0.70); font-size: 11px;")
        layout.addWidget(hint)
        layout.addStretch()
        return w

    def _tab_logs(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setSpacing(12)
        form.setContentsMargins(16, 16, 16, 16)

        self._chk_log = QCheckBox("Вести лог сессий")
        form.addRow("", self._chk_log)

        self._le_log_dir = QLineEdit()
        self._le_log_dir.setPlaceholderText("(по умолчанию: папка logs/ рядом с приложением)")
        form.addRow("Папка логов:", self._le_log_dir)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Открыть папку логов")
        open_btn.setObjectName("TestBtn")
        open_btn.clicked.connect(self._open_log_dir)
        btn_row.addWidget(open_btn)
        btn_row.addStretch()
        form.addRow("", btn_row)

        info = QLabel(
            "Логи пишутся в формате JSONL.\n"
            "Каждая строка: {ts, channel, text, lang, translation}.\n"
            "Файл: session_YYYY-MM-DD.jsonl"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: rgba(120,120,160,0.65); font-size: 10px;")
        form.addRow(info)
        return w

    # ── Load / Save ───────────────────────────────────────────────────────────

    def _load_values(self):
        backend = self.config.get("backend", default="local")
        self._cb_backend.setCurrentIndex(0 if backend == "local" else 1)

        model = self.config.get("model", default="small")
        idx = self._cb_model.findText(model)
        if idx >= 0:
            self._cb_model.setCurrentIndex(idx)

        device = self.config.get("device", default="cuda")
        self._cb_device.setCurrentIndex(0 if device == "cuda" else 1)

        lang = self.config.get("language", default="auto")
        for i in range(self._cb_language.count()):
            if self._cb_language.itemData(i) == lang:
                self._cb_language.setCurrentIndex(i)
                break

        mode = self.config.get("recording_mode", default="toggle")
        self._rb_ptt.setChecked(mode == "ptt")
        self._rb_toggle.setChecked(mode != "ptt")
        self._chk_inject.setChecked(bool(self.config.get("auto_inject", default=True)))

        opacity_pct = int(self.config.get("window", "opacity", default=0.95) * 100)
        self._sld_opacity.setValue(opacity_pct)
        self._opacity_lbl.setText(f"{opacity_pct}%")

        # Sources - mic
        saved_mic = self.config.get("audio", "device_index")
        if saved_mic is not None:
            for i in range(self._cb_mic.count()):
                if self._cb_mic.itemData(i) == saved_mic:
                    self._cb_mic.setCurrentIndex(i)
                    break

        self._chk_translate.setChecked(bool(self.config.get("translate_enabled", default=False)))
        targets = self.config.get("translate_to", default=["de", "en"])
        for i in range(self._lw_translate.count()):
            item = self._lw_translate.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in targets:
                item.setSelected(True)

        # Sources - loopback
        self._chk_loopback.setChecked(bool(self.config.get("loopback_enabled", default=False)))
        saved_lb = self.config.get("loopback_device")
        if saved_lb:
            for i in range(self._cb_loopback_dev.count()):
                if self._cb_loopback_dev.itemData(i) == saved_lb:
                    self._cb_loopback_dev.setCurrentIndex(i)
                    break

        lb_lang = self.config.get("loopback_language", default="auto")
        for i in range(self._cb_loopback_lang.count()):
            if self._cb_loopback_lang.itemData(i) == lb_lang:
                self._cb_loopback_lang.setCurrentIndex(i)
                break

        self._chk_lb_translate.setChecked(bool(self.config.get("loopback_translate_enabled", default=True)))
        lb_targets = self.config.get("loopback_translate_to", default=["ru"])
        for i in range(self._lw_lb_translate.count()):
            item = self._lw_lb_translate.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in lb_targets:
                item.setSelected(True)

        # Azure
        self._le_speech_key.setText(self.config.get("azure", "speech_key", default=""))
        self._le_speech_region.setText(self.config.get("azure", "speech_region", default="westeurope"))
        self._le_tr_key.setText(self.config.get("azure", "translator_key", default=""))
        self._le_tr_region.setText(self.config.get("azure", "translator_region", default="westeurope"))

        # AI
        ai = self.config.get("ai_assistant") or {}
        self._chk_ai.setChecked(bool(ai.get("enabled", False)))
        backend_ai = ai.get("backend", "ollama")
        self._rb_ollama.setChecked(backend_ai == "ollama")
        self._rb_openai.setChecked(backend_ai != "ollama")
        self._le_ai_endpoint.setText(ai.get("endpoint", "http://localhost:11434"))
        self._le_ai_model.setText(ai.get("model", "llama3.2:3b"))
        self._le_ai_key.setText(ai.get("api_key", ""))

        # Hotkey
        current_key = self.config.get("hotkey", default="f9")
        self._hotkey_btn.setText(current_key.upper())
        self._new_hotkey = current_key

        # Logs
        log_cfg = self.config.get("logging") or {}
        self._chk_log.setChecked(bool(log_cfg.get("enabled", True)))
        self._le_log_dir.setText(log_cfg.get("log_dir", ""))

    def _save(self):
        backend = "local" if self._cb_backend.currentIndex() == 0 else "azure"
        self.config["backend"] = backend
        self.config["model"] = self._cb_model.currentText()
        self.config["device"] = self._cb_device.currentText()
        self.config["language"] = self._cb_language.currentData() or "auto"
        self.config["recording_mode"] = "ptt" if self._rb_ptt.isChecked() else "toggle"
        self.config["auto_inject"] = self._chk_inject.isChecked()
        self.config.set("window", "opacity", self._sld_opacity.value() / 100.0)

        # Sources - mic
        self.config.set("audio", "device_index", self._cb_mic.currentData())
        self.config["translate_enabled"] = self._chk_translate.isChecked()
        targets = [
            self._lw_translate.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._lw_translate.count())
            if self._lw_translate.item(i).isSelected()
        ]
        self.config["translate_to"] = targets

        # Sources - loopback
        self.config["loopback_enabled"] = self._chk_loopback.isChecked()
        self.config["loopback_device"] = self._cb_loopback_dev.currentData()
        self.config["loopback_language"] = self._cb_loopback_lang.currentData() or "auto"
        self.config["loopback_translate_enabled"] = self._chk_lb_translate.isChecked()
        lb_targets = [
            self._lw_lb_translate.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._lw_lb_translate.count())
            if self._lw_lb_translate.item(i).isSelected()
        ]
        self.config["loopback_translate_to"] = lb_targets

        # Azure
        self.config.set("azure", "speech_key", self._le_speech_key.text().strip())
        self.config.set("azure", "speech_region", self._le_speech_region.text().strip())
        self.config.set("azure", "translator_key", self._le_tr_key.text().strip())
        self.config.set("azure", "translator_region", self._le_tr_region.text().strip())

        # AI
        self.config.set("ai_assistant", "enabled", self._chk_ai.isChecked())
        self.config.set("ai_assistant", "backend", "ollama" if self._rb_ollama.isChecked() else "openai")
        self.config.set("ai_assistant", "endpoint", self._le_ai_endpoint.text().strip())
        self.config.set("ai_assistant", "model", self._le_ai_model.text().strip())
        self.config.set("ai_assistant", "api_key", self._le_ai_key.text().strip())

        # Hotkey
        if self._new_hotkey:
            self.config["hotkey"] = self._new_hotkey

        # Logs
        self.config.set("logging", "enabled", self._chk_log.isChecked())
        self.config.set("logging", "log_dir", self._le_log_dir.text().strip())

        self.config.save()
        self.saved.emit()
        self.accept()

    # ── AI test ───────────────────────────────────────────────────────────────

    def _test_ai(self):
        self._ai_test_lbl.setText("Проверяю...")
        self._ai_test_lbl.setStyleSheet("color: rgba(180,170,100,0.80); font-size: 11px;")
        from core.ai_assistant import AIAssistant
        backend = "ollama" if self._rb_ollama.isChecked() else "openai"
        ai = AIAssistant(
            backend=backend,
            endpoint=self._le_ai_endpoint.text().strip(),
            model=self._le_ai_model.text().strip(),
            api_key=self._le_ai_key.text().strip(),
            enabled=True,
        )
        QTimer.singleShot(0, lambda: self._do_ai_test(ai))

    def _do_ai_test(self, ai):
        try:
            ok = ai.is_available()
            if ok:
                self._ai_test_lbl.setText("✓ Соединение OK")
                self._ai_test_lbl.setStyleSheet("color: rgba(80,200,160,0.90); font-size: 11px;")
            else:
                self._ai_test_lbl.setText("✗ Недоступно")
                self._ai_test_lbl.setStyleSheet("color: rgba(220,80,80,0.90); font-size: 11px;")
        except Exception as e:
            self._ai_test_lbl.setText(f"✗ {e}")
            self._ai_test_lbl.setStyleSheet("color: rgba(220,80,80,0.90); font-size: 11px;")

    # ── Logs ──────────────────────────────────────────────────────────────────

    def _open_log_dir(self):
        from pathlib import Path
        log_dir = self._le_log_dir.text().strip()
        if not log_dir:
            log_dir = str(Path(__file__).parent.parent / "logs")
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(log_dir)
        except Exception:
            subprocess.Popen(["explorer", log_dir])

    # ── Hotkey capture ────────────────────────────────────────────────────────

    def _start_listening_hotkey(self):
        self._listening_hotkey = True
        self._held_mods = set()
        self._hotkey_btn.setText("Нажми клавишу...")
        self._hotkey_btn.setProperty("listening", "true")
        self._hotkey_btn.style().unpolish(self._hotkey_btn)
        self._hotkey_btn.style().polish(self._hotkey_btn)
        self.grabKeyboard()

    def _finish_hotkey(self, key_str: str):
        self._listening_hotkey = False
        self._held_mods = set()
        self._new_hotkey = key_str
        self._hotkey_btn.setText(key_str.upper())
        self._hotkey_btn.setProperty("listening", "false")
        self._hotkey_btn.style().unpolish(self._hotkey_btn)
        self._hotkey_btn.style().polish(self._hotkey_btn)
        self.releaseKeyboard()

    def keyPressEvent(self, event):
        if not self._listening_hotkey:
            super().keyPressEvent(event)
            return

        from PyQt6.QtCore import Qt as _Qt
        key = event.key()

        if key == _Qt.Key.Key_Escape:
            self._finish_hotkey(self._new_hotkey or "f9")
            return

        # Detect modifier keys
        mod_map = {
            _Qt.Key.Key_Control: "ctrl",
            _Qt.Key.Key_Shift: "shift",
            _Qt.Key.Key_Alt: "alt",
            _Qt.Key.Key_Meta: "cmd",
        }
        if key in mod_map:
            self._held_mods.add(mod_map[key])
            # Show partial combo
            parts = sorted(self._held_mods) + ["?"]
            self._hotkey_btn.setText("+".join(parts).upper())
            return

        # Main key pressed
        special = {
            _Qt.Key.Key_F1: "f1", _Qt.Key.Key_F2: "f2", _Qt.Key.Key_F3: "f3",
            _Qt.Key.Key_F4: "f4", _Qt.Key.Key_F5: "f5", _Qt.Key.Key_F6: "f6",
            _Qt.Key.Key_F7: "f7", _Qt.Key.Key_F8: "f8", _Qt.Key.Key_F9: "f9",
            _Qt.Key.Key_F10: "f10", _Qt.Key.Key_F11: "f11", _Qt.Key.Key_F12: "f12",
            _Qt.Key.Key_Insert: "insert", _Qt.Key.Key_Home: "home",
            _Qt.Key.Key_End: "end", _Qt.Key.Key_PageUp: "page_up",
            _Qt.Key.Key_PageDown: "page_down", _Qt.Key.Key_Space: "space",
            _Qt.Key.Key_Tab: "tab", _Qt.Key.Key_Return: "enter",
        }
        key_text = special.get(key, "")
        if not key_text:
            key_text = event.text().lower().strip()
        if not key_text:
            return

        parts = sorted(self._held_mods) + [key_text]
        combo = "+".join(parts)
        self._finish_hotkey(combo)

    def keyReleaseEvent(self, event):
        if not self._listening_hotkey:
            super().keyReleaseEvent(event)
            return
        from PyQt6.QtCore import Qt as _Qt
        mod_map = {
            _Qt.Key.Key_Control: "ctrl",
            _Qt.Key.Key_Shift: "shift",
            _Qt.Key.Key_Alt: "alt",
            _Qt.Key.Key_Meta: "cmd",
        }
        key = event.key()
        if key in mod_map:
            self._held_mods.discard(mod_map[key])
