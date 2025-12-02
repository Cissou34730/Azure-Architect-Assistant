# Install Test Dependencies
# Run this script to install pytest and pytest-asyncio for running the test suite

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Installing Test Dependencies for CAF Pause/Resume Tests" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

# Check if virtual environment is activated
if ($env:VIRTUAL_ENV) {
    Write-Host "✓ Virtual environment detected: $env:VIRTUAL_ENV`n" -ForegroundColor Green
} else {
    Write-Host "⚠ Warning: No virtual environment detected" -ForegroundColor Yellow
    Write-Host "  Consider activating your virtual environment first`n" -ForegroundColor Yellow
}

Write-Host "Installing pytest and pytest-asyncio...`n" -ForegroundColor White

# Install pytest and pytest-asyncio
python -m pip install pytest pytest-asyncio

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Host "✓ Test dependencies installed successfully!" -ForegroundColor Green
    Write-Host "============================================================`n" -ForegroundColor Green
    
    Write-Host "Installed packages:" -ForegroundColor White
    Write-Host "  • pytest" -ForegroundColor Gray
    Write-Host "  • pytest-asyncio`n" -ForegroundColor Gray
    
    Write-Host "You can now run:" -ForegroundColor White
    Write-Host "  python test_caf_pause_resume.py                    (standalone)" -ForegroundColor Cyan
    Write-Host "  pytest app/ingestion/tests/test_caf_integration.py (pytest suite)" -ForegroundColor Cyan
    Write-Host "  python run_caf_tests.py --pytest                   (with runner)`n" -ForegroundColor Cyan
    
} else {
    Write-Host "`n============================================================" -ForegroundColor Red
    Write-Host "✗ Failed to install test dependencies" -ForegroundColor Red
    Write-Host "============================================================`n" -ForegroundColor Red
    
    Write-Host "Try manually:" -ForegroundColor White
    Write-Host "  pip install pytest pytest-asyncio`n" -ForegroundColor Cyan
}

Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
