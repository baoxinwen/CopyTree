"""输出格式化：纯文本、Markdown、Markdown 列表和 JSON。"""

import datetime
import json
import os

from loguru import logger

from .constants import FOLDER_PREFIX, LOCK_PREFIX, MSG_NO_ACCESS
from .scanner import (
    ScanResult,
    TreeEntry,
    _format_size,
    build_suffix,
    describe_truncation,
    strip_long_prefix,
)

def format_text(tree_text: str) -> str:
    """返回原始树状文本。"""
    return tree_text


def format_markdown(tree_text: str) -> str:
    """将树状文本包裹在 Markdown 代码块中。"""
    return f"```\n{tree_text}\n```"


def format_markdown_list(
    result: ScanResult, show_size: bool = False, show_time: bool = False
) -> str:
    """生成 Markdown 无序列表。"""
    lines: list[str] = []
    _render_markdown_entry(result.root, 0, lines, show_size, show_time)
    if result.truncated:
        lines.append(f"  - ... 输出已截断：{describe_truncation(result)}")
    return "\n".join(lines)


def format_json(
    result: ScanResult, show_size: bool = False, show_time: bool = False
) -> str:
    """生成结构化 JSON，便于脚本和其他工具消费。"""
    payload = {
        "root": _entry_to_dict(result.root, show_size, show_time),
        "stats": {
            "displayedFiles": result.total_files,
            "displayedDirectories": result.total_dirs,
            "scannedFiles": result.total_files_actual,
            "fileCountsAreComplete": not result.truncated,
            "truncated": result.truncated,
            "scanStopped": result.scan_stopped,
        },
    }
    if result.truncated:
        payload["truncation"] = {
            "summary": describe_truncation(result),
            "truncatedLevels": result.truncated_levels,
            "hiddenItemsByLevel": result.truncated_items,
            "maxFilesLimit": result.max_files_limit,
            "depthLimited": result.depth_limited,
        }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _format_text_wrapper(tree_text: str, **kwargs) -> str:
    return format_text(tree_text)


def _format_markdown_wrapper(tree_text: str, **kwargs) -> str:
    return format_markdown(tree_text)


def _format_markdown_list_wrapper(tree_text: str, result=None, show_size=False, show_time=False, **kwargs) -> str:
    if result is None:
        return tree_text
    return format_markdown_list(result, show_size, show_time)


def _format_json_wrapper(tree_text: str, result=None, show_size=False, show_time=False, **kwargs) -> str:
    if result is None:
        return tree_text
    return format_json(result, show_size, show_time)


_FORMATTERS = {
    "text": _format_text_wrapper,
    "markdown": _format_markdown_wrapper,
    "markdown-list": _format_markdown_list_wrapper,
    "json": _format_json_wrapper,
}


def format_output(
    tree_text: str,
    fmt: str,
    result: ScanResult | None = None,
    show_size: bool = False,
    show_time: bool = False,
) -> str:
    """根据格式类型分发格式化。"""
    formatter = _FORMATTERS.get(fmt, _format_text_wrapper)
    return formatter(tree_text, result=result, show_size=show_size, show_time=show_time)


def _render_markdown_entry(
    entry: TreeEntry,
    indent: int,
    lines: list[str],
    show_size: bool,
    show_time: bool,
):
    prefix = "  " * indent + "- "
    if entry.is_marker:
        lines.append(prefix + entry.name)
        return

    suffix = build_suffix(entry, show_size, show_time)
    if entry.is_dir:
        if entry.access_denied:
            lines.append(f"{prefix}{LOCK_PREFIX}{entry.name}/ ({MSG_NO_ACCESS})")
            return
        lines.append(f"{prefix}{FOLDER_PREFIX}{entry.name}/{suffix}")
        for child in entry.children:
            _render_markdown_entry(child, indent + 1, lines, show_size, show_time)
        return

    lines.append(f"{prefix}{entry.name}{suffix}")


def _entry_to_dict(entry: TreeEntry, show_size: bool, show_time: bool) -> dict:
    if entry.is_marker:
        return {"type": "truncation", "message": entry.name}

    item = {
        "name": _entry_name(entry),
        "type": "directory" if entry.is_dir else "file",
    }
    if entry.path:
        item["path"] = _strip_long_prefix(entry.path)
    if entry.access_denied:
        item["accessDenied"] = True
    if show_time and entry.mtime is not None:
        item["modifiedTime"] = _format_json_time(entry.mtime)
    if not entry.is_dir and show_size:
        item["sizeBytes"] = entry.size
    if entry.is_dir:
        item["children"] = [
            _entry_to_dict(child, show_size, show_time) for child in entry.children
        ]
    return item


def _entry_name(entry: TreeEntry) -> str:
    if not entry.path:
        return entry.name
    name = os.path.basename(entry.path.rstrip("/\\"))
    return name or entry.name


def _strip_long_prefix(path: str) -> str:
    """Strip long-path prefixes so JSON path matches text output."""
    if path.startswith("\\\\?\\UNC\\"):
        return "\\\\" + path[8:]
    if path.startswith("\\\\?\\"):
        return path[4:]
    return path


def _format_json_time(timestamp: float) -> str:
    return datetime.datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
