# Cleanup Plan: Remove JobStatus Domain Logic

## What We're Removing

### 1. Domain Enum (`backend/app/ingestion/domain/enums.py`):
- ❌ Remove `JobStatus` enum (NOT_STARTED, PENDING, RUNNING, COMPLETED, FAILED)
- ❌ Remove `_TRANSITION_MAP`
- ❌ Remove `StateTransitionError`
- ❌ Remove `validate_transition()` 
- ❌ Remove `transition_or_raise()`
- ❌ Remove `get_allowed_transitions()`
- ❌ Remove `is_terminal_status()`

### 2. State Model (`backend/app/ingestion/domain/models/state.py`):
- ❌ Remove `get_overall_status()` method (uses JobStatus)
- 🔄 Modify: Remove JobStatus import, keep PhaseStatus logic as string-based

### 3. Tests (`backend/app/ingestion/tests/test_state_machine.py`):
- ❌ DELETE entire file (tests state machine we're removing)

### 4. Test Phase State (`backend/app/ingestion/tests/test_phase_state.py`):
- 🔄 UPDATE: Remove JobStatus usage from test assertions

### 5. Domain __init__ exports:
- ❌ Remove JobStatus from exports

## What We're KEEPING

### ✅ Database Model (`backend/app/ingestion/models.py`):
- **KEEP** `JobStatus` enum (database version) - Required for SQLAlchemy
- **KEEP** status column and methods

### ✅ PhaseStatus:
- **KEEP** PhaseStatus enum - This is the new phase tracking system
- **KEEP** PhaseState model

### ✅ JobPhase:
- **KEEP** JobPhase enum (names of phases)

## Files That Will Break (Need Fixing)

All files currently using domain `JobStatus`:
1. `backend/app/ingestion/workers/producer.py` - Uses JobStatus.FAILED
2. `backend/app/ingestion/workers/consumer.py` - Uses JobStatus.FAILED
3. `backend/app/ingestion/application/ingestion_service.py` - Uses JobStatus and transitions
4. `backend/app/ingestion/application/producer_pipeline.py` - Uses JobStatus
5. `backend/app/ingestion/application/consumer_pipeline.py` - Uses JobStatus  
6. `backend/app/ingestion/infrastructure/repository.py` - Maps JobStatus to DB
7. `backend/app/routers/kb_ingestion/ingestion_models.py` - Uses JobStatus in API model

## Strategy

**Phase 1 Cleanup (Now):**
1. Remove domain JobStatus enum and state machine from `enums.py`
2. Delete `test_state_machine.py`
3. Update `state.py` to remove JobStatus references
4. Update test_phase_state.py to use string literals
5. Update domain exports

**Phase 2 (Next - Rebuild):**
- Rebuild status logic from PhaseStatus aggregation
- Fix all broken files with new logic

This is a clean slate approach - remove old, rebuild with new foundation.
