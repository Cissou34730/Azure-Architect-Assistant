# CAF Pause/Resume Tests

Comprehensive tests to validate pause/resume functionality for the Azure Cloud Adoption Framework (CAF) knowledge base ingestion.

## Quick Start

### Install Test Dependencies (Optional - for pytest)

**Option 1: Use install script (easiest)**
```bash
# Windows PowerShell
.\install_test_deps.ps1

# Linux/Mac
./install_test_deps.sh
```

**Option 2: Using pip directly**
```bash
pip install pytest pytest-asyncio
```

**Option 3: Using requirements.txt**
```bash
pip install -r requirements.txt
```

**Option 4: Using test runner**
```bash
python run_caf_tests.py --install
```

> **Note**: The standalone test (`test_caf_pause_resume.py`) works without pytest. Install pytest only if you want to run the full pytest suite.

## Test Files

### 1. `test_caf_pause_resume.py` (Standalone)
Standalone integration test that can be run directly without pytest.

**Features:**
- Complete pause/resume workflow validation
- Multiple pause/resume cycles
- Data integrity verification
- Detailed console output with progress tracking

**Run:**
```bash
cd backend
python test_caf_pause_resume.py
```

### 2. `test_caf_integration.py` (Pytest Suite)
Pytest-based integration tests for CI/CD integration.

**Features:**
- All workflow tests from standalone version
- Additional edge case tests (pause without job, resume without checkpoint)
- State transition validation
- Proper test fixtures and cleanup

**Run all tests:**
```bash
cd backend
pytest app/ingestion/tests/test_caf_integration.py -v -s
```

**Run specific test:**
```bash
cd backend
pytest app/ingestion/tests/test_caf_integration.py::test_caf_pause_resume_workflow -v -s
```

### 3. `run_caf_tests.py` (Test Runner)
Convenience script to run tests with different options.

**Usage:**
```bash
cd backend

# Run standalone test
python run_caf_tests.py

# Run pytest suite
python run_caf_tests.py --pytest

# Run all tests
python run_caf_tests.py --all

# Run specific pytest test
python run_caf_tests.py --test test_caf_pause_resume_workflow

# Show help
python run_caf_tests.py --help
```

## Test Coverage

### Core Functionality Tests

#### 1. **Pause/Resume Workflow** (`test_caf_pause_resume_workflow`)
Tests the complete lifecycle:
1. Start ingestion for CAF KB
2. Wait for progress (documents/chunks processed)
3. Pause the ingestion job
4. Verify state is persisted to disk
5. Resume from checkpoint
6. Continue processing
7. Monitor completion

**Validates:**
- ✓ Job starts successfully
- ✓ Job transitions to RUNNING state
- ✓ Pause operation succeeds
- ✓ Job transitions to PAUSED state
- ✓ State persists to disk with metrics
- ✓ Resume operation succeeds
- ✓ Job transitions back to RUNNING state
- ✓ Processing continues from checkpoint

#### 2. **Multiple Cycles** (`test_caf_multiple_pause_resume_cycles`)
Tests 3 consecutive pause/resume cycles.

**Validates:**
- ✓ Multiple pause operations work
- ✓ Multiple resume operations work
- ✓ State transitions remain valid across cycles
- ✓ No corruption after repeated operations

#### 3. **Data Integrity** (`test_caf_data_integrity_during_pause_resume`)
Verifies data consistency during pause/resume.

**Validates:**
- ✓ Document count doesn't decrease after resume
- ✓ Chunk count doesn't decrease after resume
- ✓ Persisted state matches pre-pause state
- ✓ No data loss during pause/resume
- ✓ Metrics remain consistent

### Edge Case Tests

#### 4. **Pause Without Running Job** (`test_caf_pause_without_running_job`)
Tests pausing when no job is active.

**Validates:**
- ✓ Returns False when no job to pause
- ✓ Doesn't raise exceptions
- ✓ Handles gracefully

#### 5. **Resume Without Checkpoint** (`test_caf_resume_without_checkpoint`)
Tests resuming when no checkpoint exists.

**Validates:**
- ✓ Returns False when no checkpoint found
- ✓ Doesn't raise exceptions
- ✓ Handles gracefully

#### 6. **State Transitions** (`test_caf_state_transitions`)
Tests all valid state transitions.

**Validates:**
- ✓ PENDING → RUNNING (start)
- ✓ RUNNING → PAUSED (pause)
- ✓ PAUSED → RUNNING (resume)
- ✓ RUNNING → CANCELED (cancel)
- ✓ State machine validation works

## What Gets Tested

### Ingestion Service
- `start()` - Start fresh ingestion
- `pause()` - Graceful pause with checkpoint
- `resume()` - Resume from checkpoint
- `cancel()` - Cancel running job
- `status()` - Get current job status

### Persistence
- State saved to disk during pause
- State loaded from disk during resume
- Metrics preserved across pause/resume
- Job ID and phase maintained

### Repository
- Queue statistics available
- Job records created correctly
- Database state consistent

### State Machine
- Valid transitions enforced
- Invalid transitions rejected
- Terminal states handled

## Expected Output

### Successful Test Run

```
============================================================
CAF Knowledge Base - Pause/Resume Integration Test
============================================================

============================================================
Testing CAF Knowledge Base Pause/Resume
KB ID: caf
KB Name: Azure Cloud Adoption Framework (CAF)
Source Type: website
============================================================

[Step 1] Starting CAF ingestion...
------------------------------------------------------------
✓ Ingestion started
  Job ID: abc123
  Status: running
  Phase: crawling

[Step 2] Waiting for ingestion progress...
------------------------------------------------------------
✓ Status before pause:
  Status: running
  Phase: crawling
  Progress: 15%
  Metrics: {'documents_processed': 10, 'chunks_total': 45}

[Step 3] Pausing ingestion...
------------------------------------------------------------
✓ Pause initiated successfully
✓ Status after pause:
  Status: paused
  Phase: crawling
  Progress: 15%
  Metrics: {'documents_processed': 10, 'chunks_total': 45}

[Step 4] Verifying state persistence...
------------------------------------------------------------
✓ State persisted to disk
  Job ID: abc123
  Documents processed: 10
  Chunks created: 45
  Queue stats: {'pending': 25, 'processing': 0, 'done': 20, 'error': 0}

[Step 5] Resuming ingestion from checkpoint...
------------------------------------------------------------
✓ Resume initiated successfully
✓ Status after resume:
  Status: running
  Phase: crawling
  Progress: 20%
  Metrics: {'documents_processed': 15, 'chunks_total': 67}

[Step 6] Monitoring resumed ingestion...
------------------------------------------------------------
  [1/5] Status: running, Phase: crawling, Progress: 25%
  [2/5] Status: running, Phase: embedding, Progress: 40%
  [3/5] Status: running, Phase: indexing, Progress: 60%

[Step 7] Final status check...
------------------------------------------------------------
✓ Final status:
  Status: running
  Phase: indexing
  Progress: 75%
  Message: Processing documents

============================================================
Test completed successfully! ✓
============================================================

============================================================
ALL TESTS PASSED ✓
============================================================
```

## Prerequisites

- Backend must be running or database must be accessible
- CAF KB must be configured in `backend/data/knowledge_bases/config.json`
- Python environment with all dependencies installed

## Troubleshooting

### Test Hangs
- Ingestion may take time depending on source
- Tests include timeouts to prevent infinite waits
- Cancel manually if needed: `Ctrl+C`

### Assertion Failures
- Check backend logs for errors
- Verify CAF configuration is correct
- Ensure database is accessible
- Check state files in `data/knowledge_bases/caf/`

### Import Errors
- Run from `backend/` directory
- Ensure virtual environment is activated
- Install dependencies: `pip install -r requirements.txt`

## Integration with CI/CD

Add to pytest configuration:

```ini
# pytest.ini
[pytest]
markers =
    integration: Integration tests (may take longer)
    caf: CAF-specific tests

# Run integration tests
pytest -m integration -v

# Run CAF tests only
pytest -m caf -v
```

Mark tests in code:

```python
@pytest.mark.integration
@pytest.mark.caf
async def test_caf_pause_resume_workflow(...):
    ...
```

## Performance Notes

- **Standalone test**: ~30-60 seconds (depends on ingestion speed)
- **Full pytest suite**: ~2-5 minutes (6 tests with cycles)
- **Individual test**: ~10-30 seconds

## Next Steps

1. **Run the tests** to validate current implementation
2. **Review output** for any failures or warnings
3. **Fix issues** identified by tests
4. **Integrate** into CI/CD pipeline
5. **Monitor** in production

## Related Documentation

- [Pause/Resume Implementation Guide](../../../docs/ingestion/PAUSE_RESUME_IMPLEMENTATION.md)
- [Architecture Documentation](../../../docs/ingestion/ARCHITECTURE.md)
- [Testing Guide](../../../docs/ingestion/PAUSE_RESUME_TESTING_GUIDE.md)
