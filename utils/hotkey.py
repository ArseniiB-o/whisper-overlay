from typing import Callable, Optional
from pynput import keyboard


class HotkeyManager:
    def __init__(self):
        self._listener: Optional[keyboard.Listener] = None
        self._callbacks: dict = {}
        self._held: set = set()

    def register(
        self,
        key_str: str,
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None,
    ):
        self._callbacks[key_str.lower()] = (on_press, on_release)

    def start(self):
        if self._listener and self._listener.is_alive():
            return
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._held.clear()

    def update_hotkey(self, old_key: str, new_key: str, on_press=None, on_release=None):
        self._callbacks.pop(old_key.lower(), None)
        self.register(new_key, on_press, on_release)

    def _key_str(self, key) -> str:
        try:
            return key.char.lower() if key.char else str(key).replace("Key.", "").lower()
        except AttributeError:
            return str(key).replace("Key.", "").lower()

    def _on_press(self, key):
        ks = self._key_str(key)
        if ks in self._held:
            return
        self._held.add(ks)
        if ks in self._callbacks:
            cb = self._callbacks[ks][0]
            if cb:
                try:
                    cb()
                except Exception:
                    pass

    def _on_release(self, key):
        ks = self._key_str(key)
        self._held.discard(ks)
        if ks in self._callbacks:
            cb = self._callbacks[ks][1]
            if cb:
                try:
                    cb()
                except Exception:
                    pass
