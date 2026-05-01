import os
import sys
import threading
import numpy as np
from typing import Optional, List

SAMPLE_RATE = 16000
CHANNELS = 1


def _import_soundcard():
    """Import soundcard while suppressing its verbose stderr output."""
    old_stderr = sys.stderr
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
        import soundcard as sc
        return sc
    finally:
        try:
            sys.stderr.close()
        except Exception:
            pass
        sys.stderr = old_stderr


class LoopbackCapture:
    """Captures system audio output (WASAPI loopback) — what plays through speakers/headphones.

    Usage:
        cap = LoopbackCapture()   # default output device
        cap.start()
        audio = cap.peek()        # non-destructive snapshot
        audio = cap.stop()        # stop and return full buffer
    """

    def __init__(self, device_name: Optional[str] = None):
        self.device_name = device_name
        self._recording = False
        self._buffer: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._speaker = None

    def start(self):
        if self._recording:
            return
        sc = _import_soundcard()
        if self.device_name:
            speaker = next(
                (s for s in sc.all_speakers() if self.device_name in s.name), None
            )
            if speaker is None:
                speaker = sc.default_speaker()
        else:
            speaker = sc.default_speaker()
        self._speaker = speaker
        with self._lock:
            self._buffer = []
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    def _record_loop(self):
        sc = _import_soundcard()
        try:
            mic = sc.get_microphone(id=str(self._speaker.id), include_loopback=True)
            with mic.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=1600) as recorder:
                while self._recording:
                    data = recorder.record(numframes=1600)
                    if self._recording:
                        chunk = data[:, 0] if data.ndim > 1 else data.flatten()
                        with self._lock:
                            self._buffer.append(chunk.astype(np.float32).copy())
        except Exception as e:
            print(f"[loopback] error: {e}")

    def stop(self) -> np.ndarray:
        self._recording = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(self._buffer, axis=0).astype(np.float32)
            self._buffer = []
        return audio

    def peek(self) -> np.ndarray:
        """Return snapshot of current buffer without stopping."""
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._buffer, axis=0).astype(np.float32)

    @staticmethod
    def list_devices() -> List[dict]:
        try:
            sc = _import_soundcard()
            return [{"name": s.name, "id": str(s.id)} for s in sc.all_speakers()]
        except Exception:
            return []
