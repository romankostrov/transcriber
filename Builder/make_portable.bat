@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo ERROR: .venv not found. Run bootstrap_windows.bat first.
  pause
  exit /b 1
)

echo Building exe with PyInstaller...
.venv\Scripts\python.exe -m PyInstaller --noconfirm --onefile --windowed --name TelemTranscriber app.py
if %errorlevel% neq 0 goto error

set PORTABLE=portable\TelemTranscriber
if exist portable rmdir /s /q portable
mkdir "%PORTABLE%"
mkdir "%PORTABLE%\bin"
mkdir "%PORTABLE%\models"
mkdir "%PORTABLE%\output"

copy dist\TelemTranscriber.exe "%PORTABLE%\TelemTranscriber.exe" >nul
if exist bin\ffmpeg.exe copy bin\ffmpeg.exe "%PORTABLE%\bin\ffmpeg.exe" >nul
if exist bin\ffprobe.exe copy bin\ffprobe.exe "%PORTABLE%\bin\ffprobe.exe" >nul
xcopy models "%PORTABLE%\models" /E /I /Y >nul
copy README.md "%PORTABLE%\README.md" >nul

echo.
echo Portable build ready: %PORTABLE%
echo Copy the whole folder to USB drive.
echo.
pause
exit /b 0

:error
echo ERROR: portable build failed.
pause
exit /b 1
