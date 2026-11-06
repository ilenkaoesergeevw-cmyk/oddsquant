# LocalClaw 🦀 — 单机版本地智能体软件

一款像「单机版 OpenClaw」一样的本地软件：双击 EXE 即打开，把你的编程模型文件夹放进 `models/`，界面上一刷新就能在本机写代码、调试、操作文件；兼容 OpenClaw 的 `SKILL.md` 技能文件；支持聊天记忆、每个项目的经验记忆、聊天中查看截图和视频、一键定位文件路径、成果打包为 ZIP，并可控制 Word / PPT。

## 功能

- **模型文件夹即插即用**：把 `claude-code /`、`codex /`、`qwen-code /` 等文件夹放入 `models/`，点击「刷新模型」即可在界面选择使用。
- **聊天 + 记忆**：所有对话保存在本地 SQLite（`~/.localclaw/memory.db`），每个项目目录有独立的「项目记忆」（经验教训，自动注入到后续对话）。
- **技能兼容**：自动扫描 `skills/`、`~/.localclaw/skills/`、`~/.openclaw/skills/`，识别 OpenClaw 格式的 `SKILL.md`，可在界面勾选启用。
- **附件与截图**：聊天框支持上传图片/视频直接预览，一键截取当前屏幕加入对话。
- **文件路径可点击**：回复中的本机路径会变成可点击链接，点击即在资源管理器中打开并定位该文件。
- **打包 ZIP**：一键把任意目录打包为 zip（输出到 `~/.localclaw/outputs/`）并自动打开所在位置。
- **Office 控制**：通过 pywin32 控制 Word（新建/追加内容）与 PowerPoint（生成幻灯片），仅 Windows。
- **命令行工具**：内置安全命令行接口，危险命令（rm -rf、del /s、format 等）必须用户确认后才执行。

## 安全设计（请务必阅读）

- 服务只监听 `127.0.0.1`，任何外部网络/其他网站都无法访问；所有 API 需要本次启动生成的随机 token。
- 文件读写被限制在「允许访问的根目录」内（默认你的用户主目录），可在界面修改。
- 危险命令需要显式确认；敏感文件（.env、密钥）不会被主动输出。
- 技能文件本质是「给智能体的指令」，只安装你信任来源的技能，不要运行来历不明的 SKILL.md。
- 软件本身不向任何外部服务器发送数据，模型调用只发生在你本机运行的 CLI 工具中。

## 运行（开发模式）

```bash
pip install -r requirements.txt
python run.py            # 自动打开浏览器 http://127.0.0.1:8765/
python run.py --port 9000 --no-browser
```

首次运行会在 `~/.localclaw/` 生成配置（端口、token、允许目录等）。

## 打包成 EXE（Windows）

```bash
pip install pyinstaller
pyinstaller localclaw.spec --noconfirm
# 生成 dist/LocalClaw.exe，双击即用
```

也可以直接用仓库根目录的 GitHub Actions 工作流（`.github/workflows/localclaw-release.yml`）在云端构建：
在仓库页面 **Actions → Build LocalClaw Windows EXE → Run workflow** 手动触发，完成后可在该次运行的 Artifacts 下载 `LocalClaw.exe`；推送 `localclaw-v*` 标签会自动创建 Release。
下载地址形式为：`https://github.com/<你的用户名>/<仓库名>/releases`

## 使用方法

1. 把模型工具文件夹放入软件目录的 `models/`（见 `models/README.md`），各 CLI 的 API Key 按各自官方方式配置好。
2. 打开界面 → 「刷新模型」→ 选中模型 → 「＋ 新任务」开始聊天。
3. 在「项目目录」里填入你要开发的软件目录，之后该项目的记忆会自动保存和复用。
4. 需要截图/视频加入对话：点 📎 上传或 🖼 截图；需要打包：点 📦；需要 Word/PPT：点 📄。

## 目录结构

```
LocalClaw/
├── run.py                  # 入口
├── localclaw.spec          # PyInstaller 打包配置
├── requirements.txt
├── localclaw/
│   ├── config.py           # 配置与 token
│   ├── memory.py           # SQLite 聊天记忆 + 项目记忆
│   ├── agent.py            # 组装提示词并调用模型
│   ├── server.py           # 127.0.0.1 本地 HTTP 服务（token 鉴权）
│   ├── providers/          # 扫描 models/ + CLI 调用
│   ├── skills/loader.py    # OpenClaw SKILL.md 兼容加载
│   ├── tools/              # 文件 / 命令行 / 截图 / zip / Office
│   └── ui/                 # 聊天界面
├── skills/                 # 技能目录（SKILL.md）
├── models/                 # 放你的模型文件夹
└── tests/                  # 单元测试: python -m unittest discover -s tests
```
