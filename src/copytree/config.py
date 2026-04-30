"""配置文件加载。从 %APPDATA%/CopyTree/copytree.json 读取，缺失或格式错误时使用默认值。"""

import json
import os

from .constants import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_EXCLUDE_DIRS,
    DEFAULT_EXCLUDE_FILES,
    MAX_FILES,
    MAX_ITEMS_PER_LEVEL,
    SOURCE_CODE_EXTENSIONS,
)

_DEFAULTS = {
    "excludeDirs": list(DEFAULT_EXCLUDE_DIRS),
    "excludeFiles": list(DEFAULT_EXCLUDE_FILES),
    "maxFiles": MAX_FILES,
    "maxItemsPerLevel": MAX_ITEMS_PER_LEVEL,
    "maxDepth": -1,
    "defaultFormat": "text",
    "showFileSize": False,
    "filterExt": sorted(SOURCE_CODE_EXTENSIONS),
}

_COMMENTS = {
    "__说明": "这是 CopyTree 的配置文件。修改后保存，下次使用右键菜单时生效。删除此文件可恢复默认设置。",
    "__excludeDirs说明": "要排除的目录名列表。精确匹配目录名，大小写不敏感。例如想排除 logs 目录，就在列表里加上 \"logs\"。",
    "__excludeFiles说明": "要排除的文件名列表。精确匹配文件名，大小写不敏感。",
    "__maxFiles说明": "最大显示文件总数。超过此数量会截断并在末尾提示。设为 -1 表示不限制。",
    "__maxItemsPerLevel说明": "同一层级（同一个文件夹内）最大显示项数。超过此数量会在该层级截断。",
    "__maxDepth说明": "默认显示深度。-1 表示不限制（显示全部层级），0 表示仅显示根目录，2 表示只显示 2 层。右键菜单有快捷选项。",
    "__defaultFormat说明": "默认输出格式。\"text\" 为纯文本，\"markdown\" 为 Markdown 代码块格式。",
    "__showFileSize说明": "是否默认显示文件大小。true 显示，false 不显示。右键菜单有专门的「含大小」选项。",
    "__filterExt说明": "按后缀筛选文件的扩展名列表。用于右键菜单「仅指定后缀文件」功能。可自定义，例如只看图片就填 [\".png\", \".jpg\", \".svg\"]。",
}


def load_config() -> dict:
    """加载配置文件，返回有效配置字典。文件不存在或格式错误时静默返回默认值。"""
    config = dict(_DEFAULTS)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return config

    if not isinstance(user, dict):
        return config

    _merge(config, user, "excludeDirs", list)
    _merge(config, user, "excludeFiles", list)
    _merge(config, user, "maxFiles", int)
    _merge(config, user, "maxItemsPerLevel", int)
    _merge(config, user, "maxDepth", int)
    _merge(config, user, "defaultFormat", str)
    _merge(config, user, "showFileSize", bool)
    _merge(config, user, "filterExt", list)

    return config


def get_effective_config(cli_overrides: dict | None = None) -> dict:
    """合并：默认值 < 配置文件 < CLI 覆盖。返回最终配置。"""
    config = load_config()
    if cli_overrides:
        for key, value in cli_overrides.items():
            if value is not None:
                config[key] = value
    return config


def _merge(config: dict, user: dict, key: str, expected_type: type):
    if key not in user:
        return

    value = user[key]
    if expected_type is list:
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            config[key] = value
        return

    if expected_type is int:
        if isinstance(value, bool) or not isinstance(value, int):
            return
        if key in ("maxFiles", "maxDepth") and value < -1:
            return
        if key == "maxItemsPerLevel" and value < 1:
            return
        config[key] = value
        return

    if expected_type is bool:
        if isinstance(value, bool):
            config[key] = value
        return

    if expected_type is str:
        if isinstance(value, str):
            if key == "defaultFormat" and value not in ("text", "markdown"):
                return
            config[key] = value


def ensure_config_file() -> str:
    """确保配置文件存在（带详细注释），返回文件路径。"""
    if not os.path.isfile(CONFIG_FILE):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        doc = {}
        doc["__说明"] = _COMMENTS["__说明"]
        doc["excludeDirs"] = sorted(DEFAULT_EXCLUDE_DIRS)
        doc["__excludeDirs说明"] = _COMMENTS["__excludeDirs说明"]
        doc["excludeFiles"] = sorted(DEFAULT_EXCLUDE_FILES)
        doc["__excludeFiles说明"] = _COMMENTS["__excludeFiles说明"]
        doc["maxFiles"] = MAX_FILES
        doc["__maxFiles说明"] = _COMMENTS["__maxFiles说明"]
        doc["maxItemsPerLevel"] = MAX_ITEMS_PER_LEVEL
        doc["__maxItemsPerLevel说明"] = _COMMENTS["__maxItemsPerLevel说明"]
        doc["maxDepth"] = -1
        doc["__maxDepth说明"] = _COMMENTS["__maxDepth说明"]
        doc["defaultFormat"] = "text"
        doc["__defaultFormat说明"] = _COMMENTS["__defaultFormat说明"]
        doc["showFileSize"] = False
        doc["__showFileSize说明"] = _COMMENTS["__showFileSize说明"]
        doc["filterExt"] = sorted(SOURCE_CODE_EXTENSIONS)
        doc["__filterExt说明"] = _COMMENTS["__filterExt说明"]
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
    return CONFIG_FILE


def open_config_file() -> bool:
    """创建默认配置文件（如不存在）并用记事本打开。"""
    try:
        path = ensure_config_file()
        os.startfile(path)
        return True
    except OSError:
        return False
