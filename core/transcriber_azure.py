import numpy as np


LANG_MAP = {
    "ru": "ru-RU",
    "en": "en-US",
    "de": "de-DE",
    "uk": "uk-UA",
}


class AzureTranscriber:
    def __init__(self, key: str, region: str, language: str = "ru"):
        self.key = key
        self.region = region
        self.language = LANG_MAP.get(language, language + "-" + language.upper())

    def transcribe(self, audio: np.ndarray) -> str:
        if not self.key or not self.region:
            return ""
        if len(audio) < 3200:
            return ""

        import azure.cognitiveservices.speech as speechsdk

        speech_config = speechsdk.SpeechConfig(subscription=self.key, region=self.region)
        speech_config.speech_recognition_language = self.language

        audio_int16 = (audio * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()

        audio_format = speechsdk.audio.AudioStreamFormat(
            samples_per_second=16000, bits_per_sample=16, channels=1
        )
        stream = speechsdk.audio.PushAudioInputStream(stream_format=audio_format)
        stream.write(audio_bytes)
        stream.close()

        audio_config = speechsdk.audio.AudioConfig(stream=stream)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )

        result = recognizer.recognize_once()
        if result.reason.name == "RecognizedSpeech":
            return result.text
        return ""
