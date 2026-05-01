import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

DEFAULT_CONFIG = {
    "backend": "local",
    "model": "small",
    "device": "cuda",
    "language": "ru",
    "translate_to": ["de", "en"],
    "translate_enabled": False,
    "auto_inject": True,
    "hotkey": "f9",
    "recording_mode": "toggle",
    "transcript_visible": True,
    "loopback_enabled": False,
    "loopback_device": None,
    "loopback_language": "auto",
    "loopback_translate_enabled": True,
    "loopback_translate_to": ["ru"],
    "ai_assistant": {
        "enabled": False,
        "backend": "ollama",
        "endpoint": "http://localhost:11434",
        "model": "llama3.2:3b",
        "api_key": "",
    },
    "logging": {
        "enabled": True,
        "log_dir": "",
    },
    "window": {
        "x": 100,
        "y": 100,
        "width": 420,
        "height": 500,
        "opacity": 0.95,
    },
    "azure": {
        "speech_key": "",
        "speech_region": "westeurope",
        "translator_key": "",
        "translator_region": "westeurope",
    },
    "audio": {
        "device_index": None,
        "sample_rate": 16000,
    },
}


class Config:
    def __init__(self):
        self._data = self._deep_copy(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    self._deep_update(self._data, json.load(f))
            except Exception:
                pass

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, *keys, default=None):
        d = self._data
        for k in keys:
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d

    def set(self, *keys_and_value):
        *keys, value = keys_and_value
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def _deep_update(self, base: dict, update: dict):
        for k, v in update.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                self._deep_update(base[k], v)
            else:
                base[k] = v

    def _deep_copy(self, d):
        return json.loads(json.dumps(d))
