# models/ 目录说明

把你的本地模型/编程工具文件夹整个放到这个目录里，然后在软件界面点击“刷新模型”即可识别。

支持自动识别的文件夹命名（名称中包含以下关键词即可）：

- `claude-code`（含 `claude` 字样）：查找文件夹内的 `claude` / `claude.cmd` / `claude.exe`（也会查找 `bin/`、`node_modules/.bin/` 或系统 PATH）
- `codex`（ChatGPT Codex）：查找 `codex` / `codex.exe`
- `qwen-code`（含 `qwen` 字样）：查找 `qwen` / `qwen.cmd` / `qwen.exe`

其他自定义工具文件夹：只要文件夹里有 `.exe/.cmd/.bat/.sh` 可执行文件也会被识别为自定义模型。

注意：这些 CLI 工具本身的 API Key 需要你自己在各自的配置里设置好（例如 `claude login` 或环境变量），LocalClaw 只负责在本机调用它们。
