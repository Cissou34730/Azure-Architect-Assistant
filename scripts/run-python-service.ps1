# Activate virtual environment and run Python service
$rootDir = Split-Path -Parent $PSCommandPath | Split-Path -Parent
$venvPython = Join-Path $rootDir ".venv\Scripts\python.exe"
$pythonServiceDir = Join-Path $rootDir "python-service"

Set-Location $pythonServiceDir
& $venvPython -m uvicorn app.main:app --reload --port 8000
