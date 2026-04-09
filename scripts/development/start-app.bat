@echo off
chcp 65001 >nul
echo ==========================================
echo AI Note Taker - Starting Fresh
echo ==========================================
echo.

:: Kill existing processes
echo [1/4] Stopping existing processes...
taskkill /F /IM electron.exe 2>nul
taskkill /F /IM python.exe 2>nul
timeout /t 2 /nobreak >nul

:: Clear cache
echo [2/4] Clearing cache...
if exist "%LOCALAPPDATA%\ai-note-taker-data" (
    rd /s /q "%LOCALAPPDATA%\ai-note-taker-data\Cache" 2>nul
    rd /s /q "%LOCALAPPDATA%\ai-note-taker-data\Code Cache" 2>nul
    rd /s /q "%LOCALAPPDATA%\ai-note-taker-data\GPUCache" 2>nul
    echo Cache cleared.
)

:: Clear temp
echo [3/4] Cleaning temp files...
if exist "temp_audio" rd /s /q temp_audio 2>nul
if exist "backend\temp_audio" rd /s /q "backend\temp_audio" 2>nul
mkdir temp_audio 2>nul
mkdir backend\temp_audio 2>nul

:: Wait for port
echo [4/4] Checking port 8000...
:CHECKPORT
netstat -an | findstr "127.0.0.1:8000" >nul
if %errorlevel% equ 0 (
    echo Waiting for port to free...
    timeout /t 1 /nobreak >nul
    goto CHECKPORT
)

echo.
echo ==========================================
echo Starting Backend and Electron...
echo ==========================================
echo.

:: Start backend in background
cd /d "%~dp0backend"
start /B "Backend" "%~dp0AINT_Venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info

:: Wait for backend
echo Waiting for backend to start...
:WAITBACKEND
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/health >nul
if %errorlevel% neq 0 goto WAITBACKEND
echo Backend is ready!

:: Start Electron
cd /d "%~dp0electron"
start "AI Note Taker" npm start

echo.
echo App is starting! Wait 5 seconds...
timeout /t 5 /nobreak >nul
exit
