# Unified State Tracking Implementation Plan

## Overview
Consolidate three separate tracking systems (IngestionState, crawl_checkpoint, index_checkpoint) into a single unified `state.json` file per knowledge base.

---

## Current Problems

### 1. Three Separate State Files
- `backend/data/ingestion/jobs/{kb_id}.json` - High-level job status
- `backend/data/knowledge_bases/{kb_id}/crawl_checkpoint.json` - Crawler state (200KB+ with giant URL arrays)
- `backend/data/knowledge_bases/{kb_id}/index_checkpoint.json` - Indexing progress

### 2. Duplicate & Redundant Data
- URLs stored in both `url_id_map` dict AND `visited` array
- `last_chunked_id` and `last_indexed_id` always identical (no separation)
- `chunks_per_doc` dict never used
- Metrics enriched on load, not live updated

### 3. State Synchronization Issues
- Metrics only accurate when loading from disk
- No atomic updates across files
- Race conditions possible (state saved, checkpoint fails)

---

## Proposed Solution: Single State File

### Location
`backend/data/knowledge_bases/{kb_id}/state.json`

### Complete Schema

```json
{
  "kb_id": "caf",
  "version": 1,
  "updated_at": "2025-12-01T10:15:23.456Z",
  
  "job": {
    "status": "running",
    "phase": "crawling",
    "progress": 45,
    "message": "Crawling: 150/200 pages",
    "error": null,
    "created_at": "2025-12-01T10:00:00Z",
    "started_at": "2025-12-01T10:00:05Z",
    "completed_at": null,
    "paused": false,
    "cancel_requested": false
  },
  
  "crawl": {
    "last_doc_id": 150,
    "pages_crawled": 150,
    "pages_queued": 50,
    "pages_failed": 5,
    "pending_urls": [
      "https://example.com/page1",
      "https://example.com/page2"
    ],
    "start_url": "https://learn.microsoft.com/en-us/azure/caf/",
    "url_prefix": "https://learn.microsoft.com/en-us/azure/caf"
  },
  
  "processing": {
    "documents_saved": 145,
    "last_chunked_id": 150,
    "last_indexed_id": 150,
    "chunks_total": 1200,
    "batches_processed": 15
  },
  
  "metrics": {
    "documents_per_batch": 10,
    "avg_chunks_per_doc": 8,
    "total_chars_ingested": 450000,
    "crawl_rate_pages_per_min": 12
  }
}
```

---

## Implementation Steps

### Step 1: Update WebsiteCrawler (crawler.py)

#### Changes:
1. **Remove giant storage structures**:
   - Delete `url_id_map: Dict[str, int]` - use counter instead
   - Delete `visited: Set[str]` - don't need to track ALL visited URLs
   - Keep only `to_visit: List[str]` queue (cap at 200 URLs in checkpoint)

2. **Update `_save_checkpoint()` → `_save_state()`**:
   ```python
   def _save_state(self, visited_count: int, to_visit: List[str], last_id: int):
       """Save crawler state to unified state.json"""
       state_path = self._get_state_path()
       
       # Load existing state (preserve other sections)
       state = {}
       if state_path.exists():
           with open(state_path, 'r', encoding='utf-8') as f:
               state = json.load(f)
       
       # Update only crawl section
       state['kb_id'] = self.kb_id
       state['version'] = 1
       state['updated_at'] = datetime.now().isoformat()
       state['crawl'] = {
           'last_doc_id': last_id,
           'pages_crawled': visited_count,
           'pages_queued': len(to_visit),
           'pending_urls': to_visit[:200],  # Only first 200 URLs
           'start_url': self.start_url,
           'url_prefix': self.url_prefix
       }
       
       # Atomic write
       import tempfile, os
       tmp_fd, tmp_name = tempfile.mkstemp(dir=state_path.parent, suffix='.tmp')
       with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
           json.dump(state, f, indent=2)
       os.replace(tmp_name, state_path)
       
       logger.info(f"✓ State saved: {visited_count} crawled, {len(to_visit)} queued")
   ```

3. **Update `_get_checkpoint_path()` → `_get_state_path()`**:
   ```python
   def _get_state_path(self) -> Path:
       """Get path to unified state file"""
       backend_root = Path(__file__).parent.parent.parent.parent.parent.parent
       state_dir = backend_root / "data" / "knowledge_bases" / self.kb_id
       state_dir.mkdir(parents=True, exist_ok=True)
       return state_dir / "state.json"
   ```

4. **Update checkpoint loading in `crawl()`**:
   ```python
   # Try to load existing state
   state_path = self._get_state_path()
   if state_path.exists():
       try:
           with open(state_path, 'r', encoding='utf-8') as f:
               data = json.load(f)
               crawl_state = data.get('crawl', {})
               last_id = crawl_state.get('last_doc_id', 0)
               visited_count = crawl_state.get('pages_crawled', 0)
               to_visit = crawl_state.get('pending_urls', [start_url])
               logger.info(f"Resuming from state: ID={last_id}, crawled={visited_count}, queued={len(to_visit)}")
       except Exception as e:
           logger.warning(f"Could not load state: {e}, starting fresh")
   ```

5. **Update crawl loop to track only count, not set**:
   ```python
   visited_count = visited_count or 0  # Resume from saved count
   visited_urls_this_session = set()   # Only track current session for deduplication
   
   while to_visit and visited_count < max_pages:
       url = to_visit.pop(0)
       
       # Skip if already visited this session
       if url in visited_urls_this_session:
           continue
       
       # Assign sequential ID
       last_id += 1
       visited_urls_this_session.add(url)
       visited_count += 1
       
       # ... rest of processing ...
       
       # Save state every N pages
       pages_since_checkpoint += 1
       if pages_since_checkpoint >= checkpoint_interval:
           self._save_state(visited_count, to_visit, last_id)
           pages_since_checkpoint = 0
   ```

#### Benefits:
- ✅ **90% smaller checkpoint** - No giant URL arrays
- ✅ **Faster I/O** - Small JSON file (<10KB vs 200KB+)
- ✅ **Simpler logic** - Just counter and queue

---

### Step 2: Update VectorIndexBuilder (vector.py)

#### Changes:
1. **Replace `_load_index_checkpoint()` with `_load_state()`**:
   ```python
   def _load_state(self) -> Dict[str, Any]:
       """Load processing state from unified state.json"""
       state_path = self._get_state_path()
       if state_path.exists():
           try:
               with open(state_path, 'r', encoding='utf-8') as f:
                   data = json.load(f)
                   return data.get('processing', {
                       'last_indexed_id': 0,
                       'chunks_total': 0,
                       'batches_processed': 0
                   })
           except Exception as e:
               logger.warning(f"Could not load state: {e}")
       return {
           'last_indexed_id': 0,
           'chunks_total': 0,
           'batches_processed': 0
       }
   ```

2. **Replace `_save_index_checkpoint()` with `_save_state()`**:
   ```python
   def _save_state(self, last_indexed_id: int, chunks_total: int, batches_processed: int):
       """Save processing state to unified state.json"""
       state_path = self._get_state_path()
       
       # Load existing state
       state = {}
       if state_path.exists():
           with open(state_path, 'r', encoding='utf-8') as f:
               state = json.load(f)
       
       # Update processing section
       state['kb_id'] = self.kb_id
       state['version'] = 1
       state['updated_at'] = datetime.now().isoformat()
       state['processing'] = {
           'last_indexed_id': last_indexed_id,
           'chunks_total': chunks_total,
           'batches_processed': batches_processed
       }
       
       # Atomic write
       import tempfile, os
       tmp_fd, tmp_name = tempfile.mkstemp(dir=state_path.parent, suffix='.tmp')
       with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
           json.dump(state, f, indent=2)
       os.replace(tmp_name, state_path)
       
       logger.info(f"✓ State saved: indexed up to doc_id {last_indexed_id}")
   ```

3. **Remove redundant fields**:
   - Delete `last_chunked_id` (always same as `last_indexed_id`)
   - Delete `chunks_per_doc` dict (unused)
   - Keep only `last_indexed_id`, `chunks_total`, `batches_processed`

4. **Update `_get_index_checkpoint_path()` → `_get_state_path()`**:
   ```python
   def _get_state_path(self) -> Path:
       """Get path to unified state file"""
       kb_dir = Path(self.storage_dir).parent
       return kb_dir / "state.json"
   ```

#### Benefits:
- ✅ **No redundant fields** - Clean, minimal tracking
- ✅ **Same file as crawler** - Atomic updates possible
- ✅ **Live metrics** - Always current

---

### Step 3: Update IngestionService (service.py)

#### Changes:
1. **Update `_persist_state()` to write to unified state.json**:
   ```python
   def _persist_state(self, state: IngestionState):
       """Persist state to unified state.json in KB directory"""
       import json, tempfile, os
       from pathlib import Path
       
       # State file location: backend/data/knowledge_bases/{kb_id}/state.json
       backend_root = Path(__file__).parent.parent
       state_path = backend_root / "data" / "knowledge_bases" / state.kb_id / "state.json"
       state_path.parent.mkdir(parents=True, exist_ok=True)
       
       # Load existing state (preserve crawl/processing sections)
       data = {}
       if state_path.exists():
           try:
               with open(state_path, 'r', encoding='utf-8') as f:
                   data = json.load(f)
           except Exception:
               data = {}
       
       # Update job section
       data['kb_id'] = state.kb_id
       data['version'] = 1
       data['updated_at'] = datetime.now().isoformat()
       data['job'] = {
           'status': state.status,
           'phase': state.phase,
           'progress': state.progress,
           'message': state.message,
           'error': state.error,
           'created_at': state.created_at.isoformat() if state.created_at else None,
           'started_at': state.started_at.isoformat() if state.started_at else None,
           'completed_at': state.completed_at.isoformat() if state.completed_at else None,
           'paused': state.paused,
           'cancel_requested': state.cancel_requested
       }
       
       # Preserve existing sections (crawl, processing updated by other components)
       
       # Atomic write
       try:
           tmp_fd, tmp_name = tempfile.mkstemp(dir=str(state_path.parent), suffix='.tmp')
           with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
               json.dump(data, f, indent=2)
           os.replace(tmp_name, str(state_path))
       except Exception as e:
           logger.warning(f"Failed to persist state {state.kb_id}: {e}")
   ```

2. **Simplify `load_all_states()` - remove enrichment**:
   ```python
   def load_all_states(self):
       """Load all persisted states from unified state.json files"""
       import json
       from pathlib import Path
       
       try:
           kb_root = Path(__file__).parent.parent / "data" / "knowledge_bases"
           if not kb_root.exists():
               return
           
           for kb_dir in kb_root.iterdir():
               if not kb_dir.is_dir():
                   continue
               
               state_file = kb_dir / "state.json"
               if not state_file.exists():
                   continue
               
               try:
                   with open(state_file, 'r', encoding='utf-8') as f:
                       data = json.load(f)
                   
                   job = data.get('job', {})
                   crawl = data.get('crawl', {})
                   processing = data.get('processing', {})
                   
                   state = IngestionState(
                       kb_id=data.get('kb_id', kb_dir.name),
                       status=job.get('status', 'pending'),
                       phase=job.get('phase', 'crawling'),
                       progress=int(job.get('progress', 0)),
                       message=job.get('message', ''),
                       error=job.get('error'),
                       metrics={
                           'pages_crawled': crawl.get('pages_crawled', 0),
                           'pages_queued': crawl.get('pages_queued', 0),
                           'last_doc_id': crawl.get('last_doc_id', 0),
                           'last_indexed_id': processing.get('last_indexed_id', 0),
                           'chunks_total': processing.get('chunks_total', 0),
                           'batches_processed': processing.get('batches_processed', 0)
                       },
                       created_at=datetime.fromisoformat(job['created_at']) if job.get('created_at') else None,
                       started_at=datetime.fromisoformat(job['started_at']) if job.get('started_at') else None,
                       completed_at=datetime.fromisoformat(job['completed_at']) if job.get('completed_at') else None,
                   )
                   
                   # Mark flags false on load (intentional)
                   state.paused = False
                   state.cancel_requested = False
                   
                   self._states[state.kb_id] = state
                   
               except Exception as e:
                   logger.warning(f"Failed to load state from {state_file}: {e}")
       except Exception as e:
           logger.warning(f"Failed scanning states: {e}")
   ```

3. **Delete old filesystem tracking**:
   - Remove `self._root` (ingestion/jobs directory)
   - Remove `_update_index()` method
   - Remove `_index_path()` method
   - Remove old `_state_path()` method

#### Benefits:
- ✅ **No enrichment logic** - Metrics always live
- ✅ **Simpler loading** - One file, all data
- ✅ **No duplicate storage** - Single source of truth

---

### Step 4: Update Operations Pipeline (operations.py)

#### Changes:
1. **Update progress callback to write to state.json**:
   ```python
   def progress_callback(phase: IngestionPhase, progress: int, message: str, metrics: Dict[str, Any] = None):
       # Update IngestionState
       if state:
           state.phase = phase.value if hasattr(phase, 'value') else str(phase)
           state.progress = progress
           state.message = message
           if metrics:
               state.metrics.update(metrics)
           
           # Persist state immediately (writes to state.json)
           from app.ingestion.service import IngestionService
           ingest_service = IngestionService.instance()
           ingest_service._persist_state(state)
   ```

2. **Update batch completion to save state**:
   ```python
   # After each batch is indexed
   total_chunks_indexed += len(batch_chunks)
   
   # Update metrics in state
   if state:
       state.metrics['batches_processed'] = batch_num
       state.metrics['chunks_total'] = total_chunks_indexed
       state.metrics['documents_processed'] = len(all_documents)
       
       # Persist state
       from app.ingestion.service import IngestionService
       ingest_service = IngestionService.instance()
       ingest_service._persist_state(state)
   ```

#### Benefits:
- ✅ **Live progress updates** - Frontend sees real-time data
- ✅ **No stale metrics** - Always current

---

## Migration Strategy

### Option A: Hard Cutover (Recommended for POC)
1. Implement all changes
2. Test with new KB (no migration needed)
3. For existing KBs: delete old checkpoints, restart ingestion

### Option B: Migration Script
Create `backend/scripts/migrate_to_unified_state.py`:

```python
"""Migrate old checkpoint files to unified state.json"""
import json
from pathlib import Path
from datetime import datetime

def migrate_kb(kb_id: str):
    kb_root = Path("backend/data/knowledge_bases") / kb_id
    
    # Load old files
    crawl_cp = kb_root / "crawl_checkpoint.json"
    index_cp = kb_root / "index_checkpoint.json"
    job_state = Path("backend/data/ingestion/jobs") / f"{kb_id}.json"
    
    unified_state = {
        "kb_id": kb_id,
        "version": 1,
        "updated_at": datetime.now().isoformat(),
        "job": {},
        "crawl": {},
        "processing": {},
        "metrics": {}
    }
    
    # Migrate job state
    if job_state.exists():
        with open(job_state) as f:
            job_data = json.load(f)
        unified_state["job"] = {
            "status": job_data.get("status", "pending"),
            "phase": job_data.get("phase", "crawling"),
            "progress": job_data.get("progress", 0),
            "message": job_data.get("message", ""),
            "error": job_data.get("error"),
            "created_at": job_data.get("created_at"),
            "started_at": job_data.get("started_at"),
            "completed_at": job_data.get("completed_at"),
            "paused": False,
            "cancel_requested": False
        }
    
    # Migrate crawl checkpoint
    if crawl_cp.exists():
        with open(crawl_cp) as f:
            crawl_data = json.load(f)
        unified_state["crawl"] = {
            "last_doc_id": crawl_data.get("last_id", 0),
            "pages_crawled": crawl_data.get("pages_crawled", 0),
            "pages_queued": len(crawl_data.get("to_visit", [])),
            "pending_urls": crawl_data.get("to_visit", [])[:200],  # Only first 200
            "start_url": "",  # Unknown from old data
            "url_prefix": ""
        }
    
    # Migrate index checkpoint
    if index_cp.exists():
        with open(index_cp) as f:
            index_data = json.load(f)
        unified_state["processing"] = {
            "last_indexed_id": index_data.get("last_indexed_id", 0),
            "chunks_total": index_data.get("total_chunks", 0),
            "batches_processed": 0
        }
    
    # Write unified state
    state_path = kb_root / "state.json"
    with open(state_path, 'w') as f:
        json.dump(unified_state, f, indent=2)
    
    print(f"✓ Migrated {kb_id} to unified state")
    
    # Optionally delete old files
    # crawl_cp.unlink(missing_ok=True)
    # index_cp.unlink(missing_ok=True)
    # job_state.unlink(missing_ok=True)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        migrate_kb(sys.argv[1])
    else:
        # Migrate all KBs
        kb_root = Path("backend/data/knowledge_bases")
        for kb_dir in kb_root.iterdir():
            if kb_dir.is_dir():
                migrate_kb(kb_dir.name)
```

Usage: `python backend/scripts/migrate_to_unified_state.py caf`

---

## Testing Plan

### 1. Unit Tests
- Test state loading/saving with partial data
- Test atomic writes (simulate crashes)
- Test migration script

### 2. Integration Tests
- Start fresh ingestion → verify state.json created correctly
- Pause → verify crawl.pending_urls preserved
- Resume → verify continues from last_doc_id
- Cancel → verify state marked cancelled

### 3. Performance Tests
- Compare file sizes (old vs new)
- Compare I/O times (write 1000 URLs)
- Compare resume times (load state)

---

## Expected Benefits

### File Size Reduction
- **Old**: 200KB+ crawl_checkpoint.json (1000 URLs × 2 locations)
- **New**: <10KB state.json (200 URLs + counters)
- **Savings**: ~95% reduction

### I/O Performance
- **Old**: Parse 3 JSON files (200KB + 10KB + 5KB = 215KB)
- **New**: Parse 1 JSON file (<10KB)
- **Speedup**: ~20x faster

### Code Complexity
- **Old**: 3 separate persistence methods + enrichment logic
- **New**: 1 unified persistence method, no enrichment
- **Reduction**: ~60% less code

### Reliability
- **Old**: Race conditions possible (3 files updated separately)
- **New**: Atomic updates (1 file, section-based updates)
- **Improvement**: No state drift

---

## Rollback Plan

If issues arise:
1. Keep old checkpoint code in `archive/legacy_checkpoints/`
2. Add feature flag: `USE_UNIFIED_STATE = os.getenv("USE_UNIFIED_STATE", "true") == "true"`
3. If needed, revert flag to "false" and use old system
4. Migration script can convert back (state.json → old checkpoints)

---

## Success Criteria

✅ **Functional**:
- New ingestion works end-to-end with unified state
- Resume from pause works correctly
- Cancel preserves partial progress

✅ **Performance**:
- Checkpoint files <10KB (vs 200KB+ before)
- State save/load <100ms (vs ~1s before)

✅ **Maintainability**:
- Single source of truth (no cross-file enrichment)
- Clear state schema (self-documenting)
- Simpler debugging (one file to inspect)

---

## Timeline Estimate

- **Step 1** (Crawler): 2-3 hours
- **Step 2** (IndexBuilder): 1-2 hours
- **Step 3** (IngestionService): 1-2 hours
- **Step 4** (Operations): 1 hour
- **Testing**: 2-3 hours
- **Total**: 7-11 hours

---

## Next Steps

1. Review and approve this plan
2. Create backup of current code
3. Implement Step 1 (Crawler) first
4. Test with small KB (10-20 pages)
5. Implement Steps 2-4
6. Full integration test
7. Deploy to production
