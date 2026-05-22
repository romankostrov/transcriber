@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo ERROR: .venv not found. Run bootstrap_windows.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe app.py
