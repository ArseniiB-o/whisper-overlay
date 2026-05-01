import ctypes
import threading
import time

import win32api
import win32con
import win32gui
import win32process

_inject_lock = threading.Lock()


def force_focus(hwnd: int) -> bool:
    """Bring hwnd to foreground. Returns True if successful."""
    if not hwnd:
        return False
    try:
        if not win32gui.IsWindow(hwnd):
            return False
        if win32gui.GetForegroundWindow() == hwnd:
            return True
        cur_tid = win32api.GetCurrentThreadId()
        fg = win32gui.GetForegroundWindow()
        fg_tid = win32process.GetWindowThreadProcessId(fg)[0]
        tgt_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
        user32 = ctypes.windll.user32
        user32.AttachThreadInput(cur_tid, fg_tid, True)
        user32.AttachThreadInput(cur_tid, tgt_tid, True)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        user32.AttachThreadInput(cur_tid, fg_tid, False)
        user32.AttachThreadInput(cur_tid, tgt_tid, False)
        time.sleep(0.08)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception as e:
        print(f"[injector] focus: {e}")
        return False


def inject_text(text: str, hwnd: int = 0):
    """
    Inject text into a window.

    Thread-safe (serialized via lock). Uses pynput for reliable typing.
    If hwnd given: focus that window first, then type.
    If hwnd=0: type to currently focused window (correct when using hotkey).
    """
    if not text:
        return
    with _inject_lock:
        _do_inject(text, hwnd)


def _do_inject(text: str, hwnd: int):
    try:
        from pynput.keyboard import Controller
        kb = Controller()
        if hwnd and win32gui.IsWindow(hwnd):
            fg = win32gui.GetForegroundWindow()
            if fg != hwnd:
                force_focus(hwnd)
                time.sleep(0.05)
        else:
            time.sleep(0.02)
        kb.type(text)
    except Exception as e:
        print(f"[injector] inject: {e}")
