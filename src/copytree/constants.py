"""CopyTree 常量定义：默认过滤列表、限制、UI 字符串、注册表路径。"""

import os

# ── 版本 ──
VERSION = "1.0.0"

# ── AppUserModelID ──
APP_ID = "CopyTree.CopyTree"

# ── 默认过滤目录（大小写不敏感，精确匹配）──
DEFAULT_EXCLUDE_DIRS = frozenset({
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__",
    ".vs", ".vscode", ".idea",
    "dist", "build", "out", "bin", "obj",
    ".next", ".nuxt", ".cache",
    "vendor", "target", ".gradle",
})

# ── 默认过滤文件（大小写不敏感，精确匹配）──
DEFAULT_EXCLUDE_FILES = frozenset({
    ".DS_Store", "Thumbs.db", "desktop.ini",
})

# ── 限制 ──
MAX_FILES = 2000
MAX_ITEMS_PER_LEVEL = 200
MAX_NAME_LENGTH = 80

# ── 源码文件扩展名（用于「仅源码文件」菜单项）──
SOURCE_CODE_EXTENSIONS = frozenset({
    ".py", ".pyw",
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".java", ".kt", ".kts", ".scala",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hxx",
    ".cs", ".fs", ".vb",
    ".go", ".rs", ".swift", ".dart",
    ".rb", ".php", ".pl", ".r", ".R",
    ".lua", ".vim", ".el", ".clj", ".ex", ".exs",
    ".sql", ".sh", ".bash", ".zsh", ".fish", ".ps1",
    ".bat", ".cmd",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg",
    ".md", ".rst", ".txt", ".tex",
    ".cmake", ".makefile", ".dockerfile",
    ".proto", ".graphql", ".graphqls",
    ".wasm",
})

# ── 默认输出文件名 ──
DEFAULT_OUTPUT_FILENAME_TXT = "directory_tree.txt"
DEFAULT_OUTPUT_FILENAME_MD = "directory_tree.md"

# ── 树状符号 ──
BRANCH = "\u251C\u2500\u2500 "     # ├──
LAST = "\u2514\u2500\u2500 "       # └──
PIPE = "\u2502   "                  # │
SPACE = "    "                      #     (4 spaces)
FOLDER_PREFIX = "\U0001F4C1 "      # 📁
LOCK_PREFIX = "\U0001F512 "        # 🔒

# ── 文件属性（Windows）──
FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_SYSTEM = 0x4

# ── 注册表路径 ──
HKCU = "HKEY_CURRENT_USER"
REG_KEY_DIR = r"Software\Classes\Directory\shell\CopyTree"
REG_KEY_BG = r"Software\Classes\Directory\Background\shell\CopyTree"
REG_KEY_DIR_SIZE = r"Software\Classes\Directory\shell\CopyTree.WithSize"
REG_KEY_BG_SIZE = r"Software\Classes\Directory\Background\shell\CopyTree.WithSize"

# ── 快捷方式路径 ──
SHORTCUT_DIR = os.path.join(
    os.environ.get("APPDATA", ""),
    "Microsoft", "Windows", "Start Menu", "Programs",
)
SHORTCUT_NAME = "CopyTree.lnk"

# ── 配置文件路径 ──
CONFIG_DIR = os.path.join(os.environ.get("APPDATA", ""), "CopyTree")
CONFIG_FILE = os.path.join(CONFIG_DIR, "copytree.json")

# ── UI 字符串 ──
MSG_MENU_LABEL = "复制目录树"
MSG_MENU_LABEL_SIZE = "复制目录树（含大小）"
MSG_INSTALLED = "CopyTree 已就绪，右键文件夹即可使用"
MSG_UNINSTALLED = "CopyTree 已卸载"
MSG_NOTIFY_SUCCESS = "已复制目录树：{files} 个文件，{dirs} 个文件夹"
MSG_NOTIFY_SUCCESS_TRUNCATED = "已复制目录树：{files} 个文件，{dirs} 个文件夹（已截断，共 {total} 个文件）"
MSG_NOTIFY_FAIL = "复制失败：{error}"
MSG_NO_ACCESS = "无访问权限"
MSG_TRUNCATED_TAIL = "... 还有 {count} 个文件未显示（共 {total_files} 个文件，{total_dirs} 个文件夹）"
MSG_TRUNCATED_LEVEL = "(还有 {count} 项未显示)"
MSG_SIZE_UNKNOWN = "未知"
