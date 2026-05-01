import json
import requests
from typing import List


class AIAssistant:
    """AI-powered quick reply suggestions. Supports Ollama (local) and OpenAI-compatible APIs."""

    def __init__(
        self,
        backend: str = "ollama",
        endpoint: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        api_key: str = "",
        enabled: bool = False,
    ):
        self.backend = backend
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.enabled = enabled

    def get_suggestions(self, transcript: str, language: str = "ru", n: int = 3) -> List[str]:
        """Given conversation transcript, return N short reply suggestions."""
        if not self.enabled or not transcript.strip():
            return []
        lang_name = {
            "ru": "Russian", "en": "English", "de": "German",
            "fr": "French", "es": "Spanish", "uk": "Ukrainian",
        }.get(language, language)
        prompt = (
            f"You are a conversation assistant. Given this conversation, suggest {n} "
            f"short natural reply options in {lang_name}.\n"
            f"Context:\n\"{transcript[-600:]}\"\n\n"
            f"Reply with ONLY a JSON array of {n} short strings, nothing else. "
            f'Example: ["Sure!", "I understand", "Tell me more"]'
        )
        try:
            if self.backend == "ollama":
                return self._call_ollama(prompt, n)
            else:
                return self._call_openai(prompt, n)
        except Exception as e:
            print(f"[ai_assistant] {e}")
            return []

    def _call_ollama(self, prompt: str, n: int) -> List[str]:
        resp = requests.post(
            f"{self.endpoint}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=6,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "")
        return self._parse_json_array(text, n)

    def _call_openai(self, prompt: str, n: int) -> List[str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(
            f"{self.endpoint}/v1/chat/completions",
            headers=headers,
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 200,
            },
            timeout=10,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        return self._parse_json_array(text, n)

    def _parse_json_array(self, text: str, n: int) -> List[str]:
        start = text.find("[")
        end = text.rfind("]") + 1
        if start < 0 or end <= start:
            return []
        try:
            result = json.loads(text[start:end])
            if isinstance(result, list):
                return [str(s).strip() for s in result[:n] if s]
        except json.JSONDecodeError:
            pass
        return []

    def is_available(self) -> bool:
        """Check if the AI backend is reachable."""
        try:
            if self.backend == "ollama":
                requests.get(f"{self.endpoint}/api/tags", timeout=2).raise_for_status()
            else:
                requests.get(self.endpoint, timeout=2)
            return True
        except Exception:
            return False
