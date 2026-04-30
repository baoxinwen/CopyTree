"""注册表安装/卸载操作。二级子菜单结构。"""

import os
import winreg

from .constants import APP_ID
from .shortcut import create_start_menu_shortcut, remove_start_menu_shortcut

# 子菜单项定义：(注册表子键名, 菜单文字, 命令行参数后缀, 是否在此项前加分隔线)
_SUBMENU_ITEMS = [
    # 复制到剪贴板
    ("01copy",     "复制目录树",                    "",                    False),
    ("02filter",   "复制目录树（过滤指定目录）",     "--filter",            False),
    ("03size",     "复制目录树（含大小）",            "--size",              False),
    ("04time",     "复制目录树（含修改时间）",        "--time",              False),
    ("05source",   "复制目录树（仅指定后缀文件）",    "--filter-ext",        False),
    ("06depth",    "复制目录树（限2层）",            "--max-depth 2",       False),
    # Markdown 格式
    ("07md",       "复制为 Markdown",               "--format markdown",   True),
    ("08mdsize",   "复制为 Markdown（含大小）",      "--format markdown --size", False),
    # 保存到文件
    ("09savetxt",  "保存为 txt",                    "--save",              True),
    ("10savemd",   "保存为 Markdown",               "--save-md",           False),
    # 设置
    ("11config",   "打开配置文件",                   "--config",            True),
]

# 需要注册子菜单的两个位置
_MENU_ROOTS = [
    r"Software\Classes\Directory\shell\CopyTree",         # 右键点击文件夹
    r"Software\Classes\Directory\Background\shell\CopyTree",  # 空白处右键
]


def install(exe_path: str) -> bool:
    """注册二级子菜单、创建快捷方式、注册 AUMID。"""
    exe_path = os.path.abspath(exe_path)
    if not os.path.isfile(exe_path):
        return False

    try:
        for root in _MENU_ROOTS:
            is_background = "Background" in root
            arg_param = r'"%V"' if is_background else r'"%1"'
            _write_submenu(root, exe_path, arg_param)

        if not create_start_menu_shortcut(exe_path):
            return False
        _register_aumid(exe_path)
        return True
    except OSError:
        return False


def uninstall() -> bool:
    """清除所有注册表项、删除快捷方式。"""
    for root in _MENU_ROOTS:
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, root)

    # 清理旧的单独注册项（兼容旧版本升级）
    for old_key in [
        r"Software\Classes\Directory\shell\CopyTree.WithSize",
        r"Software\Classes\Directory\Background\shell\CopyTree.WithSize",
    ]:
        _delete_key_recursive(winreg.HKEY_CURRENT_USER, old_key)

    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\AppUserModelId\{APP_ID}")
    except (FileNotFoundError, OSError):
        pass

    remove_start_menu_shortcut()
    return True


def _write_submenu(root: str, exe_path: str, arg_param: str):
    """写入一个二级子菜单的完整注册表结构。"""
    # 先清理旧的 shell 子键，避免残留
    _delete_key_recursive(winreg.HKEY_CURRENT_USER, root + r"\shell")

    # 父菜单键
    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, root, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, "CopyTree")
    winreg.SetValueEx(key, "SubCommands", 0, winreg.REG_SZ, "")
    winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}",0')
    winreg.CloseKey(key)

    # 空的 command 子键（父菜单需要）
    cmd_key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, root + r"\command", 0, winreg.KEY_WRITE
    )
    winreg.CloseKey(cmd_key)

    # 各子菜单项
    for subkey_name, label, args, separator in _SUBMENU_ITEMS:
        item_path = root + r"\shell" + "\\" + subkey_name

        item_key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, item_path, 0, winreg.KEY_WRITE
        )
        winreg.SetValueEx(item_key, "", 0, winreg.REG_SZ, label)
        winreg.SetValueEx(item_key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}",0')
        if separator:
            winreg.SetValueEx(item_key, "CommandFlags", 0, winreg.REG_DWORD, 0x20)
        winreg.CloseKey(item_key)

        # 子项的 command
        cmd_path = item_path + r"\command"
        cmd_key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, cmd_path, 0, winreg.KEY_WRITE
        )
        cmd_str = f'"{exe_path}" {arg_param}'
        if args:
            cmd_str += f" {args}"
        winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd_str)
        winreg.CloseKey(cmd_key)


def _delete_key_recursive(root: int, key_path: str):
    """递归删除注册表键及其所有子键。"""
    try:
        key = winreg.OpenKey(root, key_path, 0, winreg.KEY_READ)
    except FileNotFoundError:
        return
    except OSError:
        return

    # 先收集所有子键名
    subkeys = []
    try:
        i = 0
        while True:
            name = winreg.EnumKey(key, i)
            subkeys.append(name)
            i += 1
    except OSError:
        pass
    winreg.CloseKey(key)

    # 递归删除子键
    for name in subkeys:
        _delete_key_recursive(root, key_path + "\\" + name)

    # 删除自身
    try:
        winreg.DeleteKey(root, key_path)
    except (FileNotFoundError, OSError):
        pass


def _register_aumid(exe_path: str):
    """在注册表中注册 AppUserModelID（通知所需）。"""
    key_path = rf"Software\Classes\AppUserModelId\{APP_ID}"
    key = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "CopyTree")
    winreg.SetValueEx(key, "IconUri", 0, winreg.REG_SZ, exe_path)
    winreg.CloseKey(key)
