"""目录扫描与树状文本生成。"""

import ctypes
import os
from dataclasses import dataclass, field

from .constants import (
    FILE_ATTRIBUTE_SYSTEM,
    FOLDER_PREFIX,
    LAST,
    LOCK_PREFIX,
    MAX_NAME_LENGTH,
    MSG_NO_ACCESS,
    MSG_SIZE_UNKNOWN,
    MSG_TRUNCATED_LEVEL,
    MSG_TRUNCATED_TAIL,
    PIPE,
    SPACE,
    BRANCH,
)
from .natural_sort import natural_sort_key

# Windows reparse point 标记，用于检测 Junction
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003


@dataclass
class TreeEntry:
    name: str
    is_dir: bool
    size: int | None = None
    mtime: float | None = None
    access_denied: bool = False
    children: list["TreeEntry"] = field(default_factory=list)
    is_marker: bool = False


@dataclass
class ScanResult:
    root: TreeEntry
    total_files: int = 0
    total_dirs: int = 0
    truncated: bool = False
    total_files_actual: int = 0


def scan_directory(
    path: str,
    exclude_dirs: set[str] | None = None,
    exclude_files: set[str] | None = None,
    max_files: int = 2000,
    max_items_per_level: int = 200,
    show_size: bool = False,
    show_time: bool = False,
    max_depth: int | None = None,
    include_ext: set[str] | None = None,
) -> ScanResult:
    """递归扫描目录，返回 ScanResult。"""
    path = _normalize_path(path)
    name = os.path.basename(path.rstrip("/\\"))
    root = TreeEntry(name=name, is_dir=True)

    ctx = _ScanContext(
        exclude_dirs=exclude_dirs or set(),
        exclude_files=exclude_files or set(),
        max_files=max_files,
        max_items_per_level=max_items_per_level,
        show_size=show_size,
        show_time=show_time,
        include_ext=include_ext,
    )

    ctx._scan_children(root, path, max_depth, 0)

    return ScanResult(
        root=root,
        total_files=ctx.file_count,
        total_dirs=ctx.dir_count,
        truncated=ctx.truncated,
        total_files_actual=ctx.file_count_actual,
    )


class _ScanContext:
    def __init__(
        self,
        exclude_dirs: set[str],
        exclude_files: set[str],
        max_files: int,
        max_items_per_level: int,
        show_size: bool,
        show_time: bool,
        include_ext: set[str] | None,
    ):
        self.exclude_dirs = {d.lower() for d in exclude_dirs}
        self.exclude_files = {f.lower() for f in exclude_files}
        self.max_files = max_files
        self.max_items_per_level = max_items_per_level
        self.show_size = show_size
        self.show_time = show_time
        self.include_ext = {e.lower() for e in include_ext} if include_ext else None
        self.file_count = 0
        self.dir_count = 0
        self.file_count_actual = 0
        self.truncated = False

    def _scan_children(
        self, entry: TreeEntry, path: str, max_depth: int | None, depth: int
    ):
        if max_depth is not None and depth >= max_depth:
            return

        try:
            items = list(os.scandir(path))
        except PermissionError:
            entry.access_denied = True
            return
        except OSError:
            return

        entries: list[TreeEntry] = []
        for item in items:
            child = self._make_entry(item)
            if child is None:
                continue
            if not child.is_dir:
                self.file_count_actual += 1
                if self.file_count_actual > self.max_files:
                    self.truncated = True
                    continue
            entries.append(child)

        entries.sort(key=lambda e: natural_sort_key(e.name))

        # 同级截断
        if len(entries) > self.max_items_per_level:
            hidden_count = len(entries) - (self.max_items_per_level - 1)
            entries = entries[: self.max_items_per_level - 1]
            entries.append(
                TreeEntry(
                    name=MSG_TRUNCATED_LEVEL.format(count=hidden_count),
                    is_dir=False,
                    is_marker=True,
                )
            )

        entry.children = entries
        for child in entries:
            if child.is_marker:
                continue
            if child.is_dir:
                child_path = os.path.join(path, child.name)
                self._scan_children(child, child_path, max_depth, depth + 1)

        # 扩展名过滤模式下，移除不含匹配文件的空目录
        if self.include_ext:
            filtered = []
            for child in entry.children:
                if child.is_marker:
                    filtered.append(child)
                elif child.is_dir:
                    if child.children or child.access_denied:
                        filtered.append(child)
                    # 无子项的目录静默移除
                else:
                    filtered.append(child)
                    self.file_count += 1
            entry.children = filtered
        else:
            for child in entries:
                if child.is_marker:
                    continue
                if child.is_dir:
                    self.dir_count += 1
                else:
                    self.file_count += 1

    def _make_entry(self, item: os.DirEntry) -> TreeEntry | None:
        try:
            is_dir = item.is_dir(follow_symlinks=False)
        except OSError:
            return None

        name = item.name

        # 文件属性检查（Windows）
        try:
            st = item.stat(follow_symlinks=False)
            attrs = st.st_file_attributes
        except OSError:
            attrs = 0

        # 跳过系统文件
        if attrs & FILE_ATTRIBUTE_SYSTEM:
            return None

        # 检测 Junction 点（Windows 上的目录挂载点，不是 symlink）
        # Junction 是 IO_REPARSE_TAG_MOUNT_POINT，is_symlink() 返回 False
        if is_dir and os.name == "nt":
            try:
                if attrs & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                    if hasattr(st, "st_reparse_tag"):
                        if st.st_reparse_tag == IO_REPARSE_TAG_MOUNT_POINT:
                            is_dir = False  # 显示为文件条目，不递归
            except AttributeError:
                pass

        # 符号链接：显示但不跟随（follow_symlinks=False 已处理）
        # is_symlink 的条目会被 is_dir 正确识别但不跟随

        # 过滤
        if is_dir:
            if name.lower() in self.exclude_dirs:
                return None
        else:
            if name.lower() in self.exclude_files:
                return None
            # 扩展名过滤：只显示指定类型的文件
            if self.include_ext:
                _, ext = os.path.splitext(name)
                if ext.lower() not in self.include_ext:
                    return None

        # 文件名截断
        if len(name) > MAX_NAME_LENGTH:
            name = name[: MAX_NAME_LENGTH - 3] + "..."

        entry = TreeEntry(name=name, is_dir=is_dir)

        # 获取文件大小
        if not is_dir and self.show_size:
            try:
                entry.size = st.st_size
            except (OSError, NameError):
                entry.size = None

        # 获取修改时间
        if self.show_time:
            try:
                entry.mtime = st.st_mtime
            except (OSError, NameError):
                entry.mtime = None

        return entry


def _normalize_path(path: str) -> str:
    """标准化路径，超长路径加 \\\\?\\ 前缀。"""
    path = os.path.normpath(path)
    if len(path) > 248 and not path.startswith("\\\\?\\"):
        path = "\\\\?\\" + path
    return path


def build_tree_text(result: ScanResult, show_size: bool = False, show_time: bool = False) -> str:
    """将 ScanResult 转换为树状文本。"""
    lines: list[str] = []

    root = result.root
    if root.access_denied:
        lines.append(f"{LOCK_PREFIX}{root.name}/ ({MSG_NO_ACCESS})")
    else:
        lines.append(f"{FOLDER_PREFIX}{root.name}/")

    for i, child in enumerate(root.children):
        is_last = i == len(root.children) - 1
        _render_child(child, "", is_last, show_size, show_time, lines)

    if result.truncated:
        lines.append(
            MSG_TRUNCATED_TAIL.format(
                count=result.total_files_actual - result.total_files,
                total_files=result.total_files_actual,
                total_dirs=result.total_dirs,
            )
        )

    return "\n".join(lines)


def _render_child(
    entry: TreeEntry,
    parent_prefix: str,
    is_last: bool,
    show_size: bool,
    show_time: bool,
    lines: list[str],
):
    connector = LAST if is_last else BRANCH
    current_prefix = parent_prefix + connector

    if entry.is_marker:
        lines.append(f"{parent_prefix}{entry.name}")
        return

    suffix = _build_suffix(entry, show_size, show_time)

    if entry.is_dir:
        if entry.access_denied:
            lines.append(f"{current_prefix}{LOCK_PREFIX}{entry.name}/ ({MSG_NO_ACCESS})")
        else:
            lines.append(f"{current_prefix}{FOLDER_PREFIX}{entry.name}/{suffix}")
            child_prefix = parent_prefix + (SPACE if is_last else PIPE)
            for i, child in enumerate(entry.children):
                child_is_last = i == len(entry.children) - 1
                _render_child(child, child_prefix, child_is_last, show_size, show_time, lines)
    else:
        lines.append(f"{current_prefix}{entry.name}{suffix}")


def _format_size(size: int) -> str:
    """格式化文件大小。"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size // 1024} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.1f} GB"


def _build_suffix(entry: TreeEntry, show_size: bool, show_time: bool) -> str:
    """构建文件/文件夹后的附加信息（大小、时间）。"""
    parts = []
    if show_time and entry.mtime is not None:
        parts.append(_format_time(entry.mtime))
    if not entry.is_dir and show_size:
        if entry.size is not None:
            parts.append(_format_size(entry.size))
        else:
            parts.append(MSG_SIZE_UNKNOWN)
    if not parts:
        return ""
    return " (" + ", ".join(parts) + ")"


def _format_time(timestamp: float) -> str:
    """格式化修改时间。"""
    import datetime
    dt = datetime.datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y-%m-%d")
