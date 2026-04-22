<div align="center">

# CopyTree

**一键复制文件目录树到剪贴板**

[![Windows](https://img.shields.io/badge/platform-Windows-blue)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.10+-green)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

右键任意文件夹 → 选择 CopyTree → 目录树已复制到剪贴板

</div>

---

## 功能特性

- **右键菜单集成** — 悬停 CopyTree 即展开二级子菜单，11 种常用操作一键完成，分组显示带分隔线
- **完整目录树** — 默认显示所有文件，可选过滤 `.git`、`node_modules` 等指定目录
- **多种输出格式** — 纯文本、Markdown 代码块
- **文件大小 & 修改时间** — 可选显示文件大小和最后修改日期
- **按后缀筛选** — 通过配置文件自定义文件扩展名过滤（默认 70+ 种源码扩展名）
- **深度限制** — 控制显示层级，如只看 2 层
- **保存到文件** — 导出为 `directory_tree.txt` 或 `directory_tree.md`
- **配置文件** — 支持自定义排除列表、后缀筛选、默认格式、显示限制等
- **双击即装** — 下载 exe 后双击自动注册右键菜单
- **零依赖** — 纯 Python + ctypes，不依赖任何第三方库
- **单文件** — PyInstaller 打包为一个 ~7 MB 的 exe，无需安装 Python

## 右键菜单

右键点击任意文件夹或文件夹内空白处，悬停 **CopyTree** 即可看到：

```
复制目录树
复制目录树（过滤指定目录）
复制目录树（含大小）
复制目录树（含修改时间）
复制目录树（仅指定后缀文件）
复制目录树（限2层）
─────────────────────
复制为 Markdown
复制为 Markdown（含大小）
─────────────────────
保存为 txt
保存为 Markdown
─────────────────────
打开配置文件
```

| 菜单项 | 说明 |
|--------|------|
| 复制目录树 | 显示所有文件和目录，不做过滤 |
| 复制目录树（过滤指定目录） | 过滤 `.git`、`node_modules` 等配置中指定的目录 |
| 复制目录树（含大小） | 附带文件大小 |
| 复制目录树（含修改时间） | 附带修改日期 |
| 复制目录树（仅指定后缀文件） | 只显示配置文件中 `filterExt` 指定后缀的文件 |
| 复制目录树（限2层） | 只显示 2 层深度 |
| 复制为 Markdown | Markdown 代码块格式 |
| 复制为 Markdown（含大小） | Markdown + 文件大小 |
| 保存为 txt | 保存到 `directory_tree.txt` |
| 保存为 Markdown | 保存到 `directory_tree.md` |
| 打开配置文件 | 编辑配置 |

## 输出示例

基本复制（不过滤）：

```
📁 my-project/
├── 📁 .git/
│   └── config
├── 📁 node_modules/
│   └── 📁 pkg/
│       └── index.js
├── 📁 src/
│   ├── main.py
│   └── 📁 utils/
│       ├── helper.js
│       └── style.css
├── image.png
└── package.json
```

过滤指定目录：

```
📁 my-project/
├── 📁 src/
│   ├── main.py
│   └── 📁 utils/
│       ├── helper.js
│       └── style.css
├── image.png
└── package.json
```

含大小和修改时间：

```
📁 CopyTree/
├── __init__.py (2026-04-22, 68 B)
├── __main__.py (2026-04-22, 5.2 KB)
├── clipboard.py (2026-04-22, 2.1 KB)
└── scanner.py (2026-04-22, 8.7 KB)
```

## 安装

### 方式一：下载 exe（推荐）

从 [Releases](../../releases) 下载 `CopyTree.exe`，放到任意位置，**双击运行**即可完成安装。

安装后右键菜单立即可用，同时会在开始菜单创建快捷方式。

### 方式二：从源码构建

需要 Python 3.10+ 和 PyInstaller：

```bash
git clone https://github.com/baoxinwen/CopyTree.git
cd CopyTree
pip install pyinstaller
python -m PyInstaller copytree.spec --noconfirm
```

构建产物在 `dist/CopyTree.exe`，双击运行安装。

## 卸载

在命令行运行：

```bash
CopyTree.exe --uninstall
```

会清除所有注册表项和开始菜单快捷方式，可放心删除 exe 文件。

## 命令行用法

CopyTree 也支持命令行直接调用：

```bash
# 基本用法（不过滤，显示全部）
CopyTree.exe "C:\path\to\folder"

# 过滤指定目录（隐藏 .git、node_modules 等）
CopyTree.exe "C:\path\to\folder" --filter

# 含文件大小
CopyTree.exe "C:\path\to\folder" --size

# 含修改时间
CopyTree.exe "C:\path\to\folder" --time

# Markdown 格式
CopyTree.exe "C:\path\to\folder" --format markdown

# 按配置文件中 filterExt 筛选
CopyTree.exe "C:\path\to\folder" --filter-ext

# 仅源码文件（内置 70+ 扩展名列表）
CopyTree.exe "C:\path\to\folder" --source-only

# 限制深度为 2 层
CopyTree.exe "C:\path\to\folder" --max-depth 2

# 保存到文件
CopyTree.exe "C:\path\to\folder" --save
CopyTree.exe "C:\path\to\folder" --save-md

# 额外排除指定目录/文件
CopyTree.exe "C:\path\to\folder" --exclude logs --exclude temp

# 安装 / 卸载 / 打开配置
CopyTree.exe --install
CopyTree.exe --uninstall
CopyTree.exe --config
CopyTree.exe --version
```

## 配置文件

首次使用「打开配置文件」时，会在 `%APPDATA%\CopyTree\copytree.json` 自动生成带注释的配置文件：

```json
{
  "__说明": "这是 CopyTree 的配置文件。修改后保存，下次使用右键菜单时生效。删除此文件可恢复默认设置。",
  "excludeDirs": [".git", "node_modules", "__pycache__", ...],
  "__excludeDirs说明": "要排除的目录名列表。精确匹配，大小写不敏感。",
  "excludeFiles": [".DS_Store", "Thumbs.db", "desktop.ini"],
  "__excludeFiles说明": "要排除的文件名列表。",
  "maxFiles": 2000,
  "__maxFiles说明": "最大显示文件总数。-1 表示不限制。",
  "maxItemsPerLevel": 200,
  "__maxItemsPerLevel说明": "同一层级最大显示项数。",
  "maxDepth": -1,
  "__maxDepth说明": "默认显示深度。-1 不限制，0 仅根目录，2 显示 2 层。",
  "defaultFormat": "text",
  "__defaultFormat说明": "默认输出格式：text 或 markdown。",
  "showFileSize": false,
  "__showFileSize说明": "是否默认显示文件大小。",
  "filterExt": [".py", ".js", ".ts", ".html", ".css", ...],
  "__filterExt说明": "按后缀筛选文件的扩展名列表。可自定义，例如只看图片就填 [\".png\", \".jpg\", \".svg\"]。"
}
```

## 项目结构

```
src/copytree/
├── __init__.py        # 版本号
├── __main__.py        # 入口：CLI 解析、模式分发
├── constants.py       # 常量：过滤列表、限制、UI 字符串
├── natural_sort.py    # 自然排序（file2 < file10）
├── config.py          # 配置文件加载与生成
├── scanner.py         # 目录扫描、过滤、树状文本生成
├── formatter.py       # 输出格式化（文本 / Markdown）
├── clipboard.py       # Win32 剪贴板操作
├── notify.py          # 系统气泡通知
├── shortcut.py        # 开始菜单快捷方式
└── registry.py        # 注册表右键菜单管理
```

## 技术细节

- **零外部依赖** — 全部使用 Python 标准库和 `ctypes`/`winreg` 直接调用 Win32 API
- **剪贴板** — `GlobalAlloc` → `GlobalLock` → `SetClipboardData`，64 位安全
- **通知** — `Shell_NotifyIconW` 气泡通知，后台线程 + 主线程等待确保显示
- **快捷方式** — COM 接口 `IShellLinkW` + `IPropertyStore`，设置 AppUserModelID
- **右键菜单** — `MUIVerb` + `SubCommands` 实现级联子菜单，`CommandFlags=0x20` 添加分隔线，注册在 `HKCU` 下无需管理员权限
- **目录扫描** — `os.scandir` 递归，自动识别 Junction/符号链接、长路径 `\\?\` 前缀、权限拒绝目录
- **打包** — PyInstaller `--noconsole`，通过 `AttachConsole(-1)` 在命令行模式下仍可输出

## 许可证

[MIT License](LICENSE)
