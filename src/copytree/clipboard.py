"""Win32 剪贴板写入，ctypes 实现。"""

import ctypes
import ctypes.wintypes
import time

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002

# 设置正确的函数签名（64 位下必须显式设置返回类型）
kernel32.GlobalAlloc.restype = ctypes.wintypes.HGLOBAL
kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL
kernel32.GlobalUnlock.argtypes = [ctypes.wintypes.HGLOBAL]
kernel32.GlobalFree.restype = ctypes.wintypes.HGLOBAL
kernel32.GlobalFree.argtypes = [ctypes.wintypes.HGLOBAL]

user32.OpenClipboard.restype = ctypes.wintypes.BOOL
user32.OpenClipboard.argtypes = [ctypes.wintypes.HWND]
user32.CloseClipboard.restype = ctypes.wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.EmptyClipboard.restype = ctypes.wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def copy_to_clipboard(text: str) -> bool:
    """将 Unicode 文本写入系统剪贴板。失败重试 3 次，间隔 100ms。"""
    for _ in range(3):
        if _write_clipboard(text):
            return True
        time.sleep(0.1)
    return False


def _write_clipboard(text: str) -> bool:
    data = text.encode("utf-16-le") + b"\x00\x00"
    h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not h_mem:
        return False

    ptr = kernel32.GlobalLock(h_mem)
    if not ptr:
        kernel32.GlobalFree(h_mem)
        return False

    ctypes.memmove(ptr, data, len(data))
    kernel32.GlobalUnlock(h_mem)

    if not user32.OpenClipboard(0):
        kernel32.GlobalFree(h_mem)
        return False

    user32.EmptyClipboard()
    result = user32.SetClipboardData(CF_UNICODETEXT, h_mem)
    user32.CloseClipboard()

    if not result:
        return False

    return True
