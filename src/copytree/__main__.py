"""CopyTree 入口：CLI 解析、GUI/CLI 模式分发。"""

import argparse
import ctypes
import ctypes.wintypes
import msvcrt
import os
import sys

from .clipboard import copy_to_clipboard
from .config import get_effective_config
from .constants import (
    DEFAULT_OUTPUT_FILENAME_MD,
    DEFAULT_OUTPUT_FILENAME_TXT,
    GENERATED_OUTPUT_FILENAMES,
    MSG_INSTALLED,
    MSG_NOTIFY_FAIL,
    MSG_NOTIFY_SUCCESS,
    MSG_NOTIFY_SUCCESS_TRUNCATED,
    MSG_UNINSTALLED,
    SOURCE_CODE_EXTENSIONS,
    SOURCE_CODE_FILENAMES,
)
from .formatter import format_output
from .notify import show_notification, wait_notification
from .registry import install, uninstall
from .scanner import build_tree_text, scan_directory


ATTACH_PARENT_PROCESS = 0xFFFFFFFF
STD_OUTPUT_HANDLE = 0xFFFFFFF5
STD_ERROR_HANDLE = 0xFFFFFFF4
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
FILE_TYPE_UNKNOWN = 0
_stdio_ready = False

kernel32 = ctypes.windll.kernel32
kernel32.GetConsoleWindow.restype = ctypes.wintypes.HWND
kernel32.GetConsoleWindow.argtypes = []
kernel32.GetStdHandle.restype = ctypes.wintypes.HANDLE
kernel32.GetStdHandle.argtypes = [ctypes.wintypes.DWORD]
kernel32.GetFileType.restype = ctypes.wintypes.DWORD
kernel32.GetFileType.argtypes = [ctypes.wintypes.HANDLE]
kernel32.AttachConsole.restype = ctypes.wintypes.BOOL
kernel32.AttachConsole.argtypes = [ctypes.wintypes.DWORD]


def _has_console() -> bool:
    """检测当前进程是否拥有控制台。"""
    try:
        return kernel32.GetConsoleWindow() != 0
    except Exception:
        return False


def _attach_parent_console() -> bool:
    """附加到父进程的控制台（用于 console=False 构建）。"""
    global _stdio_ready
    if _stdio_ready:
        return True
    if _has_console():
        _stdio_ready = True
        return True
    stdout = _open_std_stream(STD_OUTPUT_HANDLE)
    stderr = _open_std_stream(STD_ERROR_HANDLE)
    if stdout or stderr:
        if stdout:
            sys.stdout = stdout
        if stderr:
            sys.stderr = stderr
        _stdio_ready = True
        return True
    try:
        if kernel32.AttachConsole(ATTACH_PARENT_PROCESS):
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", closefd=False)
            sys.stderr = open("CONERR$", "w", encoding="utf-8", closefd=False)
            _stdio_ready = True
            return True
    except Exception:
        pass
    return False


def _open_std_stream(handle_id: int):
    """打开继承的 stdout/stderr 句柄，支持重定向和测试捕获。"""
    try:
        handle = kernel32.GetStdHandle(handle_id)
        handle_value = getattr(handle, "value", handle)
        if not handle_value or handle_value == INVALID_HANDLE_VALUE:
            return None
        if kernel32.GetFileType(handle) == FILE_TYPE_UNKNOWN:
            return None
        fd = msvcrt.open_osfhandle(handle_value, os.O_TEXT)
        return open(fd, "w", encoding="utf-8", buffering=1, closefd=False)
    except Exception:
        return None


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="CopyTree",
        description="一键复制文件目录树到剪贴板",
    )
    parser.add_argument("path", nargs="?", help="目标文件夹路径")
    parser.add_argument("--size", action="store_true", help="显示文件大小")
    parser.add_argument("--time", action="store_true", help="显示修改时间")
    parser.add_argument(
        "--format",
        choices=["text", "markdown"],
        dest="fmt",
        help="输出格式：text（默认）或 markdown",
    )
    parser.add_argument(
        "--filter", action="store_true", dest="apply_filter",
        help="过滤配置文件中指定的目录和文件"
    )
    parser.add_argument(
        "--exclude", action="append", default=[],
        help="额外排除的目录或文件名（可多次使用）",
    )
    parser.add_argument(
        "--source-only", action="store_true", help="仅显示源码文件（内置列表）"
    )
    parser.add_argument(
        "--filter-ext", action="store_true", dest="filter_ext",
        help="仅显示配置文件中 filterExt 指定后缀的文件"
    )
    parser.add_argument(
        "--save", action="store_true", help="保存到目标目录下的 directory_tree.txt"
    )
    parser.add_argument(
        "--save-md", action="store_true", dest="save_md",
        help="保存到目标目录下的 directory_tree.md"
    )
    parser.add_argument(
        "--max-depth", type=int, default=None, help="限制显示深度（0 = 仅根目录）"
    )
    parser.add_argument("--install", action="store_true", help="安装：注册右键菜单")
    parser.add_argument("--uninstall", action="store_true", help="卸载：清除右键菜单")
    parser.add_argument(
        "--config", action="store_true", help="打开配置文件进行编辑"
    )
    parser.add_argument(
        "--version", action="store_true", help="显示版本号"
    )
    return parser


def main():
    _attach_parent_console()
    parser = _build_arg_parser()
    args = parser.parse_args()

    # 版本号
    if args.version:
        from .constants import VERSION

        _print(f"CopyTree {VERSION}")
        _exit(0)

    # 双击运行（无参数）：自动安装/卸载
    if not args.path and not args.install and not args.uninstall and not args.config and not args.version:
        exe_path = _get_exe_path()
        if install(exe_path):
            _notify(MSG_INSTALLED)
        else:
            _notify("安装失败")
            _exit(3)
        _exit(0)

    # 安装模式
    if args.install:
        exe_path = _get_exe_path()
        if install(exe_path):
            _notify(MSG_INSTALLED)
        else:
            _notify("安装失败")
            _exit(3)
        _exit(0)

    # 卸载模式
    if args.uninstall:
        if uninstall():
            _notify(MSG_UNINSTALLED)
        else:
            _notify("卸载失败")
            _exit(3)
        _exit(0)

    # 打开配置文件
    if args.config:
        from .config import open_config_file

        if not open_config_file():
            _notify("无法打开配置文件")
            _exit(3)
        _exit(0)

    # 目录树模式
    if not args.path:
        parser.print_help()
        _exit(1)

    target = os.path.abspath(args.path)
    if not os.path.isdir(target):
        _print_err(f"错误：'{target}' 不是有效的目录")
        _exit(1)

    # 合并配置
    cli_overrides = {}
    if args.fmt:
        cli_overrides["defaultFormat"] = args.fmt

    config = get_effective_config(cli_overrides or None)
    show_size = args.size or config.get("showFileSize", False)

    # 合并排除列表：--filter 时应用配置文件的排除规则
    if args.apply_filter:
        exclude_dirs = set(config["excludeDirs"])
        exclude_files = set(config["excludeFiles"])
    else:
        exclude_dirs = set()
        exclude_files = set()
    for name in args.exclude:
        exclude_dirs.add(name)
        exclude_files.add(name)
    exclude_files.update(GENERATED_OUTPUT_FILENAMES)

    # 深度：CLI 参数 > 配置文件 > 无限制
    max_depth = args.max_depth if args.max_depth is not None else config.get("maxDepth", -1)
    if max_depth == -1:
        max_depth = None

    show_time = args.time

    # 扩展名过滤
    include_ext = None
    include_names = None
    if args.source_only:
        include_ext = SOURCE_CODE_EXTENSIONS
        include_names = SOURCE_CODE_FILENAMES
    elif args.filter_ext:
        include_ext = set(config.get("filterExt", []))

    # 扫描目录
    result = scan_directory(
        path=target,
        exclude_dirs=exclude_dirs,
        exclude_files=exclude_files,
        max_files=config["maxFiles"],
        max_items_per_level=config["maxItemsPerLevel"],
        show_size=show_size,
        show_time=show_time,
        max_depth=max_depth,
        include_ext=include_ext,
        include_names=include_names,
    )

    tree_text = build_tree_text(result, show_size=show_size, show_time=show_time)
    output = format_output(tree_text, config.get("defaultFormat", "text"))

    # 保存到文件
    if args.save or args.save_md:
        if args.save_md:
            save_path = os.path.join(target, DEFAULT_OUTPUT_FILENAME_MD)
            save_content = format_output(tree_text, "markdown")
        else:
            save_path = os.path.join(target, DEFAULT_OUTPUT_FILENAME_TXT)
            save_content = tree_text
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(save_content)
        except OSError as e:
            gui_mode = not _has_console()
            if gui_mode:
                _notify(f"保存失败：{e}")
            else:
                _print_err(f"保存失败：{e}")
            _exit(3)

    # 复制到剪贴板
    if not copy_to_clipboard(output):
        gui_mode = not _has_console()
        if gui_mode:
            _notify(MSG_NOTIFY_FAIL.format(error="剪贴板被占用"))
        else:
            _print_err("复制失败：剪贴板被占用")
        _exit(2)

    # 输出结果
    gui_mode = not _has_console()
    if gui_mode:
        if result.truncated:
            msg = MSG_NOTIFY_SUCCESS_TRUNCATED.format(
                files=result.total_files,
                dirs=result.total_dirs,
                total=result.total_files_actual,
            )
        else:
            msg = MSG_NOTIFY_SUCCESS.format(
                files=result.total_files, dirs=result.total_dirs
            )
        _notify(msg)
    else:
        _attach_parent_console()
        print(output)

    _exit(0)


def _get_exe_path() -> str:
    """获取当前 exe 的完整路径。"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def _print(msg: str):
    """安全输出到 stdout。"""
    try:
        _attach_parent_console()
        if sys.stdout:
            print(msg)
    except Exception:
        pass


def _print_err(msg: str):
    """安全输出到 stderr。"""
    try:
        _attach_parent_console()
        if sys.stderr:
            print(msg, file=sys.stderr)
    except Exception:
        pass


def _notify(msg: str):
    """显示系统通知。"""
    show_notification("CopyTree", msg)


def _exit(code: int = 0):
    """等待通知完成后退出进程。"""
    wait_notification()
    sys.exit(code)


if __name__ == "__main__":
    main()
