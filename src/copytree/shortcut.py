"""Start Menu 快捷方式创建与删除。通过 ctypes COM 调用 IShellLinkW。"""

import ctypes
import ctypes.wintypes
import os
from ctypes import HRESULT, POINTER, byref, c_void_p

from .constants import APP_ID, SHORTCUT_DIR, SHORTCUT_NAME

ole32 = ctypes.windll.ole32


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class PROPERTYKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", ctypes.c_ulong)]


# ── 接口 GUID ──
IID_IShellLinkW = GUID()
IID_IPersistFile = GUID()
IID_IPropertyStore = GUID()
CLSID_ShellLink = GUID()

ole32.IIDFromString("{000214F9-0000-0000-C000-000000000046}", byref(IID_IShellLinkW))
ole32.IIDFromString("{0000010B-0000-0000-C000-000000000046}", byref(IID_IPersistFile))
ole32.IIDFromString("{886D8EEB-8CF2-4444-8D02-CDBA1DBDCF99}", byref(IID_IPropertyStore))
ole32.IIDFromString("{00021401-0000-0000-C000-000000000046}", byref(CLSID_ShellLink))

# PKEY_AppUserModelID: {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}, 5
PKEY_AppUserModelID = PROPERTYKEY()
ole32.IIDFromString("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}", byref(PKEY_AppUserModelID.fmtid))
PKEY_AppUserModelID.pid = 5


# vtable 调用辅助
def _vtcall(obj_ptr, slot, *arg_types):
    """获取 COM 对象 vtable 中指定偏移的函数指针。"""
    vtable = ctypes.cast(obj_ptr, POINTER(POINTER(c_void_p))).contents
    return ctypes.cast(
        vtable[slot],
        ctypes.WINFUNCTYPE(HRESULT, c_void_p, *arg_types),
    )


def create_start_menu_shortcut(exe_path: str) -> bool:
    """在 Start Menu 创建快捷方式并设置 AppUserModelID。"""
    shortcut_path = os.path.join(SHORTCUT_DIR, SHORTCUT_NAME)
    os.makedirs(SHORTCUT_DIR, exist_ok=True)

    ole32.CoInitializeEx(None, 0x2)  # COINIT_APARTMENTTHREADED
    try:
        # CoCreateInstance -> IShellLinkW
        ptr = c_void_p()
        hr = ole32.CoCreateInstance(
            byref(CLSID_ShellLink), None, 1, byref(IID_IShellLinkW), byref(ptr)
        )
        if hr != 0 or not ptr.value:
            return False

        # IShellLinkW::SetPath (slot 20)
        _vtcall(ptr, 20, ctypes.c_wchar_p)(ptr.value, exe_path)

        # QueryInterface -> IPropertyStore
        ps_ptr = c_void_p()
        _vtcall(ptr, 0, POINTER(GUID), POINTER(c_void_p))(
            ptr.value, byref(IID_IPropertyStore), byref(ps_ptr)
        )
        if ps_ptr.value:
            # IPropertyStore::SetValue (slot 5)
            pv = _make_lpWSTR(APP_ID)
            _vtcall(ps_ptr, 5, POINTER(PROPERTYKEY), ctypes.c_void_p)(
                ps_ptr.value, byref(PKEY_AppUserModelID), pv
            )
            # IPropertyStore::Commit (slot 6)
            _vtcall(ps_ptr, 6)(ps_ptr.value)
            # IPropertyStore::Release (slot 2)
            _vtcall(ps_ptr, 2)(ps_ptr.value)

        # QueryInterface -> IPersistFile
        pf_ptr = c_void_p()
        _vtcall(ptr, 0, POINTER(GUID), POINTER(c_void_p))(
            ptr.value, byref(IID_IPersistFile), byref(pf_ptr)
        )
        if pf_ptr.value:
            # IPersistFile::Save (slot 6)
            _vtcall(pf_ptr, 6, ctypes.c_wchar_p, ctypes.c_int)(
                pf_ptr.value, shortcut_path, 1
            )
            _vtcall(pf_ptr, 2)(pf_ptr.value)

        _vtcall(ptr, 2)(ptr.value)  # Release
        return True
    except Exception:
        return False
    finally:
        ole32.CoUninitialize()


def remove_start_menu_shortcut() -> bool:
    """删除 Start Menu 快捷方式。"""
    shortcut_path = os.path.join(SHORTCUT_DIR, SHORTCUT_NAME)
    try:
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
        return True
    except OSError:
        return False


def _make_lpWSTR(value: str) -> ctypes.c_void_p:
    """构造一个 VT_LPWSTR (31) PROPVARIANT。简化版：只设置 vt 和指针。"""
    # PROPVARIANT layout (16 bytes on x64):
    #   vt: USHORT (2 bytes)
    #   padding: 6 bytes
    #   union data: 8 bytes (pointer for VT_LPWSTR)
    buf = ctypes.create_string_buffer(16)
    vt = ctypes.c_ushort(31)  # VT_LPWSTR
    ctypes.memmove(buf, ctypes.addressof(vt), 2)
    wstr = ctypes.create_unicode_buffer(value)
    ptr = ctypes.c_void_p(ctypes.addressof(wstr))
    ctypes.memmove(ctypes.addressof(buf) + 8, ctypes.addressof(ptr), ctypes.sizeof(ptr))
    return ctypes.cast(buf, ctypes.c_void_p)
