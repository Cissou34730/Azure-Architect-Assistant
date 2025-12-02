# Producer-Consumer Implementation Verification

**Date:** 2025-12-02  
**Branch:** ResilientIngestion  
**Commit:** affa31c

## Implementation Summary

The producer-consumer architecture has been fully implemented per the spec:

### 1. Queue Persistence (DB Layer)
**File:** `backend/app/ingestion/service_components/repository.py`

New functions:
- `enqueue_chunks(job_id, chunks)` - Insert chunk work items with deduplication by `(job_id, doc_hash)`
- `dequeue_batch(job_id, limit=10)` - Atomically select PENDING → PROCESSING
- `commit_batch_success(job_id, item_ids)` - Mark DONE, increment `processed_items`
- `commit_batch_error(item_id, message)` - Mark ERROR, increment `attempts`

### 2. Producer Thread (Extraction & Chunking)
**File:** `backend/app/routers/kb_ingestion/operations.py`

Changes:
- After chunking documents, producer computes `doc_hash = sha256(content + metadata_json)`
- Calls `enqueue_chunks()` instead of indexing directly
- Producer is fast (CPU-bound: crawl → chunk → hash → enqueue)
- Honors pause/cancel via cooperative checks

### 3. Consumer Thread (Embedding & Indexing)
**File:** `backend/app/ingestion/service_components/manager.py` - `_run_consumer()`

Implementation:
- Polls `dequeue_batch(job_id, limit=10)` in a loop
- Prepares documents for indexing (converts queue items to doc format)
- Calls `index_builder.build_index(docs, ...)` to embed and index
- On success: `commit_batch_success(job_id, ids)`
- On failure: `commit_batch_error(item_id, error_msg)`
- Honors `pause_event` and `stop_event`
- Sleeps when no work available (0.5s)

### 4. Threading Architecture
Both threads spawned per job:
- **Producer Thread:** `_run_producer()` → executes `run_ingestion_pipeline()`
- **Consumer Thread:** `_run_consumer()` → polls queue and indexes

Both use shared `JobRuntime` with events:
- `stop_event` - Signals cancellation
- `pause_event` - Signals pause (threads wait)

## Expected Behavior

### Starting Ingestion
```bash
POST /api/ingestion/kb/caf/start
```

1. Manager spawns producer + consumer threads
2. Producer:
   - Crawls pages via `WebsiteCrawler`
   - Chunks text via `ChunkerFactory`
   - Computes `doc_hash` per chunk
   - Enqueues chunks to `ingestion_queue` (status=PENDING)
   - Fast: completes crawling in ~2-5 minutes for CAF
3. Consumer (runs in parallel):
   - Polls `ingestion_queue` for PENDING items
   - Marks them PROCESSING
   - Embeds via OpenAI API (slow: ~0.5-1s per batch)
   - Indexes via LlamaIndex
   - Marks DONE, increments `processed_items`
   - Slow: completes after producer finishes

### Database Flow
```sql
-- Producer writes
INSERT INTO ingestion_queue (job_id, doc_hash, content, metadata, status)
VALUES ('{job_id}', '{hash}', 'chunk text...', {...}, 'PENDING');

-- Consumer reads & updates atomically
UPDATE ingestion_queue SET status='PROCESSING' WHERE id IN (...);
-- [Embed & Index]
UPDATE ingestion_queue SET status='DONE' WHERE id IN (...);
UPDATE ingestion_jobs SET processed_items = processed_items + 10 WHERE id = '{job_id}';
```

### Pause Operation
```bash
POST /api/ingestion/kb/caf/pause
```

1. Manager sets `pause_event` for job runtime
2. Producer: checks `state.paused` in tight loops → returns cleanly, saves state
3. Consumer: checks `pause_event.is_set()` → waits in loop
4. Both threads stop processing; state persisted
5. Queue items remain in PENDING or PROCESSING (reset to PENDING on restart per `recover_inflight_jobs()`)

### Resume Operation
```bash
POST /api/ingestion/kb/caf/resume
```

1. Manager clears `pause_event`
2. If producer thread exited: restarts it (new behavior)
3. Consumer: wakes up, continues polling queue
4. Producer: resumes from `state.json` checkpoint (crawl continues)
5. Both threads process remaining work

### Shutdown (New Behavior)
On app shutdown (`lifecycle.shutdown()`):
- Calls `pause_all()` instead of `cancel_all()`
- All running jobs → status=PAUSED
- Queue items → PROCESSING reset to PENDING on next startup
- State persisted to disk
- On restart: user can resume any paused job

## Verification Steps

### 1. Database Inspection
During ingestion, check queue growth:

```sql
-- Total chunks queued
SELECT COUNT(*) FROM ingestion_queue WHERE job_id = '{job_id}';

-- Status breakdown
SELECT status, COUNT(*) FROM ingestion_queue 
WHERE job_id = '{job_id}' GROUP BY status;

-- Job progress
SELECT total_items, processed_items, 
       ROUND(100.0 * processed_items / NULLIF(total_items, 0), 2) as progress_pct
FROM ingestion_jobs WHERE id = '{job_id}';
```

**Expected Pattern:**
- Producer quickly adds rows (status=PENDING)
- Consumer gradually processes (PENDING → PROCESSING → DONE)
- `total_items` grows fast, `processed_items` grows slower
- After producer completes: consumer catches up until `processed_items == total_items`

### 2. Thread Lifecycle
Monitor logs during start/pause/resume:

```
# Start
INFO - Starting producer thread for KB caf
INFO - Starting consumer thread for KB caf
INFO - PIPELINE: Created handler, ready to load documents
INFO - Starting batch processing with incremental indexing...
INFO - ✓ Enqueued 87/87 chunks for job {job_id}

# Pause
INFO - KB caf paused at batch 3 start
INFO - ✓ State saved: 142 visited, 89 queued, 0 failed
# Consumer waits in loop, producer returns

# Resume
INFO - Resumed: crawling restarted from checkpoint
# Producer restarts, consumer wakes up
INFO - Resuming crawl: visited=142, queued=89
```

### 3. Index Growth
Consumer writes to `backend/data/knowledge_bases/caf/index/`:

```bash
ls backend/data/knowledge_bases/caf/index/
# default__vector_store.json
# docstore.json
# graph_store.json
# index_store.json
```

These files grow as consumer processes batches.

### 4. State Persistence
Check `backend/data/knowledge_bases/caf/state.json`:

```json
{
  "kb_id": "caf",
  "job_id": "{uuid}",
  "status": "running",  // or "paused"
  "phase": "crawling",
  "progress": 45,
  "metrics": {
    "documents_processed": 142,
    "chunks_total": 523,
    "batches_processed": 6
  },
  "crawl": {
    "pages_crawled": 142,
    "pages_queued": 89,
    "visited_urls": [...],
    "pending_urls": [...]
  }
}
```

### 5. Deduplication
Producer skips duplicate chunks via unique constraint:

```sql
UNIQUE (job_id, doc_hash)
```

If same content appears twice, second insert is skipped (caught in try/except).

## Manual Test Commands

```powershell
# Start backend
npm run backend

# Start ingestion
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/ingestion/kb/caf/start

# Check status (multiple times)
Invoke-RestMethod -Method Get -Uri http://localhost:8000/api/ingestion/kb/caf/status | ConvertTo-Json

# Pause
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/ingestion/kb/caf/pause

# Check state.json (should show status=paused)
Get-Content backend\data\knowledge_bases\caf\state.json | ConvertFrom-Json | ConvertTo-Json

# Resume
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/ingestion/kb/caf/resume

# Monitor until complete
while ($true) {
    $status = Invoke-RestMethod -Method Get -Uri http://localhost:8000/api/ingestion/kb/caf/status
    Write-Host "Status: $($status.status) | Phase: $($status.phase) | Progress: $($status.progress)%"
    if ($status.status -in @('completed', 'failed', 'cancelled')) { break }
    Start-Sleep -Seconds 5
}
```

## Success Criteria

✅ **Producer-Consumer Separation:**
- Producer completes crawling/chunking quickly
- Consumer runs concurrently, indexing slower
- Database queue acts as buffer

✅ **Crash Resilience:**
- On restart: PROCESSING → PENDING via `recover_inflight_jobs()`
- Resume picks up from checkpoint

✅ **Pause/Resume:**
- Pause stops both threads cleanly
- Resume restarts producer if needed, consumer continues
- State persisted throughout

✅ **Shutdown Grace:**
- Shutdown pauses all jobs (not cancel)
- State saved to disk
- On next start: jobs can be resumed

✅ **Deduplication:**
- Duplicate chunks (same `doc_hash`) skipped
- No wasted embedding API calls

## Next Steps

1. **Run Full CAF Flow:**
   - Verify queue progression in `ingestion.db`
   - Confirm index files grow during consumer work
   - Test pause → resume → complete cycle

2. **Test Multi-KB:**
   - Start CAF and NIST simultaneously
   - Verify independent job states and queues
   - Confirm no cross-contamination

3. **Error Handling:**
   - Simulate OpenAI API error (invalid key)
   - Verify items marked ERROR, attempts incremented
   - Confirm retry logic (future enhancement)

4. **Deletion Logic:**
   - Implement `delete_nodes(ids)` in index builder
   - On cancel: delete vector entries by `doc_hash`
   - Clean up queue and job records

## Implementation Notes

- **Consumer batching:** Currently 10 items per batch. Tune based on performance.
- **Error retry:** Currently marks ERROR and stops. Future: retry with exponential backoff.
- **Progress updates:** Consumer could update `state.progress` as it processes queue.
- **Concurrency:** One consumer per job. Could scale to multiple consumers per job (requires DB lock coordination).

---

**Status:** ✅ Implementation Complete  
**Testing:** Manual verification pending  
**Performance:** To be measured with real workload
