# 安装与使用教程（小白版）

本文目标：让你不懂代码也能把 `AI Session Viewer` 用起来。

## 1. 安装前准备

你只需要满足下面 2 条：

1. 电脑是 Windows。
2. 你至少用过一次 Claude Code 或 Codex CLI（这样本地才会有会话记录可读取）。

## 2. 下载文件

你有两种方式：

1. 从 GitHub 下载整个仓库 ZIP，然后解压。
2. 直接拿到 `ai-session-viewer.exe` 这个文件。

建议：把文件放在一个固定目录，例如 `D:\APP\AI-Session-Viewer-main`。

## 3. 启动程序

1. 双击 `ai-session-viewer.exe`。
2. 首次启动可能会被 Windows 安全提示拦截，点击“更多信息” -> “仍要运行”。

如果程序能打开主界面，说明安装成功。

## 4. 如果你在 WSL 里用过 Claude/Codex（重要）

很多人会遇到“程序打开了但看不到会话”的问题，原因通常是会话在 WSL 里，不在 Windows 用户目录。

解决步骤：

1. 双击 `sync-wsl-sessions.cmd`。
2. 等待终端窗口提示 `Sync finished`。
3. 再打开 `ai-session-viewer.exe`。

这个脚本会把 WSL 中的会话数据同步到 Windows 用户目录，并自动先做备份。

## 5. 日常使用建议

1. 每次在 WSL 里新聊了很多内容后，先运行一次 `sync-wsl-sessions.cmd`。
2. 再打开 `ai-session-viewer.exe` 看最新会话。
3. 如果你想在 WSL 里直接启动 Claude，可用 `claude-wsl.cmd`。

## 6. 常见问题

### Q1：打开程序后没有任何会话

1. 先确认你真的用过 Claude/Codex。
2. 如果是在 WSL 里用的，先执行 `sync-wsl-sessions.cmd`。
3. 关闭程序并重新打开。

### Q2：双击 `sync-wsl-sessions.cmd` 没反应

1. 确认电脑已安装并可用 WSL。
2. 脚本依赖 `wsl.exe`，需要在 Windows 环境可执行。

### Q3：会不会上传我的聊天内容？

这个项目是本地查看器，读取本地文件，不需要把会话上传到云端。
