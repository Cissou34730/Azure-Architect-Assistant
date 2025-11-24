# WAF RAG System - Implementation Complete

## Summary of Changes

The WAF RAG system has been updated to implement a **two-phase ingestion workflow** with mandatory **document-level validation** before chunking and indexing, as specified in `RAG_POC_SPECS.md`.

## Key Changes

### 1. **Two-Phase Ingestion Workflow**

#### **Phase 1: Document Cleaning & Export**
- **File**: `backend/src/python/ingestion.py`
- Crawls and cleans WAF documentation
- **Exports** cleaned documents as `.md` files to `cleaned_documents/`
- Creates `validation_manifest.json` with status: `PENDING_REVIEW`
- **No chunking** occurs at this stage

#### **Phase 2: Chunking, Embeddings, Indexing**
- **File**: `backend/src/python/build_index.py` (NEW)
- Only processes documents marked as `APPROVED` in manifest
- Chunks documents (800 tokens, 120 overlap)
- Generates embeddings (text-embedding-3-small)
- Builds vector index in `waf_storage_clean/`

### 2. **Model Updates**
- **Generation Model**: Changed from `gpt-4-turbo-preview` to `gpt-4o-mini`
- **File**: `backend/src/python/query_service.py`
- More cost-effective for RAG with high-quality retrieval

### 3. **New Scripts**

| Script | Purpose |
|--------|---------|
| `run_waf_phase1.py` | Run Phase 1: Crawl + Clean + Export |
| `run_waf_phase2.py` | Run Phase 2: Chunk + Embed + Index (approved docs only) |
| `auto_approve_docs.py` | Helper to auto-approve all documents (for testing) |
| `backend/src/python/build_index.py` | Phase 2 index builder |

### 4. **TypeScript Integration**

**Updated**: `backend/src/services/WAFService.ts`
- `startIngestionPhase1()` - Triggers Phase 1
- `startIngestionPhase2()` - Triggers Phase 2
- `startIngestion()` - Full pipeline (auto-approve for backward compatibility)
- Updated `getIngestionStatus()` to track validation state

**Updated**: `backend/src/api/waf.ts`
- `POST /api/waf/ingest/phase1` - Start Phase 1
- `POST /api/waf/ingest/phase2` - Start Phase 2
- `POST /api/waf/ingest` - Full pipeline (legacy, maintained for compatibility)

### 5. **Validation Manifest Format**

**File**: `validation_manifest.json`

```json
[
  {
    "document_id": "doc_0001",
    "url": "https://learn.microsoft.com/...",
    "title": "Document Title",
    "section": "pillar",
    "file_path": "cleaned_documents/doc_0001.md",
    "char_count": 5234,
    "status": "PENDING_REVIEW"  // PENDING_REVIEW | APPROVED | REJECTED
  }
]
```

## Usage Workflows

### **Workflow 1: Manual Validation (Recommended)**

```bash
# Phase 1: Crawl and clean
python run_waf_phase1.py

# Manual validation
# Edit validation_manifest.json - set status to APPROVED/REJECTED

# Phase 2: Build index from approved docs
python run_waf_phase2.py
```

### **Workflow 2: Auto-Approve (Quick Testing)**

```bash
# Phase 1
python run_waf_phase1.py

# Auto-approve all
python auto_approve_docs.py

# Phase 2
python run_waf_phase2.py
```

### **Workflow 3: Legacy (Backward Compatible)**

```bash
# Full pipeline with auto-approval
python run_waf_ingestion.py  # Now calls Phase 1 + auto-approve + Phase 2
```

### **Workflow 4: Via API**

```bash
# Phase 1
curl -X POST http://localhost:3000/api/waf/ingest/phase1

# Manual validation of validation_manifest.json

# Phase 2
curl -X POST http://localhost:3000/api/waf/ingest/phase2
```

## File Structure

```
Azure-Architect-Assistant/
├── run_waf_phase1.py           # NEW: Phase 1 runner
├── run_waf_phase2.py           # NEW: Phase 2 runner
├── auto_approve_docs.py        # NEW: Auto-approval helper
├── run_waf_ingestion.py        # UPDATED: Full pipeline (auto-approve)
├── validation_manifest.json    # NEW: Document validation manifest (generated)
├── cleaned_documents/          # NEW: Cleaned .md files (generated)
│   ├── doc_0001.md
│   ├── doc_0002.md
│   └── ...
└── backend/src/python/
    ├── crawler.py              # Unchanged
    ├── ingestion.py            # UPDATED: Export for validation
    ├── build_index.py          # NEW: Phase 2 index builder
    ├── chunker.py              # Unchanged (now optional)
    ├── indexer.py              # Unchanged (deprecated, use build_index.py)
    ├── query_service.py        # UPDATED: gpt-4o-mini
    └── query_wrapper.py        # Unchanged
```

## Validation States

| Status | Meaning |
|--------|---------|
| `PENDING_REVIEW` | Default state after Phase 1 export |
| `APPROVED` | Document will be included in index |
| `REJECTED` | Document will be excluded from index |

## Benefits of Two-Phase Workflow

1. **Quality Control**: Manual review of cleaned documents before expensive embedding generation
2. **Cost Optimization**: Only generate embeddings for approved content
3. **Flexibility**: Reject low-quality or irrelevant documents
4. **Transparency**: Full visibility into what content enters the index
5. **Iterative Refinement**: Re-run Phase 2 with different document selections

## Backward Compatibility

- Existing `/api/waf/ingest` endpoint still works (auto-approves all documents)
- Old `run_waf_ingestion.py` script updated to use two-phase workflow internally
- No breaking changes to query API

## Testing

```bash
# Quick test with auto-approval
python run_waf_phase1.py
python auto_approve_docs.py
python run_waf_phase2.py

# Query the index
curl -X POST http://localhost:3000/api/waf/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the five pillars of WAF?"}'
```

## Next Steps

1. Run Phase 1 to generate cleaned documents
2. Review and validate documents in `cleaned_documents/`
3. Edit `validation_manifest.json` to approve/reject documents
4. Run Phase 2 to build the final index
5. Query the WAF documentation through the API

---

**Implementation Status**: ✅ Complete and ready for testing

**Date**: November 24, 2025
