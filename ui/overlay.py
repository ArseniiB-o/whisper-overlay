import threading
import time
import numpy as np
import win32con
import win32gui
from PyQt6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QSizeGrip,
    QScrollArea,
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


# ── Workers ───────────────────────────────────────────────────────────────────

class TranscribeWorker(QThread):
    result = pyqtSignal(str, str)       # (text, detected_lang)
    translations = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, audio: np.ndarray, config: Config, local_model=None, channel: str = "self"):
        super().__init__()
        self.audio = audio
        self.config = config
        self.local_model = local_model
        self.channel = channel

    def run(self):
        try:
            text, lang = self._transcribe()
            if not text:
                return
            self.result.emit(text, lang)
            if self.channel == "self" and self.config.get("translate_enabled"):
                self._do_translate(text, lang, self.config.get("translate_to", default=[]))
            elif self.channel == "other" and self.config.get("loopback_translate_enabled"):
                self._do_translate(text, lang, self.config.get("loopback_translate_to", default=["ru"]))
        except Exception as e:
            self.error.emit(str(e))

    def _transcribe(self):
        backend = self.config.get("backend", default="local")
        lang_key = "loopback_language" if self.channel == "other" else "language"
        lang = self.config.get(lang_key, default="auto")
        if backend == "azure":
            from core.transcriber_azure import AzureTranscriber
            t = AzureTranscriber(
                key=self.config.get("azure", "speech_key", default=""),
                region=self.config.get("azure", "speech_region", default="westeurope"),
                language=lang if lang != "auto" else "ru",
            )
            return t.transcribe(self.audio), lang
        else:
            if self.local_model is None:
                from core.transcriber_local import LocalTranscriber
                self.local_model = LocalTranscriber(
                    model_name=self.config.get("model", default="small"),
                    device=self.config.get("device", default="cuda"),
                    language=lang,
                )
            if not self.local_model.is_loaded():
                self.local_model.load()
            return self.local_model.transcribe(self.audio)

    def _do_translate(self, text: str, source_lang: str, targets: list):
        if not targets:
            return
        from core.translator import AzureTranslator
        translator = AzureTranslator(
            key=self.config.get("azure", "translator_key", default=""),
            region=self.config.get("azure", "translator_region", default="westeurope"),
        )
        src = source_lang if source_lang not in ("auto", "") else "ru"
        result = translator.translate(text, targets, source_lang=src)
        if result:
            self.translations.emit(result)


class LiveTranscribeWorker(QThread):
    result = pyqtSignal(str)
    _WINDOW_SECS = 8

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
            if len(self.audio) < 6400:
                return
            text, _ = self.local_model.transcribe(self.audio)
            if text:
                self.result.emit(text)
        except Exception:
            pass


class LoopbackTranscribeWorker(QThread):
    result = pyqtSignal(str, str)   # (text, detected_lang)
    _WINDOW_SECS = 6

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
            if len(self.audio) < 8000:
                return
            text, lang = self.local_model.transcribe(self.audio)
            if text:
                self.result.emit(text, lang)
        except Exception:
            pass


class AISuggestionsWorker(QThread):
    result = pyqtSignal(list)

    def __init__(self, transcript: str, language: str, config: Config):
        super().__init__()
        self.transcript = transcript
        self.language = language
        self.config = config

    def run(self):
        try:
            from core.ai_assistant import AIAssistant
            ai_cfg = self.config.get("ai_assistant") or {}
            ai = AIAssistant(
                backend=ai_cfg.get("backend", "ollama"),
                endpoint=ai_cfg.get("endpoint", "http://localhost:11434"),
                model=ai_cfg.get("model", "llama3.2:3b"),
                api_key=ai_cfg.get("api_key", ""),
                enabled=True,
            )
            suggestions = ai.get_suggestions(self.transcript, self.language, n=3)
            self.result.emit(suggestions)
        except Exception as e:
            print(f"[ai_suggestions] {e}")
            self.result.emit([])


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
                language=self.config.get("language", default="auto"),
            )
            model.load()
            self.status.emit("Готово")
            self.done.emit(model)
        except Exception as e:
            self.status.emit(f"Ошибка: {e}")
            self.done.emit(None)


# ── Mic button with animated glow ────────────────────────────────────────────

class MicButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("🎙", parent)
        self.setObjectName("MicBtn")
        self._glow_val = 0.0
        self._anim = QPropertyAnimation(self, b"glow_val")
        self._anim.setDuration(800)
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
            color = QColor(255, 55, 85, int(90 * self._glow_val))
            p.setPen(QPen(color, 3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(center, int(radius + 6), int(radius + 6))
            p.end()


# ── Main overlay window ───────────────────────────────────────────────────────

class OverlayWindow(QWidget):
    _sig_hotkey_press = pyqtSignal()
    _sig_hotkey_release = pyqtSignal()
    _sig_loopback_translations = pyqtSignal(dict)  # thread-safe bridge for loopback translate results

    def __init__(self, config: Config, hotkey_manager: HotkeyManager):
        super().__init__()
        self.config = config
        self.hotkeys = hotkey_manager
        self._local_model = None
        self._audio_capture = None
        self._recording = False
        self._worker = None
        self._drag_pos: QPoint | None = None
        self._transcript_expanded = config.get("transcript_visible", default=True)
        self._last_injected_text = ""
        self._live_worker = None
        self._loopback_worker = None
        self._loopback_capture = None
        self._loopback_prev_text = ""
        self._ai_worker = None
        self._loopback_timer = None
        self._tracked_hwnd: int = 0
        self._pinned_hwnd: int = 0

        self._logger = self._init_logger()

        self._sig_hotkey_press.connect(self._hotkey_press_main)
        self._sig_hotkey_release.connect(self._hotkey_release_main)
        self._sig_loopback_translations.connect(self._on_loopback_translations)

        self._setup_window()
        self._build_ui()
        self._setup_hotkey()
        self._start_fg_tracker()
        self._load_model()
        self._start_loopback_if_enabled()

    # ── Init ──────────────────────────────────────────────────────────────────

    def _init_logger(self):
        from utils.logger import SessionLogger
        log_cfg = self.config.get("logging") or {}
        return SessionLogger(
            log_dir=log_cfg.get("log_dir") or None,
            enabled=bool(log_cfg.get("enabled", True)),
        )

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
        self.setWindowOpacity(self.config.get("window", "opacity", default=0.95))
        self.setMinimumSize(240, 60)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._card = QFrame()
        self._card.setObjectName("Card")
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(5)
        toolbar.setContentsMargins(0, 0, 0, 4)

        self._mic_btn = MicButton()
        self._mic_btn.pressed.connect(self._on_mic_pressed)
        self._mic_btn.released.connect(self._on_mic_released)
        toolbar.addWidget(self._mic_btn)

        self._lb_btn = QPushButton("🔊")
        self._lb_btn.setObjectName("LoopbackBtn")
        self._lb_btn.setToolTip("Системный звук (Zoom / собеседник)\nКлик = вкл/выкл захват")
        self._lb_btn.setCheckable(True)
        self._lb_btn.clicked.connect(self._toggle_loopback)
        toolbar.addWidget(self._lb_btn)

        self._status_lbl = QLabel("Загрузка...")
        self._status_lbl.setObjectName("StatusLbl")
        toolbar.addWidget(self._status_lbl, stretch=1)

        self._target_lbl = QLabel("")
        self._target_lbl.setObjectName("TargetLbl")
        self._target_lbl.setProperty("active", "false")
        self._target_lbl.setToolTip("Целевое окно для вставки текста")
        toolbar.addWidget(self._target_lbl)

        self._mode_badge = QLabel("LOCAL")
        self._mode_badge.setObjectName("ModeBadge")
        toolbar.addWidget(self._mode_badge)

        self._expand_btn = QPushButton("▾" if self._transcript_expanded else "▸")
        self._expand_btn.setObjectName("IconBtn")
        self._expand_btn.setToolTip("Показать/скрыть транскрипцию")
        self._expand_btn.clicked.connect(self._toggle_transcript)
        toolbar.addWidget(self._expand_btn)

        self._pin_btn = QPushButton("📌")
        self._pin_btn.setObjectName("IconBtn")
        self._pin_btn.setToolTip("Закрепить окно для вставки текста")
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

        # ── Divider ───────────────────────────────────────────────────────────
        self._divider = QFrame()
        self._divider.setObjectName("Divider")
        card_layout.addWidget(self._divider)
        self._divider.setVisible(self._transcript_expanded)

        # ── Transcript ────────────────────────────────────────────────────────
        self._transcript = QTextEdit()
        self._transcript.setObjectName("Transcript")
        self._transcript.setReadOnly(True)
        self._transcript.setPlaceholderText(
            "Транскрипция появится здесь...\n\n"
            "🎙 — записать свой голос\n"
            "🔊 — захватить системный звук (Zoom/Teams)"
        )
        self._transcript.setMinimumHeight(100)
        self._transcript.setVisible(self._transcript_expanded)
        card_layout.addWidget(self._transcript)

        # ── Live label (shown while recording) ───────────────────────────────
        self._live_lbl = QLabel("")
        self._live_lbl.setObjectName("LiveLbl")
        self._live_lbl.setWordWrap(True)
        self._live_lbl.setVisible(False)
        card_layout.addWidget(self._live_lbl)

        # ── AI suggestions pills ──────────────────────────────────────────────
        self._suggestions_scroll = QScrollArea()
        self._suggestions_scroll.setObjectName("SuggestionsScroll")
        self._suggestions_scroll.setFixedHeight(38)
        self._suggestions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._suggestions_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._suggestions_scroll.setWidgetResizable(True)
        self._suggestions_scroll.setVisible(False)

        self._suggestions_widget = QWidget()
        self._suggestions_widget.setObjectName("SuggestionsWidget")
        self._suggestions_layout = QHBoxLayout(self._suggestions_widget)
        self._suggestions_layout.setContentsMargins(4, 3, 4, 3)
        self._suggestions_layout.setSpacing(6)
        self._suggestions_layout.addStretch()
        self._suggestions_scroll.setWidget(self._suggestions_widget)
        card_layout.addWidget(self._suggestions_scroll)

        # ── Resize grip ───────────────────────────────────────────────────────
        grip_row = QHBoxLayout()
        grip_row.setContentsMargins(0, 2, 0, 0)
        grip_row.addStretch()
        grip = QSizeGrip(self._card)
        grip.setFixedSize(12, 12)
        grip_row.addWidget(grip)
        card_layout.addLayout(grip_row)

        root.addWidget(self._card)

        # Set initial states
        lb_enabled = self.config.get("loopback_enabled", default=False)
        self._lb_btn.setChecked(lb_enabled)
        self._lb_btn.setProperty("active", "true" if lb_enabled else "false")
        backend = self.config.get("backend", default="local")
        self._mode_badge.setText("AZURE" if backend == "azure" else "LOCAL")

        w = self.config.get("window", "width", default=420)
        self.resize(w, 200)

    # ── Model loading ─────────────────────────────────────────────────────────

    def _load_model(self):
        self._set_status("Загрузка модели...")
        self._loader = ModelLoader(self.config)
        self._loader.status.connect(self._set_status)
        self._loader.done.connect(self._on_model_loaded)
        self._loader.start()

    def _on_model_loaded(self, model):
        self._local_model = model
        self._set_status("Готово")

    # ── Hotkey ───────────────────────────────────────────────────────────────

    def _setup_hotkey(self):
        key = self.config.get("hotkey", default="f9")
        self.hotkeys.register(
            key,
            on_press=lambda: self._sig_hotkey_press.emit(),
            on_release=lambda: self._sig_hotkey_release.emit(),
        )
        self.hotkeys.start()

    # ── Foreground tracker ────────────────────────────────────────────────────

    def _start_fg_tracker(self):
        self._fg_timer = QTimer(self)
        self._fg_timer.setInterval(150)
        self._fg_timer.timeout.connect(self._poll_foreground)
        self._fg_timer.start()

    def _poll_foreground(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return
            # Skip our own overlay and all its children
            root = win32gui.GetAncestor(hwnd, 2)  # GA_ROOT=2 → top-level ancestor
            if root == int(self.winId()):
                return
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex & win32con.WS_EX_TOOLWINDOW:
                return
            if not win32gui.IsWindowVisible(hwnd):
                return
            self._tracked_hwnd = hwnd
            # Update target label
            try:
                title = win32gui.GetWindowText(hwnd)
                short = title[:18] + "…" if len(title) > 18 else title
                if short:
                    self._target_lbl.setText(f"→ {short}")
                    self._target_lbl.setProperty("active", "true")
                else:
                    self._target_lbl.setText("")
                    self._target_lbl.setProperty("active", "false")
                self._target_lbl.style().unpolish(self._target_lbl)
                self._target_lbl.style().polish(self._target_lbl)
            except Exception:
                pass
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
                short = title[:20] + "…" if len(title) > 20 else title
            except Exception:
                short = "?"
            self._pin_btn.setToolTip(f"Зафиксировано: {short}\nНажми чтобы открепить")
            self._pin_btn.setStyleSheet("color: #ffcc44;")
        else:
            self._pin_btn.setToolTip("Закрепить окно для вставки (авто-трекинг)")
            self._pin_btn.setStyleSheet("")

    # ── Loopback (system audio from Zoom etc.) ────────────────────────────────

    def _start_loopback_if_enabled(self):
        if self.config.get("loopback_enabled", default=False):
            self._start_loopback()

    def _start_loopback(self):
        if self._loopback_capture:
            return
        try:
            from core.audio_loopback import LoopbackCapture
            device_name = self.config.get("loopback_device")
            self._loopback_capture = LoopbackCapture(device_name=device_name)
            self._loopback_capture.start()
            self._loopback_timer = QTimer(self)
            self._loopback_timer.setInterval(1500)
            self._loopback_timer.timeout.connect(self._do_loopback_transcription)
            self._loopback_timer.start()
            self._set_lb_active(True)
        except Exception as e:
            self._set_status(f"Loopback: {e}")
            self._loopback_capture = None

    def _stop_loopback(self):
        if self._loopback_timer and self._loopback_timer.isActive():
            self._loopback_timer.stop()
        if self._loopback_capture:
            try:
                self._loopback_capture.stop()
            except Exception:
                pass
            self._loopback_capture = None
        self._loopback_prev_text = ""
        self._set_lb_active(False)

    def _toggle_loopback(self):
        enabled = not self.config.get("loopback_enabled", default=False)
        self.config.set("loopback_enabled", enabled)
        self.config.save()
        if enabled:
            self._start_loopback()
        else:
            self._stop_loopback()
        self._lb_btn.setChecked(enabled)
        self._set_lb_active(enabled)

    def _set_lb_active(self, active: bool):
        self._lb_btn.setProperty("active", "true" if active else "false")
        self._lb_btn.style().unpolish(self._lb_btn)
        self._lb_btn.style().polish(self._lb_btn)

    def _do_loopback_transcription(self):
        if self._loopback_capture is None:
            return
        if self._loopback_worker and self._loopback_worker.isRunning():
            return
        if self.config.get("backend", default="local") != "local":
            return
        audio = self._loopback_capture.peek()
        if len(audio) < 8000:
            return
        self._loopback_worker = LoopbackTranscribeWorker(audio, self.config, self._local_model)
        self._loopback_worker.result.connect(self._on_loopback_text)
        self._loopback_worker.start()

    def _on_loopback_text(self, text: str, lang: str):
        if not text:
            return
        if text == self._loopback_prev_text:
            return
        # Only show if there's actually new content (not just minor word-count change)
        prev_words = set(self._loopback_prev_text.lower().split())
        new_words = set(text.lower().split())
        new_content = new_words - prev_words
        if self._loopback_prev_text and len(new_content) < 2:
            return  # Less than 2 new words — not worth showing yet
        self._loopback_prev_text = text
        flag = self._lang_flag(lang)
        self._append_html(
            f"<div style='margin:3px 0 1px 0; padding:5px 8px 5px 10px; "
            f"border-left:2px solid rgba(20,200,170,0.75); "
            f"background:rgba(10,160,135,0.07); border-radius:0 6px 6px 0;'>"
            f"<span style='color:rgba(20,200,170,0.65); font-size:10px; "
            f"font-family:Segoe UI;'>{flag} Собеседник</span><br/>"
            f"<span style='color:#d8f4ef; font-size:13px;'>{text}</span>"
            f"</div>"
        )
        self._logger.log("other", text, language=lang)
        # Translate if configured
        if self.config.get("loopback_translate_enabled"):
            targets = self.config.get("loopback_translate_to", default=["ru"])
            key = self.config.get("azure", "translator_key", default="")
            if targets and key:
                src = lang if lang not in ("auto", "") else "en"
                def do_translate(t=text, s=src, tgt=targets):
                    from core.translator import AzureTranslator
                    tr = AzureTranslator(
                        key=self.config.get("azure", "translator_key", default=""),
                        region=self.config.get("azure", "translator_region", default="westeurope"),
                    )
                    result = tr.translate(t, tgt, source_lang=s)
                    if result:
                        # Emit signal — never call Qt widgets directly from a background thread
                        self._sig_loopback_translations.emit(result)
                threading.Thread(target=do_translate, daemon=True).start()
        self._maybe_get_ai_suggestions(text, lang)

    def _on_loopback_translations(self, trans: dict):
        for lang, translated in trans.items():
            flag = self._lang_flag(lang)
            self._append_html(
                f"<div style='margin:0 0 4px 12px; padding:3px 8px 3px 8px; "
                f"color:rgba(90,185,230,0.82); font-size:11.5px; font-style:italic;'>"
                f"↳ {flag} {translated}"
                f"</div>"
            )

    # ── Recording (my voice) ──────────────────────────────────────────────────

    def _start_recording(self):
        if self._recording:
            return
        from core.audio import AudioCapture
        device = self.config.get("audio", "device_index")
        self._audio_capture = AudioCapture(device_index=device)
        self._audio_capture.start()
        self._recording = True
        self._last_injected_text = ""
        self._set_mic_state("recording")
        self._mic_btn.start_glow()
        self._set_status("● Запись")
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
        self._worker = TranscribeWorker(audio, self.config, self._local_model, channel="self")
        self._worker.result.connect(self._on_text)
        self._worker.translations.connect(self._on_translations)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ── Live transcription ────────────────────────────────────────────────────

    def _start_live_timer(self):
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(350)
        self._live_timer.timeout.connect(self._do_live_transcription)
        self._live_timer.start()

    def _stop_live_timer(self):
        if hasattr(self, "_live_timer") and self._live_timer.isActive():
            self._live_timer.stop()

    def _do_live_transcription(self):
        if not self._recording or self._audio_capture is None:
            return
        if self._live_worker and self._live_worker.isRunning():
            return
        if self.config.get("backend", default="local") != "local":
            return
        audio = self._audio_capture.peek()
        if len(audio) < 6400:
            return
        self._live_worker = LiveTranscribeWorker(audio, self.config, self._local_model)
        self._live_worker.result.connect(self._on_live_text)
        self._live_worker.start()

    def _on_live_text(self, text: str):
        if not self._recording:
            return
        self._live_lbl.setText(f"◉  {text}")
        self._live_lbl.setVisible(True)
        if not self._transcript_expanded:
            self._transcript_expanded = True
            self._expand_transcript(True)
        # Word-by-word injection while still recording
        if self.config.get("auto_inject") and not self.config.get("translate_enabled"):
            new_words = self._diff_new_words(self._last_injected_text, text)
            if new_words:
                # Strip trailing whisper ellipsis before injecting (never type "..." into target)
                clean = new_words.rstrip()
                if clean.endswith("..."):
                    clean = clean[:-3].rstrip()
                elif clean.endswith("…"):
                    clean = clean[:-1].rstrip()
                if clean:
                    self._last_injected_text = text
                    hwnd = self._inject_hwnd
                    threading.Thread(
                        target=inj.inject_text, args=(clean + " ", hwnd), daemon=True
                    ).start()
                else:
                    # Only trailing ellipsis — update tracker but don't inject anything
                    self._last_injected_text = text
            elif self._last_injected_text:
                # Diff failed — check if text is completely different from what was injected.
                # This happens when whisper corrects a hallucination (e.g., "thank you" → real text).
                # If so, reset the tracker so we can inject fresh on the next tick.
                old_w = set(w.lower().strip(".,!?;:'\"") for w in self._last_injected_text.split())
                new_w = set(w.lower().strip(".,!?;:'\"") for w in text.split())
                if old_w and new_w:
                    overlap = len(old_w & new_w) / max(len(old_w), 1)
                    if overlap < 0.25:
                        self._last_injected_text = ""

    # ── Final transcription ───────────────────────────────────────────────────

    def _on_text(self, text: str, lang: str):
        flag = self._lang_flag(lang)
        self._append_html(
            f"<div style='margin:3px 0 1px 0; padding:5px 8px 5px 10px; "
            f"border-left:2px solid rgba(108,74,255,0.75); "
            f"background:rgba(80,55,200,0.07); border-radius:0 6px 6px 0;'>"
            f"<span style='color:rgba(130,100,255,0.65); font-size:10px; "
            f"font-family:Segoe UI;'>{flag} Я</span><br/>"
            f"<span style='color:#e8e2ff; font-size:13px;'>{text}</span>"
            f"</div>"
        )
        self._live_lbl.setVisible(False)
        if self.config.get("auto_inject") and not self.config.get("translate_enabled"):
            remaining = self._diff_new_words(self._last_injected_text, text)
            if remaining:
                # New words extend what was already injected live
                to_inject = remaining + " "
            elif not self._last_injected_text:
                # Nothing was injected during live phase → inject everything
                to_inject = text + " "
            else:
                # Diff failed: live injected something, but final text diverges.
                # If live injection was very short (≤2 words, likely a hallucination),
                # inject the full final text. Otherwise skip to avoid duplicates.
                to_inject = (text + " ") if len(self._last_injected_text.split()) <= 2 else ""
            if to_inject:
                hwnd = self._inject_hwnd
                threading.Thread(
                    target=inj.inject_text, args=(to_inject, hwnd), daemon=True
                ).start()
        self._logger.log("self", text, language=lang)
        self._maybe_get_ai_suggestions(text, lang)

    def _on_translations(self, trans: dict):
        inject_langs = self.config.get("translate_to", default=[])
        first_lang = inject_langs[0] if inject_langs else None
        for lang, translated in trans.items():
            flag = self._lang_flag(lang)
            self._append_html(
                f"<div style='margin:0 0 4px 12px; padding:3px 8px 3px 8px; "
                f"color:rgba(90,185,230,0.82); font-size:11.5px; font-style:italic;'>"
                f"↳ {flag} {translated}"
                f"</div>"
            )
            if self.config.get("auto_inject") and lang == first_lang:
                hwnd = self._inject_hwnd
                threading.Thread(
                    target=inj.inject_text, args=(translated + " ", hwnd), daemon=True
                ).start()

    def _on_error(self, msg: str):
        self._append_html(f"<span style='color:#e05060'>⚠ {msg}</span>")
        self._set_status("Ошибка")

    def _on_worker_done(self):
        self._set_mic_state("")
        self._set_status("Готово")

    # ── AI suggestions ────────────────────────────────────────────────────────

    def _maybe_get_ai_suggestions(self, text: str, lang: str):
        ai_cfg = self.config.get("ai_assistant") or {}
        if not ai_cfg.get("enabled", False):
            return
        if self._ai_worker and self._ai_worker.isRunning():
            return
        transcript = self._logger.get_recent_transcript(8) or text
        self._ai_worker = AISuggestionsWorker(transcript, lang, self.config)
        self._ai_worker.result.connect(self._on_ai_suggestions)
        self._ai_worker.start()

    def _on_ai_suggestions(self, suggestions: list):
        # Clear old pills (keep the trailing stretch)
        while self._suggestions_layout.count() > 1:
            item = self._suggestions_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        if not suggestions:
            self._suggestions_scroll.setVisible(False)
            return
        for s in suggestions:
            pill = QPushButton(s)
            pill.setObjectName("AIPill")
            pill.setFlat(True)
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            pill.clicked.connect(lambda checked, t=s: self._inject_suggestion(t))
            self._suggestions_layout.insertWidget(self._suggestions_layout.count() - 1, pill)
        self._suggestions_scroll.setVisible(True)
        if not self._transcript_expanded:
            self._transcript_expanded = True
            self._expand_transcript(True)

    def _inject_suggestion(self, text: str):
        hwnd = self._inject_hwnd
        threading.Thread(target=inj.inject_text, args=(text + " ", hwnd), daemon=True).start()

    # ── Hotkey handlers ───────────────────────────────────────────────────────

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

    # ── Mic button ────────────────────────────────────────────────────────────

    def _on_mic_pressed(self):
        if self._is_ptt():
            if not self._recording:
                self._start_recording()
                self._schedule_focus_restore()
        else:
            if self._recording:
                self._stop_and_transcribe()
            else:
                self._start_recording()
                self._schedule_focus_restore()

    def _schedule_focus_restore(self):
        """After clicking mic button (which steals focus), return focus to target window."""
        if self._inject_hwnd:
            hwnd = self._inject_hwnd
            def restore():
                time.sleep(0.15)
                try:
                    import win32gui as _wg
                    _wg.SetForegroundWindow(hwnd)
                except Exception:
                    pass
            threading.Thread(target=restore, daemon=True).start()

    def _on_mic_released(self):
        if self._is_ptt() and self._recording:
            self._stop_and_transcribe()

    def _is_ptt(self) -> bool:
        return self.config.get("recording_mode", default="toggle") == "ptt"

    # ── UI helpers ────────────────────────────────────────────────────────────

    def _append_html(self, html: str):
        self._transcript.append(html)
        sb = self._transcript.verticalScrollBar()
        sb.setValue(sb.maximum())
        if not self._transcript_expanded:
            self._transcript_expanded = True
            self._expand_transcript(True)

    def _set_status(self, text: str):
        self._status_lbl.setText(text)

    def _set_mic_state(self, state: str):
        self._mic_btn.setProperty("state", state)
        self._mic_btn.style().unpolish(self._mic_btn)
        self._mic_btn.style().polish(self._mic_btn)

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
        self.setWindowOpacity(self.config.get("window", "opacity", default=0.95))
        self._local_model = None
        self._load_model()
        self.hotkeys.stop()
        self.hotkeys.clear()
        self._setup_hotkey()
        self._logger = self._init_logger()
        # Update loopback state
        lb_enabled = self.config.get("loopback_enabled", default=False)
        if lb_enabled and not self._loopback_capture:
            self._start_loopback()
        elif not lb_enabled and self._loopback_capture:
            self._stop_loopback()
        self._lb_btn.setChecked(lb_enabled)
        self._set_lb_active(lb_enabled)
        backend = self.config.get("backend", default="local")
        self._mode_badge.setText("AZURE" if backend == "azure" else "LOCAL")

    @staticmethod
    def _lang_flag(lang: str) -> str:
        flags = {
            "ru": "🇷🇺", "en": "🇬🇧", "de": "🇩🇪", "uk": "🇺🇦",
            "fr": "🇫🇷", "es": "🇪🇸", "it": "🇮🇹", "pl": "🇵🇱",
            "zh": "🇨🇳", "ja": "🇯🇵",
        }
        return flags.get(lang, "🌐")

    @staticmethod
    def _diff_new_words(old: str, new: str) -> str:
        """Return words in `new` that extend `old` (prefix diff for live injection).

        Strips trailing ellipsis ('...', '…') from both sides before comparing,
        so whisper pause-artifacts never poison the diff state.
        """
        def clean(s: str) -> str:
            s = s.strip()
            while s.endswith("...") or s.endswith("…"):
                s = s[:-3 if s.endswith("...") else -1].rstrip()
            return s

        if not old:
            return clean(new)

        old_c = clean(old)
        new_c = clean(new)
        if not old_c:
            return new_c

        strip_p = lambda w: w.lower().strip(".,!?;:\"'—–-…")
        old_words = old_c.split()
        new_words = new_c.split()

        if len(new_words) <= len(old_words):
            return ""
        for i, ow in enumerate(old_words):
            if i >= len(new_words):
                return ""
            if strip_p(ow) != strip_p(new_words[i]):
                return ""
        return " ".join(new_words[len(old_words):])

    # ── Drag ──────────────────────────────────────────────────────────────────

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
        self._stop_live_timer()
        self._stop_loopback()
        self.hotkeys.stop()
        self.config.save()
        super().closeEvent(event)
