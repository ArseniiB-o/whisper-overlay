import uuid
import requests
from typing import Dict, List

ENDPOINT = "https://api.cognitive.microsofttranslator.com/translate"


class AzureTranslator:
    def __init__(self, key: str = "", region: str = "westeurope"):
        self.key = key
        self.region = region

    def translate(self, text: str, target_langs: List[str], source_lang: str = "ru") -> Dict[str, str]:
        if not self.key or not text.strip() or not target_langs:
            return {}

        headers = {
            "Ocp-Apim-Subscription-Key": self.key,
            "Ocp-Apim-Subscription-Region": self.region,
            "Content-Type": "application/json",
            "X-ClientTraceId": str(uuid.uuid4()),
        }
        params = {"api-version": "3.0", "from": source_lang, "to": target_langs}
        try:
            resp = requests.post(
                ENDPOINT, params=params, headers=headers,
                json=[{"text": text}], timeout=8
            )
            resp.raise_for_status()
            data = resp.json()
            if data:
                return {t["to"]: t["text"] for t in data[0].get("translations", [])}
        except Exception as e:
            print(f"[translator] {e}")
        return {}
