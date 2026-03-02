@echo off
REM Start Claude inside WSL so new sessions carry WSL cwd paths.
/mnt/c/Windows/System32/wsl.exe -d Ubuntu-24.04 --cd /mnt/d -- bash -lc "claude"
