# Start Backend with proper cleanup
# Usage: .\start-backend.ps1

Write-Host "Starting Azure Architect Assistant Backend..." -ForegroundColor Green

# Function to cleanup Python processes
function Stop-BackendProcesses {
    Write-Host "`nCleaning up Python processes..." -ForegroundColor Yellow
    Get-Process -Name python* -ErrorAction SilentlyContinue | Stop-Process -Force
    Write-Host "Cleanup complete." -ForegroundColor Green
}

# Register cleanup on Ctrl+C
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action {
    Stop-BackendProcesses
}

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
    # Activate venv and run directly (much faster than uv run)
    & "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn app.main:app --port $port --app-dir backend 
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    Stop-BackendProcesses
}
