# Knowledge Base Ingestion Stack

_Repository: `backend/app`_

---

## 1. HTTP Surface

### 1.1 Router Registration
- `app.main.app.include_router(kb_ingestion_router)` exposes `/api/ingestion/*`.
- Request lifecycle: FastAPI -> `app/routers/kb_ingestion/router.py`.

### 1.2 Endpoint Inventory

| Route | Handler | Purpose | Imported Dependencies |
| --- | --- | --- | --- |
| `POST /kb/create` | `create_kb` | Persist KB metadata and storage layout | `get_ingestion_service`, `invalidate_kb_manager` |
| `GET /kb/list` | `list_kbs` | Enumerate configured KBs | `get_kb_manager` |
| `DELETE /kb/{kb_id}` | `delete_kb` | Stop jobs, purge cache, remove config + data | `IngestionService`, `clear_index_cache`, `invalidate_kb_manager` |
| `POST /kb/{kb_id}/start` | `start_ingestion` | Launch async ingestion job | `get_ingestion_service`, `IngestionService` |
| `GET /kb/{kb_id}/status` | `get_kb_status` | Read persisted state | `IngestionService` |
| `POST /kb/{kb_id}/cancel` | `cancel_ingestion` | Cooperative + hard cancellation | `IngestionService` |
| `POST /kb/{kb_id}/pause` | `pause_ingestion` | Cooperative pause | `IngestionService` |
| `POST /kb/{kb_id}/resume` | `resume_ingestion` | Resume or fresh start with checkpoint | `IngestionService`, `get_ingestion_service` |
| `GET /jobs` | `list_jobs` | List `IngestionState` objects | `IngestionService` |

### 1.3 Request/Response Models (`models.py`)
- `CreateKBRequest`/`Response`, `StartIngestionResponse`.
- `JobStatusResponse` couples enumerated `JobStatus` with `IngestionPhase` (imported from `app.kb.ingestion.base`).
- Source configuration schemas (`WebsiteConfig`, `YouTubeConfig`, etc.) describe `source_config` payloads.

---

## 2. Service Layer (`operations.py`)

### 2.1 `KBIngestionService`
Singleton (`get_ingestion_service`) providing synchronous business logic invoked by router.

#### `create_knowledge_base(request)`
1. `get_kb_manager()` (singleton from `service_registry`).
2. Builds config dict (source metadata, chunk params).
3. `KBManager.create_kb` persists config + scaffolds `data/knowledge_bases/{kb_id}/{index|documents}/`.
4. `invalidate_kb_manager()` clears cached manager so future calls reload `config.json`.

#### `start_ingestion(kb_id)`
- Validates KB existence and returns job metadata (actual async execution handled later).

#### `run_ingestion_pipeline(kb_config, state)`
Async coroutine executed by `IngestionService.start`. Responsibilities:
1. Resolve KB parameters (`source_type`, chunk options, storage paths).
2. Assemble factories:
  - `SourceHandlerFactory.create_handler` -> source-specific loader.
  - `ChunkerFactory.create_chunker` -> currently `SemanticChunker`.
  - `IndexBuilderFactory.create_builder` -> `VectorIndexBuilder`.
3. `progress_callback` updates `IngestionState` and calls `_persist_state` on `IngestionService`.
4. Generator loop:
   - `handler.ingest(config)` yields batches (website handler yields streamed batches; other handlers return lists).
   - `_save_documents_to_disk` writes markdown snapshots to `data/knowledge_bases/{kb_id}/documents`.
   - `chunker.chunk_documents` returns semantic chunks.
   - `index_builder.build_index(documents_dict, progress_callback, state)` handles incremental indexing.
5. Cooperative controls:
   - `check_pause_cancel` inspects `state.paused`/`state.cancel_requested`.
   - Respects `asyncio.sleep(0)` yields for event loop fairness.
6. Metrics aggregation: `state.metrics` tracks documents, chunks, batches.
7. Errors mark `state.status = "failed"` and bubble up.

Helper methods:
- `_load_documents_from_source`: normalizes generator/list return types.
- `_convert_documents_to_dict`: adapts `llama_index.Document` to plain dict for chunker/indexer.

---

## 3. Async Job Orchestrator (`app/ingestion/service.py`)

### 3.1 `IngestionState`
Dataclass persisted to disk:
- Core fields: `status`, `phase`, `progress`, `message`, timestamps.
- Control flags: `paused`, `cancel_requested`.
- Metrics dict filled by pipeline.

### 3.2 Singleton `IngestionService`
- Tracks running tasks per `kb_id` (`_tasks`) with async lock for concurrency control.
- `start(kb_id, run_callable, *args, state_override=None, **kwargs)`:
  - Creates/updates `IngestionState`.
  - Persists initial state to `backend/data/knowledge_bases/{kb_id}/state.json`.
  - Wraps `run_callable` in `asyncio.create_task` to run pipeline cooperatively.
  - On success sets `status=completed`; exceptions mark `failed`.
- `pause`, `resume`, `cancel` toggle flags and persist state; `cancel` also cancels the underlying task.
- `resume_or_start`:
  - If paused state exists, restarts pipeline with same `IngestionState`.
  - Otherwise delegates to `start`.
- `list_kb_states` returns shallow copy for `GET /jobs`.
- Startup integration: `load_all_states` (invoked in `app.lifecycle.startup`) hydrates `_states` from disk for UI continuity.
- Shutdown: `cancel_all` used in `lifecycle.shutdown`.

### 3.3 State Persistence
`_persist_state` writes JSON with sections:
- `job`: live status.
- `metrics`: aggregated stats.
- `crawl` and `processing` updated by downstream components.
Atomic write via temp files prevents corruption.

---

## 4. Knowledge Base Registry (`app/kb/manager.py`)

- Manages `data/knowledge_bases/config.json`.
- `KBConfig` normalizes per-KB settings (paths, models, profiles).
- CRUD methods used by ingestion router:
  - `create_kb` scaffolds directories and updates config.
  - `delete_kb` removes config entry and deletes storage (with Windows-safe retries).
- Provides `get_kb_config` (raw dict) consumed by `start_ingestion`.
- Storage layout:
  ```
  backend/data/knowledge_bases/
    config.json
    {kb_id}/
      documents/              # raw batch dumps
      index/                  # llama-index artifacts
      state.json              # combined job/crawl/processing state
  ```

---

## 5. Source Handling (`app/kb/ingestion/sources`)

### 5.1 Factory (`factory.py`)
- Lowercases `source_type` and lazily imports handler classes:
  - `website`, `youtube`, `pdf`, `markdown`.
- Injects `job`/`state` for cooperative controls.

### 5.2 Website Source (`website`)
- Components:
  - `WebsiteCrawler`: streaming crawl with checkpointing and semantic path filtering.
  - `ContentFetcher`: retrying HTTP fetch + Trafilatura extraction.
  - `SitemapParser`: recursive sitemap parsing.
  - `link_extractor`: HTML anchor-based link extraction used to complement crawling when sitemap coverage is partial or absent.
- Modes:
  1. Explicit `sitemap_url`.
  2. `start_url` (auto sitemap discovery via `trafilatura.sitemaps.sitemap_search`; falls back to crawler).
  3. Direct `urls`.
- Batch yielding: crawler writes to `state.json` (`crawl` section) every `checkpoint_interval`.
- Metadata: each `Document` includes `doc_id`, `url`, `kb_id`, `date_ingested`.

Implementation notes:
- Prefer sitemap-first discovery when available via `trafilatura`.
- When sitemaps are missing/incomplete, rely on crawler traversal and HTML link extraction to expand coverage.

### 5.3 PDF Source (`pdf.py`)
- Uses `llama_index.readers.file.PyMuPDFReader`.
- Supports local paths, URLs (download to temp file), recursive folder ingestion.
- Updates metadata with file info; observes pause/cancel flags.

### 5.4 Markdown Source (`markdown.py`)
- `SimpleDirectoryReader` loads `.md` files.
- Enriches metadata with folder hierarchy (`_extract_hierarchy`).
- Provides `ingest_file` helper for single document.

### 5.5 YouTube Source (`youtube.py`)
- Transcript via `YoutubeTranscriptReader`.
- Distillation:
  - Prompt (`YOUTUBE_DISTILLATION_PROMPT`) instructs LLM `gpt-4o-mini`.
  - Structured output models: `DistilledTranscript`, `KeyConcept`, `TechnicalQA`.
- Produces multiple documents per video (summary, concepts, Q&A) for richer retrieval.

---

## 6. Chunking (`app/kb/ingestion/chunking`)

- `ChunkerFactory`: currently resolves to `SemanticChunker`.
- `SemanticChunker` wraps `SentenceSplitter` from `llama_index` with chunk size/overlap from KB config.
- Chunks enriched with metadata (`chunk_index`, `total_chunks`, `chunking_strategy`).

---

## 7. Index Building (`app/kb/ingestion/indexing`)

### 7.1 Factory
- `IndexBuilderFactory.create_builder` ensures `kb_id` and `storage_dir` provided; defaults to vector index.

### 7.2 `VectorIndexBuilder`
- Configures global `Settings.embed_model` (`OpenAIEmbedding`) and `Settings.llm` for ingestion-time operations.
- Incremental flow:
  1. `_load_state` reads `processing` section from `state.json` to resume at `last_indexed_id`.
  2. Attempts to `load_index_from_storage`; falls back to fresh `VectorStoreIndex`.
  3. Filters new documents based on `doc_id`.
  4. Builds/updates index, persists to `storage_dir`.
  5. `_save_state` writes updated checkpoints (`last_indexed_id`, `chunks_total`, `batches_processed`).
  6. `_save_index_metadata` records embedding/generation models.
- Uses `Document` builder to convert plain dicts back to LlamaIndex structures.

---

## 8. Document Persistence

### 8.1 Batch Dumps (`KBIngestionService._save_documents_to_disk`)
- Markdown snapshots saved as `{doc_id:04d}_{sanitized-page-name}.md`.
- Contains headers with doc ID and source URL for debugging.

### 8.2 State File (`state.json`)
Unified target for:
- `job` (from `IngestionService`).
- `crawl` (from `WebsiteCrawler`).
- `processing` (from `VectorIndexBuilder`).
- `metrics` (combined view).

---

## 9. Cache Invalidation & Query Readiness

- `clear_index_cache` removes in-memory `VectorStoreIndex` stored in `_INDEX_CACHE`.
- `delete_kb` endpoint invokes `clear_index_cache` before removing files.
- Query side (`app/kb/service.py`) lazily (re)loads persisted indices when first used.

---

## 10. Lifecycle Hooks (`app/lifecycle.py`)

- Startup:
  - `init_database`.
  - Instantiate `KBManager` (ensures config loaded).
  - `IngestionService.load_all_states()` to pre-populate job dashboard.
- Shutdown:
  - `cancel_all` to propagate cancel flags and stop tasks before process exit.
  - `close_database`.

---

## 11. Error Handling & Logging

- Router wraps operations in try/except; returns HTTP 400 for validation errors, 500 for unexpected exceptions.
- Pipeline-level exceptions propagate to `IngestionService`, which marks state `failed` and logs stack trace.
- Website crawler catches network errors, retries, logs progress, and saves checkpoints before exiting on pause/cancel.

---

## 12. Extensibility Points

- `SourceHandlerFactory.register_handler` and `ChunkerFactory.register_chunker` allow pluggable strategies.
- `IndexBuilderFactory.register_builder` for future index types (e.g., hybrid).
- `KBIngestionService.run_ingestion_pipeline` expects handlers to honor cooperative pause via shared `state`.

---

## 13. Data Flow Summary

```
HTTP POST /api/ingestion/kb/{kb_id}/start
      |
      v
router.start_ingestion -> KBIngestionService.start_ingestion
      |
      +--> IngestionService.instance().start(
               kb_id,
               KBIngestionService.run_ingestion_pipeline,
               kb_config
           )
             |
             v
       run_ingestion_pipeline
             |
             +-- SourceHandlerFactory -> handler.ingest()
             |      +-- WebsiteCrawler / PDFSourceHandler / ...
             |
             +-- ChunkerFactory -> SemanticChunker.chunk_documents()
             |
             +-- IndexBuilderFactory -> VectorIndexBuilder.build_index()
                      +-- state.json (processing) + llama index artifacts
```

`IngestionState` persists progress; router status endpoints surface it for clients.

---
