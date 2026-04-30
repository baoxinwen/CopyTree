"""系统托盘气泡通知。纯 ctypes 实现，非阻塞。"""

import ctypes
import ctypes.wintypes
import threading

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32

user32.CreateWindowExW.restype = ctypes.wintypes.HWND
user32.CreateWindowExW.argtypes = [
    ctypes.wintypes.DWORD,
    ctypes.c_wchar_p,
    ctypes.c_wchar_p,
    ctypes.wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.wintypes.HWND,
    ctypes.wintypes.HMENU,
    ctypes.wintypes.HINSTANCE,
    ctypes.c_void_p,
]
user32.DestroyWindow.restype = ctypes.wintypes.BOOL
user32.DestroyWindow.argtypes = [ctypes.wintypes.HWND]
user32.LoadIconW.restype = ctypes.wintypes.HICON
user32.LoadIconW.argtypes = [ctypes.wintypes.HINSTANCE, ctypes.c_void_p]
shell32.Shell_NotifyIconW.restype = ctypes.wintypes.BOOL
shell32.Shell_NotifyIconW.argtypes = [ctypes.wintypes.DWORD, ctypes.c_void_p]

IDI_INFORMATION = 32516


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.DWORD),
        ("hWnd", ctypes.wintypes.HWND),
        ("uID", ctypes.wintypes.UINT),
        ("uFlags", ctypes.wintypes.UINT),
        ("uCallbackMessage", ctypes.wintypes.UINT),
        ("hIcon", ctypes.wintypes.HICON),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.wintypes.DWORD),
        ("dwStateMask", ctypes.wintypes.DWORD),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", ctypes.wintypes.UINT),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.wintypes.DWORD),
    ]


_notify_thread: threading.Thread | None = None


def show_notification(title: str, body: str, timeout: float = 3.0) -> bool:
    """在后台线程显示气泡通知，立即返回不阻塞。"""
    global _notify_thread
    t = threading.Thread(target=_show_balloon, args=(title, body, timeout), daemon=True)
    t.start()
    _notify_thread = t
    return True


def wait_notification():
    """等待通知线程结束，防止主进程退出过快导致通知不显示。"""
    if _notify_thread is not None:
        _notify_thread.join(timeout=5.0)


def _show_balloon(title: str, body: str, timeout: float):
    """显示气泡通知并等待超时后清理。"""
    import time

    hwnd = user32.CreateWindowExW(
        0x80, "STATIC", "", 0,
        0, 0, 0, 0, None, None, None, None,
    )
    if not hwnd:
        return

    icon = user32.LoadIconW(None, ctypes.c_void_p(IDI_INFORMATION))

    nid = NOTIFYICONDATAW()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = 0x02 | 0x04 | 0x10  # NIF_ICON | NIF_TIP | NIF_INFO
    nid.hIcon = icon
    nid.szTip = "CopyTree"
    nid.szInfoTitle = title[:63]
    nid.szInfo = body[:255]
    nid.dwInfoFlags = 0x01  # NIIF_INFO

    if not shell32.Shell_NotifyIconW(0, ctypes.byref(nid)):
        user32.DestroyWindow(hwnd)
        return

    time.sleep(timeout)

    shell32.Shell_NotifyIconW(2, ctypes.byref(nid))
    user32.DestroyWindow(hwnd)
