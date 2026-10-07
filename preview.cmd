@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.cmd first.
    pause
    exit /b 1
)
echo This is a controller preview, without Webots. Ctrl+C stops it.
".venv\Scripts\python.exe" preview_controller.py
pause
