# ID-Based Resumable Ingestion - Implementation Complete

## Overview
Implemented bulletproof resumable ingestion with sequential ID tracking for all 4 phases: crawling, cleaning, chunking, and indexing.

## What Changed

### Phase 1: Crawl Checkpoint with Sequential IDs
**File**: `backend/app/kb/ingestion/sources/website.py`

- Every discovered URL gets a sequential ID (1, 2, 3, ...)
- Checkpoint structure:
  ```json
  {
    "last_id": 435,
    "pages_total": 491,
    "pages_crawled": 435,
    "url_id_map": {"https://...": 1, ...},
    "urls": {
      "1": {"url": "https://...", "status": "fetched", "timestamp": "..."},
      "435": {"url": "https://...", "status": "pending", "timestamp": "..."}
    }
  }
  ```
- On resume: loads checkpoint, continues from `last_id + 1`
- Each document metadata now includes `doc_id` field

### Phase 2: Document Storage with ID Prefix
**File**: `backend/app/kb/ingestion/base.py`

- New filename format: `{id:04d}_{page-name}.txt`
  - Example: `0001_overview.txt`, `0435_migration-guide.txt`
- Page name extracted from URL, sanitized (alphanumeric + dash/underscore only)
- File header now includes `Doc ID: {id}`
- On resume: can skip documents that already exist on disk

### Phase 3 & 4: Index Checkpoint + Incremental Indexing
**File**: `backend/app/kb/ingestion/indexing/vector.py`

- New checkpoint: `index_checkpoint.json`
  ```json
  {
    "last_chunked_id": 400,
    "last_indexed_id": 400,
    "total_chunks": 939,
    "chunks_per_doc": {"1": 3, "2": 2, ...}
  }
  ```
- Supports loading existing LlamaIndex and appending new documents
- Only processes documents with `doc_id > last_indexed_id`
- Updates checkpoint after each indexing batch
- Atomic checkpoint writes with tempfile + rename

### Phase 5: Resume Logic (Manual Trigger)
**File**: `backend/app/ingestion/service.py`

- Removed auto-resume on startup (user must click resume in frontend)
- `load_all_states()` reads all checkpoints to derive accurate metrics
- Single source of truth: checkpoint files, not snapshot

### Phase 6: Job State Synchronization
**File**: `backend/app/ingestion/service.py`, `backend/data/ingestion/jobs/caf.json`

- Job snapshot now includes checkpoint-derived metrics:
  - `crawl_last_id`: last URL ID assigned
  - `chunked_last_id`: last doc ID chunked
  - `indexed_last_id`: last doc ID indexed
- Metrics derived from:
  - `crawl_checkpoint.json` → pages_crawled, pages_total
  - `documents/` directory count → documents_cleaned
  - `index_checkpoint.json` → chunks_created, chunks_embedded

## File Structure

```
backend/data/knowledge_bases/<kb>/
  crawl_checkpoint.json          # URLs with sequential IDs
  index_checkpoint.json          # Chunking/indexing progress
  documents/
    0001_overview.txt            # ID-prefixed documents
    0002_getting-started.txt
    0435_last-page.txt
  index/
    docstore.json                # LlamaIndex storage
    index_store.json
```

## Migration Script

Created `backend/scripts/migrate_caf_to_ids.py` to backfill existing CAF data:
- Assigns IDs to existing URLs
- Renames document files to new format
- Creates index checkpoint from existing index
- Backs up old checkpoint before migration

Run with:
```bash
cd backend
python scripts/migrate_caf_to_ids.py
```

## Resume Behavior

When user clicks "Resume" in frontend:

1. **Crawling Phase**: 
   - Load `crawl_checkpoint.json`
   - Skip URLs already fetched (status='fetched')
   - Continue from `last_id + 1` for new URLs

2. **Cleaning Phase**:
   - Check `documents/` directory
   - Skip doc IDs that already have files
   - Only fetch/clean new URLs

3. **Indexing Phase**:
   - Load `index_checkpoint.json`
   - Load existing LlamaIndex from disk
   - Only process documents with `doc_id > last_indexed_id`
   - Append new chunks to existing index

## Checkpoint Persistence

All checkpoints use atomic writes:
1. Write to temp file in same directory
2. `os.replace(temp, target)` for atomic rename
3. Prevents corruption on crashes

Checkpoint intervals:
- Crawl: every 50 pages
- Index: after processing each document batch

## Testing the Implementation

1. Start fresh ingestion for a new KB
2. Pause/cancel mid-crawl (e.g., after 100 pages)
3. Restart backend
4. Click "Resume" in frontend
5. Verify it continues from page 101, not page 1

Repeat for each phase:
- Mid-cleaning (delete some document files, resume should re-fetch)
- Mid-indexing (verify it appends to existing index, not rebuild)

## Benefits

✅ **Bulletproof resume**: exact state tracking at document-level granularity
✅ **Space efficient**: only store cleaned docs + index (not raw crawl data)
✅ **Fast resume**: skip already-processed work automatically
✅ **Crash resilient**: atomic checkpoint writes prevent corruption
✅ **Transparent tracking**: UI shows exact progress via checkpoint metrics
✅ **Incremental updates**: can add new pages without rebuilding entire index

## Known Limitations

- Does not support re-crawling updated pages (would need timestamp tracking)
- Deleting a document file requires manual checkpoint cleanup
- No automatic detection of incomplete/corrupted documents
- Index append assumes same embedding model (no model version check)
