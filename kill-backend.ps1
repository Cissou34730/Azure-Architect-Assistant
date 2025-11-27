# Kill all Python processes
# Usage: .\kill-backend.ps1

Write-Host "Killing all Python processes..." -ForegroundColor Yellow

# Kill all python processes
$pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue

if ($pythonProcesses) {
    $count = $pythonProcesses.Count
    $pythonProcesses | Stop-Process -Force
    Write-Host "Killed $count Python process(es)." -ForegroundColor Green
    Start-Sleep -Milliseconds 500
} else {
    Write-Host "No Python processes found." -ForegroundColor Cyan
}

# Double-check for any remaining python processes
$remaining = Get-Process -Name "python*" -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Force killing remaining processes..." -ForegroundColor Yellow
    $remaining | Stop-Process -Force -ErrorAction SilentlyContinue
}

Write-Host "Cleanup complete. Backend is stopped." -ForegroundColor Green
