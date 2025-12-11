# Kill backend process only (by port)
# Usage: .\kill-backend.ps1

Write-Host "Killing backend process..." -ForegroundColor Yellow

# Read port from .env file (default to 8000)
$port = 8000
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    $portLine = $envContent | Where-Object { $_ -match "^BACKEND_PORT=(\d+)" }
    if ($portLine) {
        $port = [int]$Matches[1]
    }
}

Write-Host "Looking for process listening on port $port..." -ForegroundColor Cyan

# Find process listening on the backend port
$connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue

if ($connection) {
    $pid = $connection.OwningProcess
    $processName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
    
    try {
        Stop-Process -Id $pid -Force -ErrorAction Stop
        Write-Host "  Killed backend process: $processName (PID $pid)" -ForegroundColor Green
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Host "  Could not kill PID $pid: $_" -ForegroundColor Red
    }
} else {
    Write-Host "No process found listening on port $port." -ForegroundColor Cyan
}

# Double-check
$remaining = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Force killing remaining process..." -ForegroundColor Yellow
    $remainingPid = $remaining.OwningProcess
    Stop-Process -Id $remainingPid -Force -ErrorAction SilentlyContinue
}

Write-Host "Cleanup complete. Backend is stopped." -ForegroundColor Green
