@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Run setup.cmd first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" configure_python.py
set "AIRPORT_WEBOTS=%LOCALAPPDATA%\Programs\Webots\msys64\mingw64\bin\webotsw.exe"
if not exist "%AIRPORT_WEBOTS%" set "AIRPORT_WEBOTS=%ProgramFiles%\Webots\msys64\mingw64\bin\webotsw.exe"
if not exist "%AIRPORT_WEBOTS%" (
    echo Open worlds\airport.wbt in your installed Webots application.
    pause
    exit /b 1
)
start "" "%AIRPORT_WEBOTS%" --mode=pause "%~dp0worlds\airport.wbt"
