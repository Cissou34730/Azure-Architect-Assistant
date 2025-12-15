# Legacy Ingestion Pipeline Deprecation

## Status: DEPRECATED

The producer/consumer pipeline-based ingestion system is now deprecated in favor of the orchestrator-based implementation.

## Migration Guide

### Old Architecture (Deprecated)
```
Producer/Consumer Pipeline:
- Phase-based execution (crawling, chunking, embedding, indexing)
- Separate producer and consumer processes
- Phase progress tracking via phase_progress JSON
- Located in: backend/app/ingestion/domain/phases/
```

### New Architecture (Current)
```
Orchestrator-based Pipeline:
- Sequential execution: load → chunk → embed → index
- Single orchestrator process with cooperative gates
- Checkpoint/counter tracking via dedicated columns
- Located in: backend/app/ingestion/application/orchestrator.py
```

## Key Differences

| Feature | Legacy Pipeline | Orchestrator |
|---------|----------------|--------------|
| **API Endpoint** | `/ingestion/jobs` | `/ingestion/v2/jobs` |
| **Execution Model** | Producer/Consumer | Sequential |
| **State Tracking** | `phase_progress` JSON | `checkpoint`, `counters` columns |
| **Pause/Resume** | Phase-level | Batch-level with gates |
| **Idempotency** | Batch deduplication | Content hash (SHA256) |
| **Cleanup** | Manual | Automatic via `cancel` |
| **Retry Logic** | Fixed | Exponential backoff |

## Migration Steps

### 1. Update API Calls
**Before:**
```python
POST /ingestion/jobs/{kb_id}/start
GET /ingestion/jobs/{job_id}/status
```

**After:**
```python
POST /ingestion/v2/jobs/{kb_id}/start
GET /ingestion/v2/jobs/{job_id}/status
POST /ingestion/v2/jobs/{job_id}/pause
POST /ingestion/v2/jobs/{job_id}/resume
POST /ingestion/v2/jobs/{job_id}/cancel
```

### 2. Database Migration
Run migration to add orchestrator columns:
```bash
python backend/app/ingestion/migrations/add_orchestrator_fields.py
```

This adds:
- `checkpoint` (TEXT/JSON): `{last_batch_id, cursor}`
- `counters` (TEXT/JSON): `{docs_seen, chunks_seen, chunks_processed, chunks_skipped, chunks_error}`
- `heartbeat_at` (TIMESTAMP): Last activity timestamp
- `finished_at` (TIMESTAMP): Completion timestamp
- `last_error` (TEXT): Last error message

### 3. Update Job Status Checks
**Before:**
```python
# Legacy: phase_progress JSON
status = job.phase_progress.get("status")
```

**After:**
```python
# Orchestrator: dedicated columns
checkpoint = json.loads(job.checkpoint) if job.checkpoint else None
counters = json.loads(job.counters) if job.counters else None
last_batch = checkpoint["last_batch_id"] if checkpoint else None
```

### 4. Leverage New Features

#### Pause/Resume
```python
# Pause during batch processing
POST /ingestion/v2/jobs/{job_id}/pause

# Resume from last checkpoint
POST /ingestion/v2/jobs/{job_id}/resume
```

#### Cancel with Cleanup
```python
# Cancel and delete all indexed vectors
POST /ingestion/v2/jobs/{job_id}/cancel
# Job resets to not_started, vectors deleted
```

#### Idempotency
```python
# Chunks are deduplicated via content_hash
# Crashes resume without re-processing existing chunks
# content_hash = SHA256(kb_id::source_id::normalized_text)
```

## Deprecated Components

### Files to Remove (Future)
```
backend/app/ingestion/domain/phases/
├── producer/
│   └── batch_producer.py
└── consumer/
    ├── base_consumer.py
    ├── chunking_consumer.py
    ├── embedding_consumer.py
    └── indexing_consumer.py
```

### Routers to Remove
```
backend/app/routers/ingestion.py  # Legacy endpoint
```

### Models to Keep (Backward Compatibility)
```
backend/app/ingestion/models.py
- Keep: current_phase, phase_progress (for old jobs)
- Add: checkpoint, counters, heartbeat_at, finished_at, last_error (for new jobs)
```

## Timeline

- **Phase 1 (Current):** Orchestrator v2 API available alongside legacy
- **Phase 2 (Q1 2026):** Deprecation warnings in legacy endpoints
- **Phase 3 (Q2 2026):** Legacy endpoints disabled by default
- **Phase 4 (Q3 2026):** Legacy code removal

## Testing

### Unit Tests
```bash
pytest backend/tests/test_orchestrator_unit.py -v
```

Tests:
- Content hash determinism
- WorkflowDefinition step sequencing
- RetryPolicy backoff logic

### Integration Tests
```bash
pytest backend/tests/test_orchestrator_integration.py -v
```

Tests:
- Pause/resume with checkpoint
- Cancel with cleanup
- Idempotency via content_hash

## Support

For migration assistance or issues:
1. Check `/ingestion/v2/jobs/{job_id}/status` for detailed counters
2. Review `last_error` column for failure details
3. Inspect `checkpoint` for resume state
4. Monitor `heartbeat_at` for activity tracking

## References

- **Orchestrator Spec:** `docs/ingestion/OrchestratorSpec.md`
- **Implementation Plan:** `docs/plan-orchestratorSpec.prompt.md`
- **New API Router:** `backend/app/routers/ingestion_v2.py`
- **Orchestrator Core:** `backend/app/ingestion/application/orchestrator.py`
