@echo off
echo ===========================================
echo AI NOTE TAKER - Backend Restart Script
echo ===========================================
echo.

cd /d D:\Rep\ai-note-taker\backend

echo [1/3] Checking Python...
python --version || (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

echo.
echo [2/3] Killing existing Python processes on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    echo Stopping PID %%a...
    taskkill /PID %%a /F 2>nul
)

echo.
echo [3/3] Starting backend...
echo.
echo ===========================================
python main.py
echo ===========================================
echo.

if %errorlevel% neq 0 (
    echo ERROR: Backend failed to start
    echo Check error messages above
    pause
    exit /b 1
)

pause
