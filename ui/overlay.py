import threading
import time
import numpy as np
import win32con
import win32gui
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSizeGrip,
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QTimer, QPoint, pyqtProperty,
)
from PyQt6.QtGui import QPainter, QColor, QPen

from ui.styles import OVERLAY_STYLE
from utils.config import Config
from utils.hotkey import HotkeyManager
from utils import injector as inj


class TranscribeWorker(QThread):
    result = pyqtSignal(str)
    translations = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, audio: np.ndarray, config: Config, local_model=None):
        super().__init__()
        self.audio = audio
        self.config = config
        self.local_model = local_model

    def run(self):
        try:
            text = self._transcribe()
            if not text:
                return
            self.result.emit(text)
            if self.config.get("translate_enabled"):
                self._translate(text)
        except Exception as e:
            self.error.emit(str(e))

    def _transcribe(self) -> str:
        backend = self.config.get("backend", default="local")
        if backend == "azure":
            from core.transcriber_azure import AzureTranscriber
            t = AzureTranscriber(
                key=self.config.get("azure", "speech_key", default=""),
                region=self.config.get("azure", "speech_region", default="westeurope"),
                language=self.config.get("language", default="ru"),
            )
            return t.transcribe(self.audio)
        else:
            if self.local_model is None:
                from core.transcriber_local import LocalTranscriber
                self.local_model = LocalTranscriber(
                    model_name=self.config.get("model", default="small"),
                    device=self.config.get("device", default="cuda"),
                    language=self.config.get("language", default="ru"),
                )
            if not self.local_model.is_loaded():
                self.local_model.load()
            return self.local_model.transcribe(self.audio)

    def _translate(self, text: str):
        from core.translator import AzureTranslator
        target = self.config.get("translate_to", default=["en", "de"])
        translator = AzureTranslator(
            key=self.config.get("azure", "translator_key", default=""),
            region=self.config.get("azure", "translator_region", default="westeurope"),
        )
        result = translator.translate(
            text, target, source_lang=self.config.get("language", default="ru")
        )
        if result:
            self.translations.emit(result)


class LiveTranscribeWorker(QThread):
    """Transcribes the last N seconds of audio while recording — no translation."""
    result = pyqtSignal(str)

    _WINDOW_SECS = 8  # only look at the last 8 seconds

    def __init__(self, audio: np.ndarray, config: Config, local_model=None):
        super().__init__()
        max_samples = 16000 * self._WINDOW_SECS
        self.audio = audio[-max_samples:] if len(audio) > max_samples else audio
        self.config = config
        self.local_model = local_model

    def run(self):
        try:
            if self.local_model is None or not self.local_model.is_loaded():
                return
            if len(self.audio) < 6400:  # < 0.4s — skip
                return
            text = self.local_model.transcribe(self.audio)
            if text:
                self.result.emit(text)
        except Exception:
            pass


class ModelLoader(QThread):
    status = pyqtSignal(str)
    done = pyqtSignal(object)

    def __init__(self, config: Config):
        super().__init__()
        self.config = config

    def run(self):
        if self.config.get("backend", default="local") != "local":
            self.done.emit(None)
            return
        try:
            from core.transcriber_local import LocalTranscriber
            self.status.emit("Загрузка модели...")
            model = LocalTranscriber(
                model_name=self.config.get("model", default="small"),
                device=self.config.get("device", default="cuda"),
                language=self.config.get("language", default="ru"),
            )
            model.load()
            self.status.emit("Готово")
            self.done.emit(model)
        except Exception as e:
            self.status.emit(f"Ошибка: {e}")
            self.done.emit(None)


class MicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("🎙", parent)
        self.setObjectName("MicBtn")
        self._glow_val = 0.0

        self._anim = QPropertyAnimation(self, b"glow_val")
        self._anim.setDuration(900)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.SineCurve)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)

    @pyqtProperty(float)
    def glow_val(self) -> float:
        return self._glow_val

    @glow_val.setter
    def glow_val(self, v: float):
        self._glow_val = v
        self.update()

    def start_glow(self):
        self._anim.start()

    def stop_glow(self):
        self._anim.stop()
        self._glow_val = 0.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._glow_val > 0.01:
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            r = self.rect()
            center = r.center()
            radius = min(r.width(), r.height()) / 2
            color = QColor(255, 60, 80, int(80 * self._glow_val))
            p.setPen(QPen(color, 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(center, int(radius + 5), int(radius + 5))
            p.end()


class OverlayWindow(QWidget):
    # Signals emitted from pynput thread → handled on main Qt thread
    _sig_hotkey_press = pyqtSignal()
    _sig_hotkey_release = pyqtSignal()

    def __init__(self, config: Config, hotkey_manager: HotkeyManager):
        super().__init__()
        self.config = config
        self.hotkeys = hotkey_manager
        self._local_model = None
        self._audio_capture = None
        self._recording = False
        self._worker = None
        self._drag_pos: QPoint | None = None
        self._press_time: float = 0.0
        self._transcript_expanded = config.get("transcript_visible", default=True)

        # Wire hotkey signals — always delivered on main thread via Qt event loop
        self._sig_hotkey_press.connect(self._hotkey_press_main)
        self._sig_hotkey_release.connect(self._hotkey_release_main)

        self._tracked_hwnd: int = 0   # last non-overlay, non-tool foreground window
        self._pinned_hwnd: int = 0    # manually pinned target (0 = use tracked)
        self._live_worker = None

        self._setup_window()
        self._build_ui()
        self._setup_hotkey()
        self._start_fg_tracker()
        self._load_model()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("OverlayRoot")
        self.setStyleSheet(OVERLAY_STYLE)
        x = self.config.get("window", "x", default=100)
        y = self.config.get("window", "y", default=100)
        self.move(x, y)
        self.setWindowOpacity(self.config.get("window", "opacity", default=0.94))
        self.setMinimumSize(220, 60)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("Card")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 8, 10, 10)
        card_layout.setSpacing(0)

        # toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        toolbar.setContentsMargins(0, 0, 0, 0)

        self._mic_btn = MicButton()
        self._mic_btn.pressed.connect(self._on_mic_pressed)
        self._mic_btn.released.connect(self._on_mic_released)
        toolbar.addWidget(self._mic_btn)

        self._status_lbl = QLabel("Готово")
        self._status_lbl.setObjectName("StatusLbl")
        toolbar.addWidget(self._status_lbl, stretch=1)

        self._expand_btn = QPushButton("▾" if self._transcript_expanded else "▸")
        self._expand_btn.setObjectName("IconBtn")
        self._expand_btn.setToolTip("Показать/скрыть транскрипцию")
        self._expand_btn.clicked.connect(self._toggle_transcript)
        toolbar.addWidget(self._expand_btn)

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setObjectName("IconBtn")
        self._pin_btn.setToolTip("Зафиксировать окно для вставки (авто)")
        self._pin_btn.clicked.connect(self._toggle_pin)
        toolbar.addWidget(self._pin_btn)

        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("IconBtn")
        settings_btn.setToolTip("Настройки")
        settings_btn.clicked.connect(self._open_settings)
        toolbar.addWidget(settings_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("IconBtn")
        close_btn.setToolTip("Закрыть")
        close_btn.clicked.connect(self.close)
        toolbar.addWidget(close_btn)

        card_layout.addLayout(toolbar)

        self._divider = QFrame()
        self._divider.setObjectName("Divider")
        card_layout.addWidget(self._divider)
        self._divider.setVisible(self._transcript_expanded)

        self._transcript = QTextEdit()
        self._transcript.setObjectName("Transcript")
        self._transcript.setReadOnly(True)
        self._transcript.setPlaceholderText("Транскрипция появится здесь...")
        self._transcript.setMinimumHeight(120)
        self._transcript.setMaximumHeight(280)
        self._transcript.setVisible(self._transcript_expanded)
        card_layout.addWidget(self._transcript)

        # Live transcription label (shown while recording, hidden otherwise)
        self._live_lbl = QLabel("")
        self._live_lbl.setObjectName("LiveLbl")
        self._live_lbl.setWordWrap(True)
        self._live_lbl.setVisible(False)
        card_layout.addWidget(self._live_lbl)

        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 2, 0, 0)
        grip_row.addStretch()
        grip = QSizeGrip(self._card)
        grip.setFixedSize(14, 14)
        grip_row.addWidget(grip)
        card_layout.addLayout(grip_row)

        root.addWidget(self._card)
        self.resize(self.config.get("window", "width", default=340), 70)

    def _load_model(self):
        self._set_status("Загрузка модели...")
        self._loader = ModelLoader(self.config)
        self._loader.status.connect(self._set_status)
        self._loader.done.connect(self._on_model_loaded)
        self._loader.start()

    def _on_model_loaded(self, model):
        self._local_model = model
        self._set_status("Готово")

    def _setup_hotkey(self):
        key = self.config.get("hotkey", default="f9")
        # Callbacks here run on pynput thread — only emit signals, never touch UI
        self.hotkeys.register(
            key,
            on_press=lambda: self._sig_hotkey_press.emit(),
            on_release=lambda: self._sig_hotkey_release.emit(),
        )
        self.hotkeys.start()

    # ── Foreground window tracker (polls every 150ms) ─────────────────────────

    def _start_fg_tracker(self):
        self._fg_timer = QTimer(self)
        self._fg_timer.setInterval(150)
        self._fg_timer.timeout.connect(self._poll_foreground)
        self._fg_timer.start()

    def _poll_foreground(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or hwnd == int(self.winId()):
                return
            # Skip tool windows: Discord overlays, subtitle windows, system popups
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex & win32con.WS_EX_TOOLWINDOW:
                return
            # Must be visible and have non-empty title or be a proper app window
            if not win32gui.IsWindowVisible(hwnd):
                return
            self._tracked_hwnd = hwnd
        except Exception:
            pass

    @property
    def _inject_hwnd(self) -> int:
        return self._pinned_hwnd if self._pinned_hwnd else self._tracked_hwnd

    def _toggle_pin(self):
        if self._pinned_hwnd:
            self._pinned_hwnd = 0
        else:
            self._pinned_hwnd = self._inject_hwnd
        self._update_pin_btn()

    def _update_pin_btn(self):
        if self._pinned_hwnd:
            try:
                title = win32gui.GetWindowText(self._pinned_hwnd)
                short = title[:22] + "…" if len(title) > 22 else title
            except Exception:
                short = "?"
            self._pin_btn.setToolTip(f"Зафиксировано: {short}\nНажми чтобы открепить")
            self._pin_btn.setStyleSheet("color: #ffcc44;")
        else:
            self._pin_btn.setToolTip("Зафиксировать окно для вставки\n(сейчас: авто-трекинг)")
            self._pin_btn.setStyleSheet("")

    # ── Recording ─────────────────────────────────────────────────────────────

    def _start_recording(self):
        if self._recording:
            return
        from core.audio import AudioCapture
        device = self.config.get("audio", "device_index")
        self._audio_capture = AudioCapture(device_index=device)
        self._audio_capture.start()
        self._recording = True
        self._last_injected_text = ""  # tracks what was already injected live
        self._set_mic_state("recording")
        self._mic_btn.start_glow()
        self._set_status("Запись...")
        self._start_live_timer()

    def _stop_and_transcribe(self):
        if not self._recording:
            return
        if self._worker and self._worker.isRunning():
            return
        self._stop_live_timer()
        self._recording = False
        audio = self._audio_capture.stop()
        self._audio_capture = None
        self._mic_btn.stop_glow()
        self._set_mic_state("processing")
        self._set_status("Обработка...")
        self._live_lbl.setVisible(False)
        self._worker = TranscribeWorker(audio, self.config, self._local_model)
        self._worker.result.connect(self._on_text)
        self._worker.translations.connect(self._on_translations)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ── Live transcription timer ──────────────────────────────────────────────

    def _start_live_timer(self):
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(400)
        self._live_timer.timeout.connect(self._do_live_transcription)
        self._live_timer.start()

    def _stop_live_timer(self):
        if hasattr(self, "_live_timer") and self._live_timer.isActive():
            self._live_timer.stop()

    def _do_live_transcription(self):
        if not self._recording or self._audio_capture is None:
            return
        if self._live_worker and self._live_worker.isRunning():
            return  # previous live pass still running
        audio = self._audio_capture.peek()
        if len(audio) < 6400:
            return
        if self.config.get("backend", default="local") != "local":
            return  # live mode only for local backend
        self._live_worker = LiveTranscribeWorker(audio, self.config, self._local_model)
        self._live_worker.result.connect(self._on_live_text)
        self._live_worker.start()

    def _on_live_text(self, text: str):
        if not self._recording:
            return
        self._live_lbl.setText(f"◉ {text}")
        self._live_lbl.setVisible(True)
        if not self._transcript_expanded:
            self._transcript_expanded = True
            self._expand_transcript(True)
        # Inject only new words (diff from what was already sent to active window)
        translate_on = self.config.get("translate_enabled")
        if self.config.get("auto_inject") and not translate_on:
            new_words = self._diff_new_words(self._last_injected_text, text)
            if new_words:
                self._last_injected_text = text
                hwnd = self._inject_hwnd
                threading.Thread(
                    target=inj.inject_text, args=(new_words, hwnd), daemon=True
                ).start()

    def _on_worker_done(self):
        self._set_mic_state("")
        self._set_status("Готово")

    def _set_mic_state(self, state: str):
        self._mic_btn.setProperty("state", state)
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)

    def _is_ptt(self) -> bool:
        return self.config.get("recording_mode", default="toggle") == "ptt"

    # ── Mic button ────────────────────────────────────────────────────────────

    def _on_mic_pressed(self):
        self._press_time = time.monotonic()
        if self._is_ptt():
            # PTT: press → start, release → stop
            if not self._recording:
                self._start_recording()
        else:
            # Toggle: each press flips state
            if self._recording:
                self._stop_and_transcribe()
            else:
                self._start_recording()

    def _on_mic_released(self):
        if self._is_ptt() and self._recording:
            self._stop_and_transcribe()

    # ── Hotkey: emits signal from pynput thread → handled here on main thread ─

    def _hotkey_press_main(self):
        if self._is_ptt():
            if not self._recording:
                self._start_recording()
        else:
            if self._recording:
                self._stop_and_transcribe()
            else:
                self._start_recording()

    def _hotkey_release_main(self):
        if self._is_ptt() and self._recording:
            self._stop_and_transcribe()

    # ── Text output ───────────────────────────────────────────────────────────

    def _on_text(self, text: str):
        lang = self.config.get("language", default="ru")
        flag = {"ru": "🇷🇺", "en": "🇬🇧", "de": "🇩🇪", "uk": "🇺🇦"}.get(lang, "")
        self._append_html(f"<span style='color:#7878cc'>{flag} Оригинал:</span> {text}")
        self._live_lbl.setVisible(False)
        translate_on = self.config.get("translate_enabled")
        if self.config.get("auto_inject") and not translate_on:
            # Inject only what wasn't injected live yet (remaining tail)
            remaining = self._diff_new_words(self._last_injected_text, text)
            if remaining:
                hwnd = self._inject_hwnd
                threading.Thread(
                    target=inj.inject_text, args=(remaining, hwnd), daemon=True
                ).start()

    def _on_translations(self, trans: dict):
        style = {"en": ("🇬🇧", "#4ec9a0"), "de": ("🇩🇪", "#7dc8e8")}
        inject_lang = self.config.get("translate_to", default=["en", "de"])
        first_lang = inject_lang[0] if inject_lang else None
        for lang, translated in trans.items():
            flag, color = style.get(lang, ("", "#aaaacc"))
            self._append_html(
                f"<span style='color:{color}'>{flag} {lang.upper()}:</span> {translated}"
            )
            # Inject only first target language into active window
            if self.config.get("auto_inject") and lang == first_lang:
                hwnd = self._inject_hwnd
                threading.Thread(
                    target=inj.inject_text, args=(translated, hwnd), daemon=True
                ).start()

    def _on_error(self, msg: str):
        self._append_html(f"<span style='color:#e05050'>⚠ {msg}</span>")
        self._set_status("Ошибка")

    def _append_html(self, html: str):
        self._transcript.append(html)
        sb = self._transcript.verticalScrollBar()
        sb.setValue(sb.maximum())
        if not self._transcript_expanded:
            self._transcript_expanded = True
            self._expand_transcript(True)

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    def _toggle_transcript(self):
        self._transcript_expanded = not self._transcript_expanded
        self._expand_transcript(self._transcript_expanded)

    def _expand_transcript(self, visible: bool):
        self._transcript.setVisible(visible)
        self._divider.setVisible(visible)
        self._expand_btn.setText("▾" if visible else "▸")
        self.adjustSize()
        self.config.set("transcript_visible", visible)

    def _open_settings(self):
        from ui.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self.config, self.hotkeys, parent=self)
        dlg.saved.connect(self._on_settings_saved)
        dlg.exec()

    def _on_settings_saved(self):
        self.setWindowOpacity(self.config.get("window", "opacity", default=0.94))
        self._local_model = None
        self._load_model()
        # Restart hotkey listener with the (possibly new) key from config
        self.hotkeys.stop()
        self.hotkeys._callbacks.clear()
        self.hotkeys._held.clear()
        self._setup_hotkey()

    @staticmethod
    def _diff_new_words(old: str, new: str) -> str:
        """Return words in `new` that extend `old` (common-prefix diff).
        Returns empty string if new is shorter or a correction with no clear extension."""
        if not old:
            return new.strip()
        strip_punct = lambda w: w.lower().strip(".,!?;:\"'—–-")
        old_words = old.split()
        new_words = new.split()
        if len(new_words) <= len(old_words):
            return ""
        # Verify new starts with the same words as old
        for i, ow in enumerate(old_words):
            if i >= len(new_words):
                return ""
            if strip_punct(ow) != strip_punct(new_words[i]):
                return ""
        return " ".join(new_words[len(old_words):])

    # ── Drag to move ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            new_pos = event.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            self.config.set("window", "x", new_pos.x())
            self.config.set("window", "y", new_pos.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        self.config.set("window", "width", self.width())
        self.config.set("window", "height", self.height())
        super().resizeEvent(event)

    def closeEvent(self, event):
        self.hotkeys.stop()
        self.config.save()
        super().closeEvent(event)
