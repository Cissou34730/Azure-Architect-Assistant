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
    # Activate virtual environment
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & ".\.venv\Scripts\Activate.ps1"
    
    # Change to backend directory
    Push-Location backend
    
    Write-Host "Starting uvicorn server on port 8000..." -ForegroundColor Cyan
    # Start uvicorn without reload for stability
    python -m uvicorn app.main:app --port 8000
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    Pop-Location
    Stop-BackendProcesses
}
