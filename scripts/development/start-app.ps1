# AI Note Taker - Complete Startup Script
# This starts both backend and Electron together

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AI Note Taker - Starting..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Kill any existing processes
Write-Host "[1/3] Stopping existing processes..." -ForegroundColor Yellow
Stop-Process -Name "electron" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Clear Electron cache to fix connection issues
Write-Host "[2/3] Clearing Electron cache..." -ForegroundColor Yellow
$cachePath = "$env:APPDATA\ai-note-taker-data"
if (Test-Path $cachePath) {
    Remove-Item -Path "$cachePath\Cache" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$cachePath\Code Cache" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$cachePath\GPUCache" -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path "$cachePath\Service Worker" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "  Cache cleared!" -ForegroundColor Green
}

# Check if port is free
$portInUse = $true
while ($portInUse) {
    $connection = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  Waiting for port 8000 to free..."
        Start-Sleep -Seconds 1
        Stop-Process -Id $connection.OwningProcess -Force -ErrorAction SilentlyContinue
    } else {
        $portInUse = $false
    }
}

# Start Backend
Write-Host "[3/3] Starting Backend..." -ForegroundColor Green
$backendPath = Join-Path $PSScriptRoot "backend"
$venvPython = Join-Path $PSScriptRoot "AINT_Venv\Scripts\python.exe"

$backendJob = Start-Job -ScriptBlock {
    param($path, $python)
    Set-Location $path
    & $python -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
} -ArgumentList $backendPath, $venvPython

# Wait for backend to be ready
Write-Host "  Waiting for backend (port 8000)..." -ForegroundColor Yellow
$retries = 0
$maxRetries = 30
$backendReady = $false

while ($retries -lt $maxRetries -and -not $backendReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "  Backend is ready!" -ForegroundColor Green
        }
    } catch {
        Start-Sleep -Milliseconds 500
        $retries++
    }
}

if (-not $backendReady) {
    Write-Host "  Backend failed to start!" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start Electron
Write-Host "  Starting Electron..." -ForegroundColor Green
$electronPath = Join-Path $PSScriptRoot "electron"
Set-Location $electronPath

# Start Electron in new window
Start-Process npm -ArgumentList "start" -WorkingDirectory $electronPath

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "AI Note Taker is running!" -ForegroundColor Green
Write-Host "Backend: http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Green

# Keep monitoring
while ($true) {
    Start-Sleep -Seconds 5
    $backendCheck = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if (-not $backendCheck) {
        Write-Host "Backend stopped!" -ForegroundColor Red
        break
    }
}
