## OrchestratorSpec Implementation Plan (SQLite, direct vector-store, no limit)

Goal: Implement the clean, sequential orchestrator defined in `backend/docs/ingestion/OrchestratorSpec.md` with minimal reuse (only domain phases), SQLite persistence for checkpoints and counters, and direct vector-store cleanup on cancel.

### Functional Requirements Trace
- WorkflowDefinition: step order `LOAD → CHUNK → EMBED → INDEX` with `get_first_step()` and `get_next_step()`.
- RetryPolicy: max attempts + backoff; applied per-chunk during embed+index.
- ProcessingTask: dataclass for logging/observability.
- Gates: cooperative `check_gate()` polling `jobs.status` among `not_started | running | paused | completed | failed | canceled`.
- Crash safety: batch-level checkpoint `{last_batch_id, cursor}` persisted after each batch; idempotency via `(kb_id, content_hash)`.
- Counters: `{docs_seen, chunks_seen, chunks_processed, chunks_skipped, chunks_error}` persisted on `jobs`.
- Cancel cleanup: delete embeddings/chunks via vector-store client; reset state to `not_started`; clear checkpoint/counters; set `finished_at` and `last_error`.
- API surface: start/pause/resume/cancel/status.

### Deliverables (Files & Modules)
1. `backend/app/ingestion/application/orchestrator.py`
	 - `StepName` enum, `WorkflowDefinition`, `RetryPolicy`, `ProcessingTask`.
	 - `IngestionOrchestrator.run(job_id, kb_id, kb_config)` implementing sequential flow, gates, checkpoints, counters, heartbeat, completion/failure paths, and cleanup.
2. `backend/app/ingestion/domain/loading/loader.py`
	 - `fetch_batches(kb_config, checkpoint)` generator using existing SourceHandlerFactory; yields lists of documents; supports resume via checkpoint cursor/`last_batch_id`.
3. `backend/app/ingestion/domain/chunking/adapter.py`
	 - `create_chunker_from_config(kb_config)`; `chunk_documents_to_chunks(documents)` → `List[Chunk]`.
	 - `Chunk` dataclass with `text`, `content_hash`, `metadata` (compute hash from normalized text + source identifiers).
4. `backend/app/ingestion/domain/embedding/embedder.py`
	 - `Embedder` class with `async embed(chunk: Chunk) -> EmbeddingResult`.
	 - `EmbeddingResult` dataclass includes `vector`, `content_hash`, `metadata`.
5. `backend/app/ingestion/domain/indexing/indexer.py`
	 - `Indexer` with `exists(kb_id, content_hash) -> bool`, `index(kb_id, embedding: EmbeddingResult) -> None`, `delete_by_job(job_id, kb_id) -> None`.
	 - Implemented via direct vector-store client (existing index builder/retriever), adding delete support.
6. `backend/app/routers/ingestion_v2.py`
	 - FastAPI router: `POST /ingestion/jobs/{kb_id}/start`, `POST /ingestion/jobs/{id}/pause`, `POST /ingestion/jobs/{id}/resume`, `POST /ingestion/jobs/{id}/cancel`, `GET /ingestion/jobs/{id}/status`.
	 - Background task spawns orchestrator; uses factory functions to instantiate embedder/indexer.
7. `backend/app/main.py`
	 - Register `ingestion_v2` router.
8. Persistence updates (SQLite)
	 - Job model: add `checkpoint` (JSON), `counters` (JSON), optional `heartbeat_at` (timestamp).
	 - `embeddings_index` uniqueness: `(kb_id, content_hash)` (via DB table or maintained by the vector store metadata).
	 - Repository methods: `get_job(job_id)`, `get_job_status(job_id)`, `update_job(checkpoint, counters)`, `update_heartbeat(job_id)`, `set_job_status(status, finished_at, last_error)`.
9. Tests (minimal but targeted)
	 - Unit: content hash stability, idempotent indexing, RetryPolicy backoff.
	 - Integration: gates pause/resume/cancel, checkpoint resume, cleanup deletes vectors.

### Detailed Task Breakdown
1) Domain Loading
- Implement `fetch_batches(kb_config, checkpoint)`:
	- Use `SourceHandlerFactory.create(kb_config, checkpoint)` from existing domain/sources.
	- Handle `cursor` and `last_batch_id` for resume; yield `List[Document]`.
	- Validate documents (non-empty text, source id present).

2) Domain Chunking
- Implement `Chunk` and adapter functions:
	- `create_chunker_from_config(kb_config)` to instantiate existing chunkers.
	- `chunk_documents_to_chunks(documents)` returns `List[Chunk]`.
	- Compute `content_hash = sha256(normalize(text) + source_id + kb_id)`.

3) Domain Embedding
- Implement `Embedder`:
	- Pure async API: `embed(chunk)` returns `EmbeddingResult` (vector + metadata).
	- Extract existing embedding logic from prior code paths; avoid orchestration dependencies.
	- Ensure deterministic metadata carries `content_hash` and source refs.

4) Domain Indexing (vector-store client)
- Implement `Indexer` against existing services:
	- `exists(kb_id, content_hash)` checks presence via vector-store metadata.
	- `index(kb_id, embedding)` writes vector + metadata; atomic semantics.
	- `delete_by_job(job_id, kb_id)` removes all vectors for the job/kb via client; if client lacks delete, add helper in `services/vector/index_builder.py`.

5) Orchestrator
- Implement `WorkflowDefinition`, `RetryPolicy`, `ProcessingTask`.
- Implement `IngestionOrchestrator.run(...)`:
	- Resolve `job`, `checkpoint`, `counters` (default zeroed map).
	- Initialize components (loader, chunker, embedder, indexer).
	- For each batch (starting from `checkpoint.last_batch_id + 1`):
		- Gate check (`running | paused | canceled`); pause loops sleeping; canceled triggers cleanup.
		- Chunk batch; update `docs_seen`, `chunks_seen`.
		- For each chunk:
			- Gate check.
			- Build `ProcessingTask` for logging.
			- Embed + Index with retry:
				- If `indexer.exists(kb_id, content_hash)`: count `chunks_skipped`.
				- Else try `embed`, then `index`; on success: `chunks_processed`; on failure: `chunks_error`.
				- Retry on transient errors per `RetryPolicy` with `asyncio.sleep(backoff)`.
		- Persist `checkpoint.last_batch_id`, `counters`; heartbeat update.
	- On normal completion: `set_job_status('completed', finished_at=now())`.
	- On exception: `set_job_status('failed', last_error=str(e), finished_at=now())` and re-raise.
	- On cancel: run `_cleanup_job(job_id, kb_id)` then exit.

6) Cleanup Workflow
- `_cleanup_job(job_id, kb_id)`:
	- Call `indexer.delete_by_job(job_id, kb_id)` (direct vector-store client).
	- Reset job: `status='not_started'`, `checkpoint=None`, `counters=None`, `finished_at=now()`, `last_error='Canceled by user'`.
	- Best-effort logging on failure.

7) API Layer
- Router `ingestion_v2` endpoints:
	- `start(kb_id)`: create job `status=running`, spawn background task `orchestrator.run(...)`.
	- `pause(job_id)`: `set_job_status('paused')`.
	- `resume(job_id)`: `set_job_status('running')`.
	- `cancel(job_id)`: `set_job_status('canceled')`; orchestrator cleanup on next gate.
	- `status(job_id)`: return `status`, `counters`, `last_error`, heartbeat age.
	- Factories: `create_embedder`, `create_indexer(kb_id)`.

8) Persistence (SQLite)
- Model updates:
	- Add `checkpoint` (JSON) and `counters` (JSON) to `jobs` table.
	- Add `heartbeat_at` timestamp.
- Migration strategy:
	- Use existing schema versioning helper to apply `ALTER TABLE` for new columns.
	- If JSON unsupported, store as TEXT with JSON serialization; repository marshals values.
- Repository additions:
	- `get_job(job_id)`, `get_job_status(job_id)`.
	- `update_job(job_id, checkpoint, counters)`.
	- `update_heartbeat(job_id)`.
	- `set_job_status(job_id, status, finished_at=None, last_error=None)`.

9) Testing & Validation
- Unit tests:
	- Content hash computation consistency.
	- Indexer `exists` and idempotency behavior.
	- RetryPolicy delays and stop conditions.
- Integration tests:
	- Start → pause → resume → complete with checkpoint resume.
	- Cancel → cleanup deletes vectors → status reset to `not_started`.
	- Crash midway → restart resumes from `last_batch_id` without duplicates.

### Non-Goals / Explicitly Not Reused
- No producer/consumer queues, no phase tracker tables, no old orchestration logic.
- Minimal reuse limited to domain handlers (sources, chunkers) and the vector-store client.

### Implementation Order (Phases)
1. Phase 1 — Domain adapters: loading, chunking, embedding, indexing (interfaces + basic implementations).
2. Phase 2 — Orchestrator core with gates, checkpoints, counters, cleanup.
3. Phase 3 — API router and registration.
4. Phase 4 — SQLite model updates + repository methods.
5. Phase 5 — Tests + deprecate legacy pipeline modules.

### Operational Notes
- Concurrency: no orchestrator limit; jobs run independently.
- Observability: log batch/chunk progress, update counters per batch, heartbeat every 5–10s.
- Backoff: `min(2 ** attempt * backoff_multiplier, 60)` seconds.
