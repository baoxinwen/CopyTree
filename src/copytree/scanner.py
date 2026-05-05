"""目录扫描与树状文本生成。"""

import ctypes
import os
import sys
from dataclasses import dataclass, field

from .constants import (
    BRANCH,
    FILE_ATTRIBUTE_SYSTEM,
    FOLDER_PREFIX,
    LAST,
    LOCK_PREFIX,
    MAX_NAME_LENGTH,
    MSG_NO_ACCESS,
    MSG_SIZE_UNKNOWN,
    MSG_TRUNCATED_DEPTH,
    MSG_TRUNCATED_LEVEL,
    MSG_TRUNCATED_TAIL,
    PIPE,
    SPACE,
)
from .natural_sort import natural_sort_key

# Windows reparse point 标记，用于检测 Junction
IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003

# MAX_PATH 前缀阈值，超过此长度的路径需要 \\\\?\\ 前缀
_MAX_PATH_PREFIX_THRESHOLD = 248


@dataclass
class TreeEntry:
    name: str
    is_dir: bool
    path: str | None = None
    size: int | None = None
    mtime: float | None = None
    access_denied: bool = False
    children: list["TreeEntry"] = field(default_factory=list)
    is_marker: bool = False
    had_children: bool = False


@dataclass
class ScanResult:
    root: TreeEntry
    total_files: int = 0
    total_dirs: int = 0
    truncated: bool = False
    total_files_actual: int = 0
    truncated_levels: int = 0
    truncated_items: int = 0
    scan_stopped: bool = False
    max_files_limit: int | None = None
    depth_limited: bool = False


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
    include_names: set[str] | None = None,
    prune_empty_dirs: bool = False,
) -> ScanResult:
    """递归扫描目录，返回 ScanResult。"""
    path = _normalize_path(path)
    name = _root_display_name(path)
    root = TreeEntry(name=name, is_dir=True, path=path)

    ctx = _ScanContext(
        exclude_dirs=exclude_dirs or set(),
        exclude_files=exclude_files or set(),
        max_files=max_files,
        max_items_per_level=max_items_per_level,
        show_size=show_size,
        show_time=show_time,
        include_ext=include_ext,
        include_names=include_names,
        prune_empty_dirs=prune_empty_dirs,
    )

    ctx._scan_children(root, path, max_depth, 0)
    total_files, total_dirs = _count_tree(root)

    return ScanResult(
        root=root,
        total_files=total_files,
        total_dirs=total_dirs,
        truncated=ctx.truncated,
        total_files_actual=ctx.file_count_actual,
        truncated_levels=ctx.truncated_levels,
        truncated_items=ctx.truncated_items,
        scan_stopped=ctx.scan_stopped,
        max_files_limit=max_files if max_files >= 0 else None,
        depth_limited=ctx.depth_limited,
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
        include_names: set[str] | None,
        prune_empty_dirs: bool,
    ):
        self.exclude_dirs = {d.lower() for d in exclude_dirs}
        self.exclude_files = {f.lower() for f in exclude_files}
        self.max_files = max_files
        self.max_items_per_level = max(1, max_items_per_level)
        self.show_size = show_size
        self.show_time = show_time
        self.include_ext = {e.lower() for e in include_ext} if include_ext is not None else None
        self.include_names = {n.lower() for n in include_names} if include_names is not None else None
        self.prune_empty_dirs = prune_empty_dirs
        self.file_count_actual = 0
        self.truncated = False
        self.truncated_levels = 0
        self.truncated_items = 0
        self.scan_stopped = False
        self.depth_limited = False
        self.max_safe_depth = max(10, sys.getrecursionlimit() - 200)

    def _scan_children(
        self, entry: TreeEntry, path: str, max_depth: int | None, depth: int
    ):
        if max_depth is not None and depth >= max_depth:
            return
        if depth >= self.max_safe_depth:
            self._mark_depth_limited(entry)
            return

        entries, stopped_while_listing = self._list_entries(entry, path)
        if entries is None:
            return

        entries.sort(key=lambda e: natural_sort_key(e.name))
        if stopped_while_listing:
            entries = [child for child in entries if not child.is_dir]

        entries = self._apply_level_truncation(entries)
        entry.children = entries

        if stopped_while_listing:
            self._prune_empty_dirs(entry)
            return

        entry.children = self._scan_subdirs(entry, entries, path, max_depth, depth)
        self._prune_empty_dirs(entry)

    def _list_entries(self, entry: TreeEntry, path: str) -> tuple[list[TreeEntry] | None, bool]:
        """列出目录内容，返回 (entries, stopped) 或 (None, False) 表示权限拒绝。"""
        entries: list[TreeEntry] = []
        stopped = False
        try:
            with os.scandir(path) as items:
                for item in items:
                    if self.scan_stopped:
                        break
                    entry.had_children = True
                    child = self._make_entry(item)
                    if child is None:
                        continue
                    if not child.is_dir and self._reached_file_limit():
                        self.truncated = True
                        self.scan_stopped = True
                        stopped = True
                        break
                    if not child.is_dir:
                        self.file_count_actual += 1
                    entries.append(child)
        except PermissionError:
            entry.access_denied = True
            return None, False
        except OSError:
            return None, False
        return entries, stopped

    def _reached_file_limit(self) -> bool:
        return self.max_files >= 0 and self.file_count_actual >= self.max_files

    def _apply_level_truncation(self, entries: list[TreeEntry]) -> list[TreeEntry]:
        if len(entries) <= self.max_items_per_level:
            return entries
        hidden_count = len(entries) - (self.max_items_per_level - 1)
        entries = entries[: self.max_items_per_level - 1]
        self.truncated = True
        self.truncated_levels += 1
        self.truncated_items += hidden_count
        entries.append(
            TreeEntry(
                name=MSG_TRUNCATED_LEVEL.format(count=hidden_count),
                is_dir=False,
                is_marker=True,
            )
        )
        return entries

    def _scan_subdirs(
        self,
        parent: TreeEntry,
        entries: list[TreeEntry],
        path: str,
        max_depth: int | None,
        depth: int,
    ) -> list[TreeEntry]:
        scanned: list[TreeEntry] = []
        for child in entries:
            if child.is_marker or not child.is_dir:
                scanned.append(child)
                continue
            if self.scan_stopped:
                break
            child_path = child.path or os.path.join(path, child.name)
            self._scan_children(child, child_path, max_depth, depth + 1)
            if self._should_stop_after_scan(child):
                break
            scanned.append(child)
        return scanned

    def _should_stop_after_scan(self, child: TreeEntry) -> bool:
        return (
            self.scan_stopped
            and not child.children
            and not child.access_denied
            and child.had_children
        )

    def _prune_empty_dirs(self, entry: TreeEntry):
        """主动过滤模式下，移除因过滤变空的目录，保留原本就是空的目录。"""
        if self.prune_empty_dirs or self.include_ext is not None or self.include_names is not None:
            filtered = []
            for child in entry.children:
                if child.is_marker:
                    filtered.append(child)
                elif child.is_dir:
                    if child.children or child.access_denied or not child.had_children:
                        filtered.append(child)
                    # 有原始子项但过滤后无可显示内容的目录静默移除
                else:
                    filtered.append(child)
            entry.children = filtered

    def _mark_depth_limited(self, entry: TreeEntry):
        self.truncated = True
        self.depth_limited = True
        entry.children = [
            TreeEntry(
                name=MSG_TRUNCATED_DEPTH,
                is_dir=False,
                is_marker=True,
            )
        ]

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
        except (OSError, AttributeError):
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
            if self.include_ext is not None or self.include_names is not None:
                _, ext = os.path.splitext(name)
                name_matches = self.include_names is not None and name.lower() in self.include_names
                ext_matches = self.include_ext is not None and ext.lower() in self.include_ext
                if not name_matches and not ext_matches:
                    return None

        # 文件名截断只影响显示，递归仍使用 DirEntry 的真实路径。
        display_name = name
        if len(display_name) > MAX_NAME_LENGTH:
            display_name = display_name[: MAX_NAME_LENGTH - 3] + "..."

        entry = TreeEntry(name=display_name, is_dir=is_dir, path=_normalize_path(item.path))

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
    if path.startswith("\\\\?\\"):
        return path
    if len(path) > _MAX_PATH_PREFIX_THRESHOLD:
        if path.startswith("\\\\"):
            path = "\\\\?\\UNC\\" + path.lstrip("\\")
        else:
            if not os.path.isabs(path):
                path = os.path.abspath(path)
            path = "\\\\?\\" + path
    return path


def _root_display_name(path: str) -> str:
    """返回根节点展示名，兼容 C:\\ 这类驱动器根目录。"""
    display_path = path
    if display_path.startswith("\\\\?\\UNC\\"):
        display_path = "\\\\" + display_path[8:]
    elif display_path.startswith("\\\\?\\"):
        display_path = display_path[4:]
    stripped = display_path.rstrip("/\\")
    name = os.path.basename(stripped)
    if name:
        return name
    drive, _tail = os.path.splitdrive(display_path)
    if drive:
        return drive
    return display_path or os.sep


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
                details=describe_truncation(result),
                shown_files=result.total_files,
                total_dirs=result.total_dirs,
            )
        )

    return "\n".join(lines)


def describe_truncation(result: ScanResult) -> str:
    """返回适合展示给用户的截断原因摘要。"""
    details = []
    if result.scan_stopped:
        if result.max_files_limit is not None:
            details.append(f"达到 maxFiles={result.max_files_limit}，后续内容未扫描")
        else:
            details.append("后续内容未扫描")
    if result.truncated_levels:
        details.append(
            f"{result.truncated_levels} 个层级超过 maxItemsPerLevel，隐藏 {result.truncated_items} 项"
        )
    if result.depth_limited:
        details.append("目录层级过深，后续未扫描")
    if not details and result.truncated:
        hidden_files = max(0, result.total_files_actual - result.total_files)
        if hidden_files:
            details.append(f"隐藏 {hidden_files} 个文件")
        else:
            details.append("部分内容未显示")
    return "；".join(details)


def _count_tree(root: TreeEntry) -> tuple[int, int]:
    files = 0
    dirs = 0
    stack = list(root.children)
    while stack:
        entry = stack.pop()
        if entry.is_marker:
            continue
        if entry.is_dir:
            dirs += 1
            stack.extend(entry.children)
        else:
            files += 1
    return files, dirs


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
        lines.append(f"{current_prefix}{entry.name}")
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
    if size < 0:
        return MSG_SIZE_UNKNOWN
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
