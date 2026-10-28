@echo off
rem Run Heal-Jimaku from source (no packaging needed).
rem Double-click this file. Logs stay visible in this window.
chcp 65001 >nul
cd /d "%~dp0"

if not exist "src\main.py" (
  echo [ERROR] src\main.py not found - put this file in the project root.
  pause
  exit /b 1
)

python "src\main.py"

if errorlevel 1 (
  echo.
  echo [ERROR] App exited with code %errorlevel% - messages above.
  pause
)
