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

## 3. 普通用户如何安装和使用

请直接看 [`INSTALL.md`](./INSTALL.md)，里面按“从零开始”的顺序写了每一步。

最短路径是：

1. 下载本仓库（或直接拿到 `ai-session-viewer.exe`）。
2. 双击 `ai-session-viewer.exe`。
3. 如果你在 WSL 里使用过 Claude/Codex，先双击 `sync-wsl-sessions.cmd` 再打开程序。

## 4. 如何把这个项目发布到 GitHub

请看 [`PUBLISH_TO_GITHUB.md`](./PUBLISH_TO_GITHUB.md)。

文档已经包含：

1. Git 和 GitHub 账号准备。
2. 在 GitHub 创建仓库。
3. 本地初始化、提交、推送命令（可直接复制）。
4. 常见报错处理（认证失败、远程已存在、推送被拒绝等）。
