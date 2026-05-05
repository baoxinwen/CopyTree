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

- **右键菜单集成** — 13 种操作一键完成，分组显示
- **完整目录树** — 可选过滤 `.git`、`node_modules` 等目录
- **多种输出格式** — 纯文本、Markdown 代码块、Markdown 列表、JSON
- **文件信息** — 可选显示文件大小和修改时间
- **后缀/源码筛选** — 自定义扩展名过滤，源码模式识别 `Dockerfile`、`Makefile` 等
- **深度限制** — 控制显示层级
- **保存到文件** — 导出为 txt 或 Markdown
- **配置文件** — 自定义排除列表、默认格式、显示限制等
- **双击管理** — 双击 exe 即可安装、更新、修复或卸载
- **零依赖** — 纯 Python + ctypes

## 右键菜单

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
复制为 Markdown 列表
复制为 JSON
─────────────────────
保存为 txt
保存为 Markdown
─────────────────────
打开配置文件
```

## 输出示例

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

## 安装

### 下载 exe（推荐）

从 [Releases](../../releases) 下载 `CopyTree.exe`，**双击运行**即可完成安装。

安装后自动复制到 `%LOCALAPPDATA%\CopyTree\`，右键菜单指向该稳定路径。再次双击可更新或卸载。

### 从源码构建

```bash
git clone https://github.com/baoxinwen/CopyTree.git
cd CopyTree
pip install pyinstaller
python -m PyInstaller copytree.spec --noconfirm
```

产物在 `dist/CopyTree.exe` 和 `dist/CopyTreeCLI.exe`。

## 命令行用法

`CopyTreeCLI.exe` 用于脚本和重定向：

```bash
CopyTreeCLI.exe "C:\path\to\folder"                    # 基本用法
CopyTreeCLI.exe "C:\path\to\folder" --filter            # 过滤 .git 等
CopyTreeCLI.exe "C:\path\to\folder" --size               # 含文件大小
CopyTreeCLI.exe "C:\path\to\folder" --format json        # JSON 格式
CopyTreeCLI.exe "C:\path\to\folder" --max-depth 2        # 限 2 层
CopyTreeCLI.exe "C:\path\to\folder" --save               # 保存为 txt
CopyTreeCLI.exe "C:\path\to\folder" --no-clipboard       # 只输出不复制
CopyTreeCLI.exe --check-config                           # 检查配置
CopyTreeCLI.exe --version                                # 查看版本
```

## 配置文件

首次使用「打开配置文件」时自动生成 `%APPDATA%\CopyTree\copytree.json`：

```json
{
  "excludeDirs": [".git", "node_modules", "__pycache__"],
  "excludeFiles": [".DS_Store", "Thumbs.db"],
  "maxFiles": 2000,
  "maxItemsPerLevel": 200,
  "maxDepth": -1,
  "defaultFormat": "text",
  "showFileSize": false,
  "filterExt": [".py", ".js", ".ts", ".html", ".css"]
}
```

| 字段 | 范围 | 说明 |
|------|------|------|
| `maxFiles` | -1 ~ 1000000 | 最大文件数，-1 不限制 |
| `maxItemsPerLevel` | 1 ~ 10000 | 单层级最大项数 |
| `maxDepth` | -1 ~ 100 | 显示深度，-1 不限制 |

## 项目结构

```
src/copytree/
├── __init__.py        # 版本号
├── __main__.py        # 入口：CLI 解析、GUI/CLI 模式分发
├── winapi.py          # Win32 API ctypes 声明集中管理
├── constants.py       # 常量：过滤列表、限制、UI 字符串
├── natural_sort.py    # 自然排序（file2 < file10）
├── config.py          # 配置文件加载与生成
├── scanner.py         # 目录扫描、过滤、树状文本生成
├── formatter.py       # 输出格式化（文本 / Markdown / JSON）
├── clipboard.py       # Win32 剪贴板操作
├── notify.py          # 系统气泡通知
├── shortcut.py        # 开始菜单快捷方式（COM 接口）
└── registry.py        # 注册表右键菜单管理
```

## 许可证

[MIT License](LICENSE)
