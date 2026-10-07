@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 (
        echo Install Python 3.12 from python.org, then run this file again.
        pause
        exit /b 1
    )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed. Read the message above.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" configure_python.py
echo Setup finished. Run dashboard.cmd and webots.cmd.
pause
