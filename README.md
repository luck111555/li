# AI Session Viewer（Windows 发布版）

这个仓库是 `AI Session Viewer` 的 Windows 可执行发布目录，适合直接下载和运行。

## 1. 这个项目能做什么

`AI Session Viewer` 可以把你本地的 Claude / Codex 会话记录集中展示，方便查看、搜索和继续会话。

你可以把它理解成：

- 一个本地会话浏览器
- 不依赖云端存储
- 双击可运行（`ai-session-viewer.exe`）

## 2. 仓库文件说明（小白版）

- `ai-session-viewer.exe`：主程序，双击启动。
- `sync-wsl-sessions.cmd`：一键把 WSL 里的会话同步到 Windows 用户目录。
- `sync-wsl-sessions.sh`：上面 `.cmd` 调用的脚本（Linux shell 脚本）。
- `claude-wsl.cmd`：在 WSL 中启动 `claude` 的快捷方式。
- `INSTALL.md`：详细安装与使用教程。
- `PUBLISH_TO_GITHUB.md`：从零发布到 GitHub 的详细步骤。

## 3. 安装步骤（从零开始，每一步都写清楚）

### 第 1 步：确认你的电脑环境

你需要满足下面两条：

1. 电脑系统是 Windows。
2. 你至少用过一次 Claude Code 或 Codex CLI（本地要先有会话数据）。

### 第 2 步：下载项目文件

有两种方式：

1. 打开本项目 GitHub 页面，点击 `Code` -> `Download ZIP`，下载后解压。
2. 或者你已经拿到了项目目录，确保目录里有 `ai-session-viewer.exe`。

建议把项目放到固定目录，例如：`D:\APP\AI-Session-Viewer-main`。

### 第 3 步：启动主程序

1. 进入目录，找到 `ai-session-viewer.exe`。
2. 双击运行。
3. 如果 Windows 弹出安全提示，点击“更多信息” -> “仍要运行”。

看到程序主界面，说明安装完成。

### 第 4 步（重要）：同步 WSL 里的会话数据

如果你平时在 WSL 里使用 Claude/Codex，建议先同步一次数据，不然可能看不到历史会话。

操作如下：

1. 双击 `sync-wsl-sessions.cmd`。
2. 等待黑色窗口执行完成，看到 `Sync finished`。
3. 关闭窗口后，再打开 `ai-session-viewer.exe`。

说明：

1. 这个脚本会先备份 Windows 用户目录中的旧数据。
2. 再把 WSL 中的会话同步到 Windows 用户目录。

### 第 5 步：日常正确使用顺序

建议固定按这个顺序：

1. 在 Claude/Codex 里继续聊天（尤其是 WSL 环境）。
2. 聊完后运行一次 `sync-wsl-sessions.cmd`。
3. 打开 `ai-session-viewer.exe` 查看最新会话。

### 第 6 步：可选快捷方式

如果你想在 WSL 中直接启动 Claude，可双击 `claude-wsl.cmd`。

## 4. 常见问题（安装后最常见）

### Q1：打开程序后看不到任何会话

1. 先确认你确实使用过 Claude 或 Codex。
2. 如果你在 WSL 里使用，先执行 `sync-wsl-sessions.cmd`。
3. 重新打开 `ai-session-viewer.exe`。

### Q2：双击 `sync-wsl-sessions.cmd` 没反应

1. 确认 Windows 已安装并启用 WSL。
2. 确认 `wsl.exe` 在系统中可用。

### Q3：会不会上传聊天记录

不会。这个工具是本地读取器，读取本地文件，不需要把聊天内容上传到云端。

## 5. 如何把这个项目发布到 GitHub

请看 [`PUBLISH_TO_GITHUB.md`](./PUBLISH_TO_GITHUB.md)。

文档已经包含：

1. Git 和 GitHub 账号准备。
2. 在 GitHub 创建仓库。
3. 本地初始化、提交、推送命令（可直接复制）。
4. 常见报错处理（认证失败、远程已存在、推送被拒绝等）。
