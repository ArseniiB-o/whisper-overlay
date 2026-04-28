import ctypes
import time
import win32api
import win32con
import win32gui
import win32process


def force_focus(hwnd: int) -> bool:
    """Reliably bring hwnd to foreground using AttachThreadInput trick."""
    if not hwnd:
        return False
    try:
        if not win32gui.IsWindow(hwnd):
            return False
        fg = win32gui.GetForegroundWindow()
        if fg == hwnd:
            return True
        cur_tid = win32api.GetCurrentThreadId()
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
        return True
    except Exception as e:
        print(f"[injector] focus: {e}")
        return False


def inject_text(text: str, hwnd: int = 0):
    if not text:
        return
    try:
        from pynput.keyboard import Controller
        kb = Controller()
        if hwnd:
            if force_focus(hwnd):
                time.sleep(0.12)
            else:
                time.sleep(0.05)
        else:
            time.sleep(0.05)
        kb.type(text + " ")
    except Exception as e:
        print(f"[injector] type: {e}")
