@echo off
echo ==========================================
echo AI Note Taker - Complete Reset and Restart
echo ==========================================
echo.

:: Step 1: Kill all Electron and Python processes
echo [1/5] Stopping all running processes...
taskkill /IM electron.exe /F 2>nul
taskkill /IM python.exe /F 2>nul
timeout /t 2 /nobreak >nul

:: Step 2: Clear Electron cache
echo [2/5] Clearing Electron cache...
if exist "%APPDATA%\ai-note-taker-data" (
    rmdir /s /q "%APPDATA%\ai-note-taker-data\Cache" 2>nul
    rmdir /s /q "%APPDATA%\ai-note-taker-data\Code Cache" 2>nul
    rmdir /s /q "%APPDATA%\ai-note-taker-data\GPUCache" 2>nul
    rmdir /s /q "%APPDATA%\ai-note-taker-data\Service Worker" 2>nul
    echo Cache cleared.
)

:: Step 3: Clear temp audio files
echo [3/5] Cleaning temp files...
if exist "temp_audio" rmdir /s /q temp_audio 2>nul
if exist "backend\temp_audio" rmdir /s /q backend\temp_audio 2>nul
if exist "electron\temp_audio" rmdir /s /q electron\temp_audio 2>nul
mkdir temp_audio 2>nul
mkdir backend\temp_audio 2>nul

:: Step 4: Wait for port to be free
echo [4/5] Checking port 8000...
:CHECK_PORT
netstat -ano | findstr :8000 >nul
if %errorlevel% equ 0 (
    echo Waiting for port 8000 to be free...
    timeout /t 1 /nobreak >nul
    goto CHECK_PORT
)
echo Port 8000 is free.

:: Step 5: Start the app
echo [5/5] Starting AI Note Taker...
echo.
cd electron
start "AI Note Taker" npm start

echo.
echo ==========================================
echo App is starting...
echo Wait 5-10 seconds for it to fully load.
echo ==========================================
pause
