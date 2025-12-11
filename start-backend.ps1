# Start Backend with proper cleanup
# Usage: .\start-backend.ps1

Write-Host "Starting Azure Architect Assistant Backend..." -ForegroundColor Green

# Store the backend process ID globally
$Global:BackendPID = $null

# Function to cleanup backend process only
function Stop-BackendProcesses {
    Write-Host "`nCleaning up backend process..." -ForegroundColor Yellow
    
    if ($Global:BackendPID) {
        try {
            $process = Get-Process -Id $Global:BackendPID -ErrorAction SilentlyContinue
            if ($process) {
                Stop-Process -Id $Global:BackendPID -Force -ErrorAction Stop
                Write-Host "  Stopped backend process (PID $Global:BackendPID)" -ForegroundColor Green
            }
        } catch {
            Write-Host "  Backend process already stopped" -ForegroundColor DarkGray
        }
    } else {
        # Fallback: find uvicorn process by command line
        $uvicornProcs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | 
            Where-Object { $_.CommandLine -like "*uvicorn*app.main:app*" }
        
        if ($uvicornProcs) {
            $uvicornProcs | ForEach-Object {
                try {
                    Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
                    Write-Host "  Stopped backend process (PID $($_.ProcessId))" -ForegroundColor Green
                } catch {
                    Write-Host "  Could not stop PID $($_.ProcessId)" -ForegroundColor DarkGray
                }
            }
        }
    }
    
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
    
    # Start the backend process and capture its ID
    $process = Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\python.exe" `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--port", $port, "--app-dir", "backend" `
        -NoNewWindow -PassThru
    
    $Global:BackendPID = $process.Id
    Write-Host "Backend started with PID $($Global:BackendPID)" -ForegroundColor Green
    
    # Wait for the process to exit
    $process.WaitForExit()
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    Stop-BackendProcesses
}
