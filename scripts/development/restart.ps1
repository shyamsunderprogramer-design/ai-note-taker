# AI Note Taker - PowerShell Reset Script
# Run this in PowerShell to clear cache and restart

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "AI Note Taker - Complete Reset and Restart" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Kill processes
Write-Host "[1/5] Stopping processes..." -ForegroundColor Yellow
Stop-Process -Name "electron" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# Step 2: Clear cache
Write-Host "[2/5] Clearing cache..." -ForegroundColor Yellow
$cachePaths = @(
    "$env:APPDATA\ai-note-taker-data\Cache",
    "$env:APPDATA\ai-note-taker-data\Code Cache",
    "$env:APPDATA\ai-note-taker-data\GPUCache",
    "$env:APPDATA\ai-note-taker-data\Service Worker"
)
foreach ($path in $cachePaths) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        Write-Host "  Cleared: $path"
    }
}

# Step 3: Clear temp files
Write-Host "[3/5] Cleaning temp files..." -ForegroundColor Yellow
$tempPaths = @("temp_audio", "backend\temp_audio", "electron\temp_audio")
foreach ($path in $tempPaths) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

# Step 4: Wait for port
Write-Host "[4/5] Checking port 8000..." -ForegroundColor Yellow
$portInUse = $true
while ($portInUse) {
    $connection = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($connection) {
        Write-Host "  Waiting for port 8000..."
        Start-Sleep -Seconds 1
    } else {
        $portInUse = $false
    }
}
Write-Host "  Port 8000 is free!" -ForegroundColor Green

# Step 5: Start app
Write-Host "[5/5] Starting AI Note Taker..." -ForegroundColor Green
Write-Host ""

# Change to electron directory and start
$electronPath = Join-Path $PSScriptRoot "electron"
if (Test-Path $electronPath) {
    Set-Location $electronPath
    Start-Process npm -ArgumentList "start" -WindowStyle Normal
} else {
    # Try from current location
    Set-Location "D:\Rep\ai-note-taker\electron"
    Start-Process npm -ArgumentList "start" -WindowStyle Normal
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "App is starting! Wait 5-10 seconds..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green

# Keep window open
Read-Host -Prompt "Press Enter to exit"
