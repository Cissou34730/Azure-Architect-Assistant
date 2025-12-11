# Kill backend process only (not all Python)
# Usage: .\kill-backend.ps1

Write-Host "Killing backend process..." -ForegroundColor Yellow

# Find uvicorn backend process by command line
$backendProcesses = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | 
    Where-Object { $_.CommandLine -like "*uvicorn*app.main:app*" }

if ($backendProcesses) {
    $count = 0
    $backendProcesses | ForEach-Object {
        try {
            Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop
            Write-Host "  Killed backend process (PID $($_.ProcessId))" -ForegroundColor Green
            $count++
        } catch {
            Write-Host "  Could not kill PID $($_.ProcessId): $_" -ForegroundColor Red
        }
    }
    
    if ($count -gt 0) {
        Write-Host "Killed $count backend process(es)." -ForegroundColor Green
        Start-Sleep -Milliseconds 500
    }
} else {
    Write-Host "No backend process found." -ForegroundColor Cyan
}

# Double-check for any remaining backend processes
$remaining = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | 
    Where-Object { $_.CommandLine -like "*uvicorn*app.main:app*" }

if ($remaining) {
    Write-Host "Force killing remaining backend processes..." -ForegroundColor Yellow
    $remaining | ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Cleanup complete. Backend is stopped." -ForegroundColor Green
