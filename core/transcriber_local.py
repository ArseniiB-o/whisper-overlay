import numpy as np
from typing import Tuple

# Common faster-whisper hallucinations on silence/quiet audio
_HALLUCINATIONS = frozenset({
    "thank you", "thank you.", "thank you!", "thank you for watching",
    "thank you for watching.", "thanks for watching", "thanks for watching!",
    "thanks.", "thanks!", "thanks", "you", "you.", "bye", "bye.", "goodbye",
    "goodbye.", "see you", "see you.", "see you later", "see you later.",
    "please subscribe", "subscribe", "like and subscribe",
    "спасибо", "спасибо.", "спасибо за просмотр", "спасибо за просмотр.",
    "подпишитесь", "подпишитесь на канал", "лайк", "до свидания",
    ".", "..", "...", " ", "-", "–", "—",
})


class LocalTranscriber:
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

    def transcribe(self, audio: np.ndarray) -> Tuple[str, str]:
        """
        Returns (text, detected_language_code).
        Filters hallucinations and silent segments automatically.
        """
        if self._model is None:
            self.load()
        if len(audio) < 4800:  # < 0.3s — too short
            return "", self.language or "ru"

        lang = None if (self.language in ("auto", None, "")) else self.language
        segments, info = self._model.transcribe(
            audio,
            language=lang,
            beam_size=5,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 400,
            },
        )

        valid = []
        for seg in segments:
            # Skip near-silent segments
            if getattr(seg, "no_speech_prob", 0.0) > 0.60:
                continue
            txt = seg.text.strip()
            # Skip empty or known hallucination phrases
            if not txt or txt.lower().strip(".,!? ") in _HALLUCINATIONS:
                continue
            # Skip if the ENTIRE output is punctuation only
            if all(c in ".,!?;:—–-…\" " for c in txt):
                continue
            valid.append(txt)

        text = " ".join(valid).strip()

        # Strip trailing ellipsis that whisper adds on pauses ("...") — we never want to inject these
        while text.endswith("...") or text.endswith("…"):
            text = text[:-3 if text.endswith("...") else -1].rstrip()

        detected = getattr(info, "language", self.language or "ru")
        return text, detected
