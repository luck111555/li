@echo off
wsl.exe -u root bash -lc "/mnt/d/APP/AI-Session-Viewer-main/sync-wsl-sessions.sh"
echo.
echo Sync finished. Press any key to close.
pause >nul
