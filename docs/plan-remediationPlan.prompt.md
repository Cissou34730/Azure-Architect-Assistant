## Plan: Ingestion Layered Refactor

Refactor ingestion into clear domain, infrastructure, and application layers, introducing interfaces for state, runtime, workers, repositories, and persistence. Add a lifecycle manager, a reusable asyncio executor, cooperative shutdown semantics, and a typed settings object. Standardize logging/metrics, return domain objects, and expand tests and docs. The plan aims to reduce coupling, improve resiliency, enable pluggable backends, and raise observability.

### Steps
1. Create `backend/app/ingestion/domain/models/` and move `state.py`, `runtime.py`, DTOs; add `__all__` exports and pydantic-compatible schemas.
2. Add `backend/app/ingestion/domain/enums.py` with `JobStatus`, `JobPhase`, and a transition map in a small state machine utility.
3. Define `backend/app/ingestion/domain/interfaces/` for `Repository`, `PersistenceStore`, `LifecycleManager`, `ProducerWorker`, `ConsumerWorker` protocols.
4. Create `backend/app/ingestion/infrastructure/` and relocate `repository.py`, `storage.py`, filesystem/DB helpers; implement factories and injectable instances.
5. Add `backend/app/ingestion/application/ingestion_service.py`; slim `manager.py` to orchestrate start/resume/pause/cancel/status using interfaces only.
6. Introduce `backend/app/ingestion/application/lifecycle.py` to encapsulate thread create/join/cancel with cooperative “queue drained” shutdown checks.
7. Create `backend/app/ingestion/application/executor.py` for safe `asyncio.run` wrappers preventing nested-loop errors and enabling loop reuse.
8. Collapse thread entrypoints into `backend/app/ingestion/workers/` with protocol-based `ProducerWorker`/`ConsumerWorker`; route run logic via lifecycle.
9. Implement `backend/app/ingestion/config/settings.py` typed settings (env or file) for paths, batch sizes, retries; remove literals from producer/consumer/storage.
10. Refine repository return types to domain objects; add structured errors (`DuplicateChunkError`, `QueueEmptyError`) and transactional batch helpers.
11. Abstract persistence via `PersistenceStore` (local disk, Azure Files, Blob) behind an interface; wire through `IngestionService` without service changes.
12. Standardize logging with correlation IDs (`job_id`, `kb_id`) and log levels across threads; add Prometheus-style metrics hooks and a monitoring service.
13. Expand tests: lifecycle threads, DB queue contention, resume-from-checkpoint, persistence edge cases; add fixtures for alternate backends.
14. Update docs in `docs/ingestion/` for module boundaries, configuration knobs, extension points; include diagrams and quick-start examples.
