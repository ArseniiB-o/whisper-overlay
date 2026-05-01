from typing import Callable, FrozenSet, Optional, Tuple
from pynput import keyboard

MODIFIER_KEYS = {"ctrl", "shift", "alt", "cmd", "win"}


def parse_hotkey(key_str: str) -> Tuple[FrozenSet[str], str]:
    """Parse "ctrl+shift+f9" → (frozenset({"ctrl", "shift"}), "f9")"""
    parts = [p.strip().lower() for p in key_str.lower().split("+")]
    mods = frozenset(p for p in parts if p in MODIFIER_KEYS)
    main_keys = [p for p in parts if p not in MODIFIER_KEYS]
    main = main_keys[-1] if main_keys else ""
    return mods, main


def hotkey_display(key_str: str) -> str:
    """Return display string: "ctrl+shift+f9" → "CTRL+SHIFT+F9"."""
    return key_str.upper()


class HotkeyManager:
    def __init__(self):
        self._listener: Optional[keyboard.Listener] = None
        # maps (frozenset_of_modifiers, main_key) → (on_press_cb, on_release_cb)
        self._callbacks: dict = {}
        self._held: set = set()  # all currently held key strings

    def register(
        self,
        key_str: str,
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None,
    ):
        """Register hotkey. key_str examples: "f9", "ctrl+shift+f9", "alt+r"."""
        mods, main = parse_hotkey(key_str)
        self._callbacks[(mods, main)] = (on_press, on_release)

    def unregister(self, key_str: str):
        mods, main = parse_hotkey(key_str)
        self._callbacks.pop((mods, main), None)

    def clear(self):
        self._callbacks.clear()
        self._held.clear()

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

    def _key_str(self, key) -> str:
        try:
            c = key.char
            if c:
                return c.lower()
        except AttributeError:
            pass
        name = str(key).replace("Key.", "").lower()
        # Normalize modifier key names
        if name in ("ctrl_l", "ctrl_r"):
            return "ctrl"
        if name in ("shift_l", "shift_r", "shift"):
            return "shift"
        if name in ("alt_l", "alt_r", "alt_gr"):
            return "alt"
        if name in ("cmd", "cmd_l", "cmd_r", "super_l", "super_r"):
            return "cmd"
        return name

    def _current_mods(self) -> FrozenSet[str]:
        return frozenset(k for k in self._held if k in MODIFIER_KEYS)

    def _on_press(self, key):
        ks = self._key_str(key)
        if ks in self._held:
            return
        self._held.add(ks)
        if ks not in MODIFIER_KEYS:
            mods = self._current_mods()
            combo = (mods, ks)
            if combo in self._callbacks:
                cb = self._callbacks[combo][0]
                if cb:
                    try:
                        cb()
                    except Exception:
                        pass

    def _on_release(self, key):
        ks = self._key_str(key)
        if ks not in MODIFIER_KEYS:
            mods = self._current_mods()
            combo = (mods, ks)
            if combo in self._callbacks:
                cb = self._callbacks[combo][1]
                if cb:
                    try:
                        cb()
                    except Exception:
                        pass
        self._held.discard(ks)
