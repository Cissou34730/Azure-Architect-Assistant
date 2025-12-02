#!/bin/bash
# Install Test Dependencies
# Run this script to install pytest and pytest-asyncio for running the test suite

echo ""
echo "============================================================"
echo "Installing Test Dependencies for CAF Pause/Resume Tests"
echo "============================================================"
echo ""

# Check if virtual environment is activated
if [ -n "$VIRTUAL_ENV" ]; then
    echo "✓ Virtual environment detected: $VIRTUAL_ENV"
    echo ""
else
    echo "⚠ Warning: No virtual environment detected"
    echo "  Consider activating your virtual environment first"
    echo ""
fi

echo "Installing pytest and pytest-asyncio..."
echo ""

# Install pytest and pytest-asyncio
python -m pip install pytest pytest-asyncio

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✓ Test dependencies installed successfully!"
    echo "============================================================"
    echo ""
    
    echo "Installed packages:"
    echo "  • pytest"
    echo "  • pytest-asyncio"
    echo ""
    
    echo "You can now run:"
    echo "  python test_caf_pause_resume.py                    (standalone)"
    echo "  pytest app/ingestion/tests/test_caf_integration.py (pytest suite)"
    echo "  python run_caf_tests.py --pytest                   (with runner)"
    echo ""
    
else
    echo ""
    echo "============================================================"
    echo "✗ Failed to install test dependencies"
    echo "============================================================"
    echo ""
    
    echo "Try manually:"
    echo "  pip install pytest pytest-asyncio"
    echo ""
fi
