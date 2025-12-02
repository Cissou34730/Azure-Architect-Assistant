# Ingestion Architecture Refactoring Plan

## Current Problems

### 1. **Misplaced Logic**
- `operations.py` contains the entire producer workflow (300+ lines)
- `run_ingestion_pipeline()` does: crawl → save → chunk → enqueue
- Producer worker is just a thin wrapper calling `operations.run_ingestion_pipeline`
- This violates separation of concerns

### 2. **Phase Status Not Tracked**
- Created `phase_status.py` with tracking infrastructure
- But it's not integrated into the pipeline
- Can't properly handle resume scenarios (skip completed phases)

### 3. **Resume Logic Bug**
- When resuming with completed crawl (565 pages, 0 pending URLs)
- Crawler yields 0 documents
- Pipeline fails with "No documents loaded from source"
- Should skip crawling and let consumer finish

## Correct Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Router Layer (router.py)                                     │
│ - HTTP endpoints                                             │
│ - Request validation                                         │
│ - Calls IngestionService                                     │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│ Service Layer (operations.py)                                │
│ - Business logic orchestration                               │
│ - KB validation                                              │
│ - Configuration extraction                                   │
│ - Job creation delegation                                    │
└──────────────────┬──────────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────────┐
│ Ingestion Service (ingestion_service.py)                     │
│ - Job lifecycle management                                   │
│ - Start/Pause/Resume/Cancel                                  │
│ - Creates producer & consumer threads                        │
│ - Manages JobRuntime                                         │
└──────────────┬────────────────────┬─────────────────────────┘
               │                    │
     ┌─────────▼────────┐  ┌────────▼─────────┐
     │ Producer Worker  │  │ Consumer Worker  │
     │ (producer.py)    │  │ (consumer.py)    │
     │                  │  │                  │
     │ 1. Crawl docs    │  │ 1. Dequeue       │
     │ 2. Save to disk  │  │ 2. Embed         │
     │ 3. Chunk         │  │ 3. Index         │
     │ 4. Enqueue       │  │ 4. Commit        │
     │ 5. Set stop_event│  │ 5. Mark complete │
     └──────────────────┘  └──────────────────┘
```

## Refactoring Steps

### Phase 1: Move Producer Logic ✅ (Already correct location)

**Current State Analysis:**
- `operations.run_ingestion_pipeline()` contains all producer logic
- Producer worker just wraps and executes it
- **Decision**: This is actually acceptable IF we clean it up

**Keep it, but improve it:**
1. Add phase status tracking
2. Add phase skip logic for resume
3. Clean up responsibilities

### Phase 2: Integrate Phase Status Tracking

**Add to `operations.run_ingestion_pipeline()`:**
```python
from app.kb.ingestion.phase_status import IngestionPhaseTracker

# Initialize phase tracker
phase_tracker = IngestionPhaseTracker()

# Check if resuming - load phase status from state
if state and state.phase_status:
    # Restore phase status
    ...

# Before crawling
if phase_tracker.crawling.state == PhaseState.COMPLETED:
    logger.info("Crawling already complete - skipping")
    phase_tracker.crawling.skip("Already completed in previous run")
else:
    phase_tracker.crawling.start("Starting document crawl")
    # ... crawl logic ...
    phase_tracker.crawling.complete("Crawled X documents")

# Before chunking
if phase_tracker.chunking.state == PhaseState.COMPLETED:
    logger.info("Chunking already complete - skipping")
    phase_tracker.chunking.skip("Already completed in previous run")
else:
    phase_tracker.chunking.start("Chunking documents")
    # ... chunking logic ...
    phase_tracker.chunking.complete("Created X chunks")

# Save phase status to state
state.phase_status = phase_tracker.to_dict()
```

### Phase 3: Fix Resume Logic

**Problem:**
```
Resume clicked → Crawler finds 565 visited, 0 pending → Yields 0 docs → Pipeline fails
```

**Solution:**
```python
# Check phase status before starting
if state and state.phase_status:
    phases = state.phase_status
    
    # If crawling complete but chunking/embedding not, skip crawl
    if phases['crawling']['state'] == 'completed':
        if phases['chunking']['state'] != 'completed':
            logger.info("Resume: Crawling done, loading documents from disk for chunking")
            # Load documents from disk
            all_documents = _load_documents_from_disk(kb_id)
            # Continue with chunking
        elif phases['embedding']['state'] != 'completed':
            logger.info("Resume: Crawl & chunk done, consumer will process queue")
            # Skip producer entirely, just let consumer work
            return
```

### Phase 4: Clean Separation of Concerns

**operations.py should only:**
- Validate KB exists
- Extract configuration
- Delegate to IngestionService
- Provide high-level pipeline orchestration

**producer.py should contain:**
- All crawl/chunk/enqueue logic (currently in operations.py)
- Phase tracking
- Batch processing
- Or keep as thin wrapper calling operations

**Decision: Keep current structure but clean it up**
- `operations.run_ingestion_pipeline()` is the producer pipeline - that's fine
- Add phase tracking
- Add skip logic
- Improve error handling

## Implementation Priority

### Immediate (Fix Resume Bug)
1. ✅ Consumer drains queue after producer finishes
2. ✅ Consumer marks job complete (not producer)
3. ✅ Status endpoint shows "paused" if pending chunks exist
4. ✅ Frontend hides "Start" for completed jobs
5. **TODO**: Integrate phase tracking
6. **TODO**: Skip completed phases on resume

### Next (Clean Architecture)
1. Document the flow clearly
2. Add phase skip logic
3. Load documents from disk when needed
4. Better error messages

### Future (Nice to Have)
1. Move all producer logic to producer.py (if we want pure separation)
2. Make operations.py pure orchestration
3. More granular phase metrics

## Key Files

- `backend/app/routers/kb_ingestion/operations.py` - Producer pipeline logic (300 lines)
- `backend/app/ingestion/workers/producer.py` - Producer thread wrapper
- `backend/app/ingestion/workers/consumer.py` - Consumer thread
- `backend/app/ingestion/application/ingestion_service.py` - Job lifecycle
- `backend/app/kb/ingestion/phase_status.py` - Phase tracking (created, not used)
- `backend/app/ingestion/domain/models/state.py` - IngestionState with phase_status field

## Status

- ✅ Producer/consumer separation working
- ✅ Consumer completes job after draining queue
- ✅ Frontend shows correct buttons
- ✅ Phase tracking infrastructure created
- ❌ Phase tracking not integrated
- ❌ Resume bug: fails when crawl complete, chunks pending
- ❌ Can't skip completed phases

## Next Steps

1. Integrate phase tracker into `run_ingestion_pipeline`
2. Check phase status before each phase
3. Skip completed phases on resume
4. Load documents from disk if needed
5. Test resume scenarios thoroughly
