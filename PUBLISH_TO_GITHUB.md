# 发布到 GitHub 教程（从零开始，小白可用）

本文按最常见的 Windows 流程写。只要照着做，就能把当前目录发布到 GitHub。

目标目录：`D:\APP\AI-Session-Viewer-main`

## 1. 先准备 2 个东西

1. GitHub 账号（没有就先注册）。
2. Git 客户端（下载地址：<https://git-scm.com/download/win>）。

安装 Git 时一路下一步即可，默认选项就可以。

## 2. 在 GitHub 网站创建一个空仓库

1. 登录 GitHub。
2. 右上角 `+` -> `New repository`。
3. 仓库名填：`AI-Session-Viewer-main`（也可以自定义）。
4. 选择 `Public` 或 `Private`。
5. 不要勾选 `Add a README file`（因为本地已经有文件）。
6. 点击 `Create repository`。

创建完成后，GitHub 会显示一段“push an existing repository from the command line”的命令。

## 3. 在本地初始化并提交

先进入项目目录：

```bash
cd /d/APP/AI-Session-Viewer-main
```

如果你使用的是 PowerShell，也可以写成：

```powershell
Set-Location "D:\APP\AI-Session-Viewer-main"
```

然后执行初始化与提交命令：

```bash
git init
git branch -M main
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
git add .
git commit -m "chore: initial publish package"
```

## 4. 绑定远程仓库并推送

把下面命令里的 `你的用户名` 改成你的 GitHub 用户名：

```bash
git remote add origin https://github.com/你的用户名/AI-Session-Viewer-main.git
git push -u origin main
```

第一次推送会要求登录。按提示使用浏览器授权即可。

## 5. 以后更新项目怎么推送

每次修改后，执行 3 条命令：

```bash
git add .
git commit -m "feat: 你的更新说明"
git push
```

## 6. 推荐再做一步：发布 Release（给用户下载）

1. 打开你的 GitHub 仓库页面。
2. 进入 `Releases` -> `Draft a new release`。
3. 标签填 `v1.0.0`（示例）。
4. 上传 `ai-session-viewer.exe`。
5. 写版本说明后点击 `Publish release`。

用户就可以在 `Releases` 页面直接下载。

## 7. 常见报错与解决

### 报错 1：`remote origin already exists`

说明你之前已经绑定过远程。执行：

```bash
git remote -v
git remote remove origin
git remote add origin https://github.com/你的用户名/AI-Session-Viewer-main.git
```

### 报错 2：`failed to push some refs`

常见原因是远程比本地多一个初始提交（比如你在 GitHub 勾选了自动创建 README）。

处理方式（保留远程内容并合并）：

```bash
git pull origin main --allow-unrelated-histories
git push -u origin main
```

### 报错 3：认证失败（Authentication failed）

1. 确认你登录的是正确 GitHub 账号。
2. 建议使用 Git for Windows 自带的浏览器登录流程（Git Credential Manager）。
3. 如果你在公司网络，先确认能访问 `github.com`。

## 8. 一次性可复制命令（只需改用户名）

```bash
cd /d/APP/AI-Session-Viewer-main
git init
git branch -M main
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
git add .
git commit -m "chore: initial publish package"
git remote add origin https://github.com/你的用户名/AI-Session-Viewer-main.git
git push -u origin main
```
