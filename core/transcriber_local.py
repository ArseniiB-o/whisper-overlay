import numpy as np
from typing import Optional


class LocalTranscriber:
    _instance: Optional["LocalTranscriber"] = None

    def __init__(self, model_name: str = "small", device: str = "cuda", language: str = "ru"):
        self.model_name = model_name
        self.device = device
        self.language = language
        self._model = None

    def load(self, on_progress=None):
        from faster_whisper import WhisperModel
        compute_type = "float16" if self.device == "cuda" else "int8"
        if on_progress:
            on_progress("Загрузка модели...")
        self._model = WhisperModel(self.model_name, device=self.device, compute_type=compute_type)
        if on_progress:
            on_progress("Готово")

    def is_loaded(self) -> bool:
        return self._model is not None

    def transcribe(self, audio: np.ndarray) -> str:
        if self._model is None:
            self.load()
        if len(audio) < 3200:  # < 0.2s — too short, skip
            return ""
        segments, _ = self._model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        return " ".join(s.text.strip() for s in segments).strip()
