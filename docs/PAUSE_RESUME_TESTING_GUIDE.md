# Pause/Resume/Cancel Testing Guide

## Quick Start Testing

### Prerequisites
1. Backend running: `python backend/app/main.py` or use `start-backend.ps1`
2. Frontend running: `npm run dev` in `frontend/` directory
3. At least one knowledge base configured

---

## Test Suite

### Test 1: Basic Pause/Resume During Crawling
**Duration:** 2-3 minutes

**Steps:**
1. Start an ingestion job for a website with 50+ pages (e.g., a section of learn.microsoft.com)
2. Monitor the logs - you should see: `[1/50] ID=1: https://...`
3. After ~10 pages crawled, click **Pause** button in UI
4. **Expected:** 
   - Logs show: `Crawl paused by user at 10 pages, waiting...`
   - Status changes to "paused" in UI within 1 second
   - Backend continues to log the pause message every 0.5s
5. Wait 10 seconds (verify it stays paused)
6. Click **Resume** button
7. **Expected:**
   - Logs show: `Resume requested for {kb_id}`
   - Crawling continues from page 11 (no duplicates)
   - Status changes back to "running"

**Success Criteria:**
✅ Pause takes effect immediately (< 1 second)  
✅ No pages crawled during pause  
✅ Resume continues from exact point (no re-crawling)  
✅ Checkpoint file exists: `backend/data/knowledge_bases/{kb_id}/crawl_checkpoint.json`

---

### Test 2: Cancel During Crawling
**Duration:** 1-2 minutes

**Steps:**
1. Start an ingestion job
2. After ~5 pages, click **Cancel** button
3. Confirm the cancellation in the dialog
4. **Expected:**
   - Logs show: `Crawl cancelled by user at 5 pages`
   - Job stops within 1 second
   - Status changes to "cancelled"
   - Checkpoint saved with 5 pages

**Success Criteria:**
✅ Cancel takes effect immediately  
✅ Partial work preserved in checkpoint  
✅ Job cannot be resumed (status=cancelled is final)

---

### Test 3: Pause During Chunking Phase
**Duration:** 3-4 minutes

**Steps:**
1. Start ingestion with batch_size=10 (default)
2. Wait for Phase 2 to start - logs show: `Chunking batch 1...`
3. Click **Pause** immediately
4. **Expected:**
   - Logs show: `Chunking paused at document X/Y, waiting...`
   - Pause takes effect within 5 seconds (chunking is fast)

**Success Criteria:**
✅ Chunking phase respects pause  
✅ Resume continues chunking from same batch

**Note:** This is hard to test manually because chunking is very fast. More relevant for large document batches.

---

### Test 4: Pause During Embedding Phase (CRITICAL)
**Duration:** 5-10 minutes

**Steps:**
1. Start ingestion job that will create embeddings (any source)
2. Wait until logs show: `Generating embeddings...` or `Appending X documents to existing index`
3. Click **Pause** button
4. **Expected:**
   - Pause takes effect within 10-30 seconds (after current embedding batch)
   - Logs show: `Indexing paused at document X/Y, waiting...`
   - Status changes to "paused"
5. Wait 30 seconds (verify it stays paused)
6. Click **Resume**
7. **Expected:**
   - Embedding continues from next document
   - No duplicate embeddings

**Success Criteria:**
✅ Pause works during slowest operation (OpenAI API calls)  
✅ Pause responsiveness acceptable (< 30 seconds)  
✅ Resume continues from correct document  
✅ Index checkpoint updated: `backend/data/knowledge_bases/{kb_id}/index_checkpoint.json`

**Tip:** Check logs for messages like:
```
Indexing paused at document 20/50, waiting...
Indexing paused at document 20/50, waiting...
Resume requested for {kb_id}
Appended 30 documents to existing index
```

---

### Test 5: Backend Restart During Pause
**Duration:** 3-5 minutes

**Steps:**
1. Start ingestion job
2. Click **Pause** after ~10 pages
3. Verify status shows "paused"
4. Stop the backend (Ctrl+C in terminal)
5. Wait 5 seconds
6. Start the backend again
7. Refresh frontend UI
8. **Expected:**
   - Job still shows "paused" status
   - No automatic resume (job is dormant)
   - Pause button is disabled, Resume button is enabled
9. Click **Resume**
10. **Expected:**
    - New task created
    - Logs show: `Restarting paused job from checkpoint for {kb_id}`
    - Crawling resumes from page 11 (loads checkpoint)

**Success Criteria:**
✅ State persisted across restart  
✅ No auto-resume (user control maintained)  
✅ Resume from UI works after restart  
✅ Checkpoint loaded correctly

---

### Test 6: Pause → Cancel Flow
**Duration:** 1-2 minutes

**Steps:**
1. Start ingestion
2. Click **Pause**
3. Verify status="paused"
4. Click **Cancel** (without resuming first)
5. Confirm cancellation
6. **Expected:**
   - Cancel takes effect immediately
   - No need to resume first
   - Status changes to "cancelled"

**Success Criteria:**
✅ Cancel works from paused state  
✅ No errors in logs

---

### Test 7: Multiple Pause/Resume Cycles
**Duration:** 5-10 minutes

**Steps:**
1. Start ingestion job with 100+ pages
2. Pause at 10 pages → Resume → Continue to 20 pages
3. Pause at 20 pages → Resume → Continue to 30 pages
4. Pause at 30 pages → Resume → Let finish
5. **Expected:**
   - Each pause/resume cycle works smoothly
   - No duplicate pages crawled
   - Final checkpoint shows 100+ pages

**Success Criteria:**
✅ Multiple pause/resume cycles work  
✅ No cumulative errors  
✅ Final document count matches pages crawled

---

## Log Patterns to Look For

### ✅ Good Patterns
```
Pause requested for {kb_id}
Crawl paused by user at 10 pages, waiting...
Resume requested for {kb_id}
Resuming from checkpoint: ID=10, visited=10, queued=40
Checkpoint saved: ID=10, 10 visited, 40 queued
```

### ❌ Bad Patterns
```
Error: state is None  (means state not passed correctly)
Duplicate page warning: already visited  (checkpoint not loading)
IndexError / KeyError  (state corruption)
Task cancelled unexpectedly  (hard cancellation instead of cooperative)
```

---

## Debugging Tips

### Check State Files
```powershell
# View current ingestion state
Get-Content "backend/data/ingestion/jobs/{kb_id}.json"

# View crawl checkpoint
Get-Content "backend/data/knowledge_bases/{kb_id}/crawl_checkpoint.json"

# View index checkpoint
Get-Content "backend/data/knowledge_bases/{kb_id}/index_checkpoint.json"
```

### Monitor Logs in Real-Time
```powershell
# Filter for pause/resume messages
python backend/app/main.py 2>&1 | Select-String "pause|resume|cancel"
```

### Check Task State
```python
# In Python console or endpoint
from app.ingestion.service import IngestionService
service = IngestionService.instance()
state = service.status("your_kb_id")
print(f"Status: {state.status}, Paused: {state.paused}, Cancel: {state.cancel_requested}")
```

---

## Common Issues and Solutions

### Issue: Pause button does nothing
**Possible Cause:** State not being passed to handlers  
**Fix:** Check that `state` parameter is passed through factory → handler → crawler

### Issue: Resume restarts from beginning
**Possible Cause:** Checkpoint not loading or url_id_map not preserved  
**Fix:** Check crawl_checkpoint.json exists and contains url_id_map

### Issue: Pause takes > 1 minute
**Possible Cause:** Stuck in embedding generation without checks  
**Fix:** Already fixed in implementation - check every 10 docs

### Issue: Backend restart causes auto-resume
**Possible Cause:** load_all_states() not clearing pause flag  
**Fix:** Already fixed - flags are intentionally cleared on load

---

## Performance Expectations

| Phase | Pause Responsiveness | Checkpoint Frequency |
|-------|---------------------|---------------------|
| Crawling | < 1 second | Every 50 pages |
| Cleaning | Immediate | Per batch |
| Chunking | < 5 seconds | Per batch |
| Embedding | 10-30 seconds | Every 10 docs |
| Indexing | < 5 seconds | Per batch |

---

## Success Metrics

After running all tests, you should achieve:

✅ **100% pause success rate** - Pause always takes effect  
✅ **< 30 second max pause latency** - Even during embeddings  
✅ **Zero data loss** - Checkpoints preserve all progress  
✅ **Zero duplicate work** - Resume continues from exact point  
✅ **State persistence** - Survives backend restarts  
✅ **User control** - No auto-resume, explicit resume required  

---

## Automated Testing (Future)

To add automated integration tests:

```python
# tests/integration/test_pause_resume.py
import asyncio
import pytest
from app.ingestion.service import IngestionService

@pytest.mark.asyncio
async def test_pause_during_crawling():
    service = IngestionService.instance()
    
    # Start job
    state = await service.start(kb_id, run_pipeline, ...)
    
    # Wait for crawling to start
    await asyncio.sleep(2)
    
    # Pause
    assert await service.pause(kb_id) == True
    assert state.status == "paused"
    
    # Resume
    assert await service.resume(kb_id) == True
    assert state.status == "running"
```

This would require:
1. Mock data sources (mock website with 100 fake pages)
2. Mock OpenAI API (return fake embeddings)
3. Temporary test databases/indexes
4. Async test framework (pytest-asyncio)

---

## Conclusion

Run tests 1, 2, 4, and 5 as minimum validation. Test 4 (embedding phase) is most critical since it's the slowest operation. Test 5 validates persistence across restarts.

Good luck! 🚀
