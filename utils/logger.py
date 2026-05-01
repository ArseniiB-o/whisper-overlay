import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class SessionLogger:
    """Logs transcription sessions to JSONL files in logs/ directory."""

    def __init__(self, log_dir: Optional[str] = None, enabled: bool = True):
        self.enabled = enabled
        if log_dir:
            self._log_dir = Path(log_dir)
        else:
            self._log_dir = Path(__file__).parent.parent / "logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._today: str = ""
        self._current_file: Optional[Path] = None
        self._recent: list = []

    def _get_log_file(self) -> Path:
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._today:
            self._today = today
            self._current_file = self._log_dir / f"session_{today}.jsonl"
        return self._current_file

    def log(
        self,
        channel: str,
        text: str,
        language: str = "",
        translation: Optional[dict] = None,
    ):
        """
        channel: "self" (my mic) | "other" (system audio / other speaker)
        text: original transcribed text
        language: detected or configured language code
        translation: {"en": "...", "de": "..."} or None
        """
        if not self.enabled or not text.strip():
            return
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "channel": channel,
            "text": text,
            "lang": language,
            "translation": translation or {},
        }
        self._recent.append(entry)
        if len(self._recent) > 100:
            self._recent.pop(0)
        try:
            with open(self._get_log_file(), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[logger] {e}")

    def get_recent_transcript(self, n_lines: int = 12) -> str:
        """Return last N entries as readable text (for AI context)."""
        lines = self._recent[-n_lines:]
        parts = []
        for e in lines:
            who = "Я" if e["channel"] == "self" else "Собеседник"
            parts.append(f"{who}: {e['text']}")
        return "\n".join(parts)

    @property
    def log_dir(self) -> Path:
        return self._log_dir
