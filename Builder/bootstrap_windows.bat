@echo off
setlocal
cd /d "%~dp0"

echo === Telem Transcriber v10 bootstrap ===
echo This script installs uv, Python 3.12, virtual environment, dependencies and local FFmpeg.
echo.

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo uv not found. Installing uv...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: uv was not installed or not found in PATH.
    echo Close this window, open a new cmd, and run this bat again.
    pause
    exit /b 1
)

echo Installing Python 3.12 via uv...
uv python install 3.12
if %errorlevel% neq 0 goto error

echo Creating .venv...
uv venv --python 3.12 .venv
if %errorlevel% neq 0 goto error

echo Installing dependencies...
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
if %errorlevel% neq 0 goto error

if not exist models mkdir models
if not exist bin mkdir bin
if not exist output mkdir output

echo Preparing local FFmpeg...
.venv\Scripts\python.exe scripts\download_ffmpeg.py
if %errorlevel% neq 0 goto error

echo.
echo Done. Next run prepare_models.bat, then run.bat
echo.
pause
exit /b 0

:error
echo.
echo ERROR: bootstrap failed.
pause
exit /b 1
