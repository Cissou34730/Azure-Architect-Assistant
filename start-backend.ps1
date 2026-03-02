# Start Backend with proper cleanup
# Usage: .\start-backend.ps1

Write-Host "Starting Azure Architect Assistant Backend..." -ForegroundColor Green

# Read port from .env file (default to 8000)
$port = "8000"
$envFile = Join-Path $PSScriptRoot ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile
    $portLine = $envContent | Where-Object { $_ -match "^BACKEND_PORT=(\d+)" }
    if ($portLine) {
        $port = $Matches[1]
    }
}

Write-Host "Starting uvicorn server on port $port via uv..." -ForegroundColor Cyan

# Start uvicorn as a child process so we can track its PID
$proc = Start-Process -FilePath "uv" `
    -ArgumentList "run", "uvicorn", "app.main:app", "--port", $port, "--app-dir", "backend" `
    -NoNewWindow -PassThru

try {
    # Wait for the process — Ctrl+C will break out of this
    $proc.WaitForExit()
}
finally {
    # Kill the uvicorn process tree if still running
    if (-not $proc.HasExited) {
        Write-Host "`nStopping backend (PID $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    # Also kill any orphaned child python processes on the same port
    $portListeners = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq 'Listen' }
    foreach ($conn in $portListeners) {
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
    }

    Write-Host "Backend stopped." -ForegroundColor Green
}
