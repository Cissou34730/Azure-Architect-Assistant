# Quick Setup Guide - CAF Pause/Resume Tests

## Step 1: Install Test Dependencies (Optional)

The standalone test works without pytest. Install pytest only if you want the full test suite.

### Choose one method:

**Method 1: PowerShell Script (Easiest for Windows)**
```powershell
cd backend
.\install_test_deps.ps1
```

**Method 2: Bash Script (Linux/Mac)**
```bash
cd backend
./install_test_deps.sh
```

**Method 3: Python Runner**
```bash
cd backend
python run_caf_tests.py --install
```

**Method 4: Direct pip**
```bash
pip install pytest pytest-asyncio
```

**Method 5: Requirements file**
```bash
pip install -r requirements.txt
```

## Step 2: Run Tests

### Option A: Standalone Test (No pytest needed)
```bash
cd backend
python test_caf_pause_resume.py
```
**Best for**: Quick validation, debugging, detailed output

### Option B: Pytest Suite (Requires pytest)
```bash
cd backend
pytest app/ingestion/tests/test_caf_integration.py -v -s
```
**Best for**: CI/CD, automated testing, comprehensive coverage

### Option C: Test Runner
```bash
cd backend
python run_caf_tests.py              # Standalone
python run_caf_tests.py --pytest     # Pytest suite
python run_caf_tests.py --all        # Both
```
**Best for**: Convenience, exploring options

## Step 3: Verify Installation

```bash
cd backend
python validate_tests.py
```

Expected output:
```
✓ Standalone test (test_caf_pause_resume.py):
  - Test methods: 3
✓ pytest is installed
✓ Pytest integration tests (test_caf_integration.py):
  - Test functions: 6
✓ Required imports available
```

## Troubleshooting

### "pytest not installed"
→ Run any install method from Step 1

### "ModuleNotFoundError: No module named 'pytest'"
→ Ensure virtual environment is activated
→ Run: `pip install pytest pytest-asyncio`

### "No module named 'app'"
→ Must run from `backend/` directory
→ Check: `cd backend` then run test

### Tests hang
→ Normal for website crawling (CAF is large)
→ Press `Ctrl+C` to cancel if needed

## What Gets Tested

✅ Start CAF ingestion  
✅ Pause during processing  
✅ Save state to disk  
✅ Resume from checkpoint  
✅ Multiple pause/resume cycles  
✅ Data integrity (no data loss)  
✅ Edge cases (pause without job, resume without checkpoint)  
✅ State transitions validation  

## Files Overview

```
backend/
├── test_caf_pause_resume.py           # ← Run this (no pytest needed)
├── run_caf_tests.py                   # Test runner with options
├── validate_tests.py                  # Check installation
├── install_test_deps.ps1              # Windows installer
├── install_test_deps.sh               # Linux/Mac installer
├── requirements.txt                   # Includes pytest now
├── CAF_TESTS_README.md                # Full documentation
├── CAF_TESTS_SUMMARY.md               # Quick reference
└── app/ingestion/tests/
    └── test_caf_integration.py        # Pytest suite (requires pytest)
```

## Quick Command Reference

| Task | Command |
|------|---------|
| Install pytest | `.\install_test_deps.ps1` or `python run_caf_tests.py --install` |
| Run standalone | `python test_caf_pause_resume.py` |
| Run pytest suite | `pytest app/ingestion/tests/test_caf_integration.py -v -s` |
| Run specific test | `python run_caf_tests.py --test test_caf_pause_resume_workflow` |
| Validate setup | `python validate_tests.py` |
| Show help | `python run_caf_tests.py --help` |

## Success Indicators

When tests pass, you'll see:
```
============================================================
ALL TESTS PASSED ✓
============================================================
```

The test validates:
- Ingestion starts for CAF
- Pause works during processing
- State persists with metrics
- Resume continues from checkpoint
- No data is lost
- Multiple cycles work correctly

---

**Ready to test!** Start with: `python test_caf_pause_resume.py`
