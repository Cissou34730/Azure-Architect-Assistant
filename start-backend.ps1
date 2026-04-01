# Start Backend with proper cleanup
# Usage: .\start-backend.ps1

Write-Host "Starting Azure Architect Assistant Backend..." -ForegroundColor Green

$repoRoot = $PSScriptRoot
$backendAppDir = Join-Path $repoRoot "backend"

function Get-PortListener {
    param([int]$Port)

    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
}

function Get-ProcessCommandLine {
    param([int]$ProcessId)

    $processInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
    if ($null -eq $processInfo) {
        return ""
    }

    return [string]$processInfo.CommandLine
}

function Test-IsRepoBackendProcess {
    param(
        [int]$ProcessId,
        [string]$RepositoryRoot
    )

    $commandLine = Get-ProcessCommandLine -ProcessId $ProcessId
    if ([string]::IsNullOrWhiteSpace($commandLine)) {
        return $false
    }

    return $commandLine.Contains("uvicorn app.main:app") -and $commandLine.Contains($RepositoryRoot)
}

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

$existingListener = Get-PortListener -Port ([int]$port)
if ($null -ne $existingListener) {
    $existingPid = $existingListener.OwningProcess
    $existingProcess = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    $existingName = if ($null -ne $existingProcess) { $existingProcess.ProcessName } else { "<unknown>" }

    if (Test-IsRepoBackendProcess -ProcessId $existingPid -RepositoryRoot $repoRoot) {
        Write-Host "Found existing backend instance on port $port ($existingName, PID $existingPid). Restarting it first..." -ForegroundColor Yellow
        Stop-Process -Id $existingPid -Force -ErrorAction Stop
        Start-Sleep -Milliseconds 500
    } else {
        $existingCommandLine = Get-ProcessCommandLine -ProcessId $existingPid
        Write-Host "Port $port is already in use by $existingName (PID $existingPid)." -ForegroundColor Red
        if (-not [string]::IsNullOrWhiteSpace($existingCommandLine)) {
            Write-Host "Command line: $existingCommandLine" -ForegroundColor DarkYellow
        }
        Write-Host "Stop the existing process or change BACKEND_PORT before starting the backend." -ForegroundColor Red
        exit 1
    }

    $remainingListener = Get-PortListener -Port ([int]$port)
    if ($null -ne $remainingListener) {
        Write-Host "Port $port is still in use after attempting cleanup. Aborting startup." -ForegroundColor Red
        exit 1
    }
}

# Start uvicorn as a child process so we can track its PID
$proc = $null
$proc = Start-Process -FilePath "uv" `
    -ArgumentList "run", "python", "-m", "uvicorn", "app.main:app", "--port", $port, "--app-dir", $backendAppDir `
    -WorkingDirectory $repoRoot `
    -NoNewWindow -PassThru

try {
    # Wait for the process — Ctrl+C will break out of this
    $proc.WaitForExit()
}
finally {
    # Kill the uvicorn process tree if still running
    if ($null -ne $proc -and -not $proc.HasExited) {
        Write-Host "`nStopping backend (PID $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }

    # Also kill any orphaned child backend processes on the same port
    if ($null -ne $proc) {
        $portListeners = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
            Where-Object { $_.State -eq 'Listen' }
        foreach ($conn in $portListeners) {
            if (Test-IsRepoBackendProcess -ProcessId $conn.OwningProcess -RepositoryRoot $repoRoot) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    }

    Write-Host "Backend stopped." -ForegroundColor Green
}
