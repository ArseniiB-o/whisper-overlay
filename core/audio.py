import threading
import numpy as np
import sounddevice as sd
from typing import Optional, List

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"


class AudioCapture:
    def __init__(self, device_index: Optional[int] = None):
        self.device_index = device_index
        self._stream: Optional[sd.InputStream] = None
        self._recording = False
        self._buffer: List[np.ndarray] = []
        self._lock = threading.Lock()

    def start(self):
        if self._recording:
            return
        with self._lock:
            self._buffer = []
        self._recording = True
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            device=self.device_index,
            blocksize=int(SAMPLE_RATE * 0.1),
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if not self._recording:
            return np.array([], dtype=np.float32)
        self._recording = False
        if self._stream:
            self._stream.stop()  # blocks until callback finishes current call
            self._stream.close()
            self._stream = None
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            audio = np.concatenate(self._buffer, axis=0).flatten()
            self._buffer = []
        return audio

    def peek(self) -> np.ndarray:
        """Return a copy of current buffer without stopping the stream."""
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            return np.concatenate(self._buffer, axis=0).flatten()

    def _callback(self, indata, frames, time_info, status):
        if self._recording:
            with self._lock:
                self._buffer.append(indata.copy())

    @staticmethod
    def list_devices() -> List[dict]:
        devices = sd.query_devices()
        result = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                result.append({"index": i, "name": d["name"]})
        return result
