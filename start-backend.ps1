# Start Backend with proper cleanup
# Usage: .\start-backend.ps1

Write-Host "Starting Azure Architect Assistant Backend..." -ForegroundColor Green

try {
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
    
    Write-Host "Starting uvicorn server on port $port..." -ForegroundColor Cyan
    Write-Host "Press CTRL+C to gracefully stop the server and pause running jobs" -ForegroundColor Yellow
    
    # Run uvicorn directly in this PowerShell session (not detached)
    # This allows CTRL-C to properly trigger FastAPI shutdown event
    & "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --port $port --app-dir backend
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    Write-Host "`nServer stopped." -ForegroundColor Green
}
