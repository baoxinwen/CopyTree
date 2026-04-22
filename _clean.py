"""删除所有 GitHub releases + 重建 git 历史 + 创建新 release"""
import requests, json, subprocess, os, sys, base64

# 获取 token
result = subprocess.run(
    ["git", "credential", "fill"],
    input=b"protocol=https\nhost=github.com\n",
    capture_output=True
)
lines = result.stdout.decode().strip().split("\n")
token = None
for line in lines:
    if line.startswith("password="):
        token = line.split("=", 1)[1]
        break
if not token:
    print("ERROR: cannot get token")
    sys.exit(1)

headers = {"Authorization": f"token {token}"}
repo = "baoxinwen/CopyTree"
api = f"https://api.github.com/repos/{repo}"

# 1. 删除所有 releases
print("Deleting releases...")
r = requests.get(f"{api}/releases", headers=headers)
for rel in r.json():
    rid = rel["id"]
    tag = rel["tag_name"]
    requests.delete(f"{api}/releases/{rid}", headers=headers)
    # 删除对应 tag
    requests.delete(f"{api}/git/refs/tags/{tag}", headers=headers)
    print(f"  Deleted: {tag}")

# 2. 重建 git 历史（orphan commit）
print("Rebuilding git history...")
subprocess.run(["git", "checkout", "--orphan", "temp_branch"], capture_output=True)
subprocess.run(["git", "add", "-A"], capture_output=True)
subprocess.run(["git", "commit", "-m", "CopyTree v1.0.0"], capture_output=True)
subprocess.run(["git", "branch", "-D", "main"], capture_output=True)
subprocess.run(["git", "branch", "-m", "main"], capture_output=True)
subprocess.run(["git", "push", "--force", "origin", "main"], capture_output=True)
print("  Git history reset")

# 3. 创建新 release + 上传 exe
print("Creating new release...")
r = requests.post(f"{api}/releases", headers=headers, json={
    "tag_name": "v1.0.0",
    "target_commitish": "main",
    "name": "CopyTree v1.0.0",
    "body": """## CopyTree v1.0.0

Windows 右键菜单工具，右键文件夹即可复制目录树到剪贴板。

### 使用方法

1. 下载 `CopyTree.exe`，放到任意位置
2. 双击运行，自动注册右键菜单
3. 右键任意文件夹 → 悬停 **CopyTree** → 选择操作

### 功能

- 11 种右键菜单操作（分组显示，带分隔线）
- 复制目录树（默认不过滤）/ 过滤指定目录 / 含大小 / 含修改时间
- 复制为 Markdown（含大小）
- 按后缀筛选文件（可自定义）
- 限制显示深度（限2层）
- 保存为 txt / Markdown 文件
- 可自定义配置文件
- 单文件约 7 MB，零依赖，无需管理员权限

### 卸载

命令行运行：`CopyTree.exe --uninstall`""",
    "draft": False,
    "prerelease": False,
})
release = r.json()
upload_url = release["upload_url"].split("{")[0]
print(f"  Release created: {release['html_url']}")

# 上传 exe
exe_path = r"D:\Program Data\Projects\tools\CopyTree\dist\CopyTree.exe"
with open(exe_path, "rb") as f:
    exe_data = f.read()
r = requests.post(
    upload_url,
    headers={**headers, "Content-Type": "application/octet-stream"},
    params={"name": "CopyTree.exe"},
    data=exe_data,
)
print(f"  Upload: {'OK' if r.status_code == 201 else 'FAILED ' + str(r.status_code)}")
print(f"\nDownload: https://github.com/{repo}/releases/download/v1.0.0/CopyTree.exe")
