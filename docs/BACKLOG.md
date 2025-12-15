**Architecture Backlog**

- **Fix Toast Notifications Not Showing**: Toast notifications replaced alert() calls but don't appear visually in UI.
  - **Problem**: useToast hook called successfully, ToastContainer rendered in App.tsx, but toasts don't display on screen.
  - **Status**: Analyze button works (no black page), StatePanel renders correctly, but user feedback missing.
  - **Priority**: Low - core functionality works, UX improvement only.
  - **Investigation needed**: Check ToastContainer styling, z-index, positioning, or missing CSS imports.

- **Refactor `SourceHandlerFactory` resolution**: Replace hardcoded `if/elif` lazy imports with a clean registry-based factory (or DI at composition root).
  - **Problem**: `register_handler`/`list_handlers` exist but `HANDLERS` is undefined and `create_handler` ignores any registry. Hardcoded branches limit extensibility and testability.
  - **Goal**: Support runtime handler registration (e.g., plugins like `confluence`) while keeping call sites simple.
  - **Plan**:
    - Add `HANDLERS: dict[str, type[BaseSourceHandler]] = {}` inside `SourceHandlerFactory`.
    - In `create_handler`, first check `HANDLERS.get(source_type)`; if present, use it; else fallback to built-in handlers.
    - Validate registered classes inherit `BaseSourceHandler`.
    - Update `list_handlers()` to return registry keys (optionally include built-ins).
    - Add minimal startup hook to register environment-specific handlers.
  - **Why Not Now**: Lower priority vs ingestion resilience; current hardcoded handlers are sufficient.
  - **Risks**: Import side effects; stringly-typed keys. Mitigate with validation and typed constants.

- **Optional DI Integration (later)**: At app bootstrap, register handlers via a lightweight DI container; still delegate to the factory registry for resolution.
  - Keeps both approaches compatible; DI provides per-env overrides without changing call sites.

- **Safe Runtime Cleanup before Ingestion Start (deferred)**
  - Add a scoped, non-destructive `cleanup_runtime(kb_id, runtime)` in `IngestionService` to ensure fresh starts don’t inherit stale thread/stop-event state.
  - Guardrails: KB-targeted only; no queue/item purge; idempotent; logging-first with opt-in resets.
  - Controlled actions to consider later: reset stuck `PROCESSING` items to `PENDING` for latest job; cancel previous job via repository `cancel_job_and_reset(job_id)` when explicitly starting fresh; clear in-memory stop events.
  - Deferred until lifecycle tests and gating stability are validated; not implemented now.

- **Ingestion phase status not updating across resume**
  - **Problem**: When ingestion restarts/resumes, per-phase statuses (loading/chunking/embedding/indexing) in `ingestion_phase_status` stop reflecting live work. UI shows phases completed while crawling/chunking continues; only KPIs move.
  - **Likely causes**: Orchestrator does not consistently start/update phases on resumed batches; phase rows may be left completed or not_started; job-view endpoint only surfaces persisted rows (no inference).
  - **Goal**: Reliable real-time phase state and overall status derived from persisted phase rows across fresh runs and resumes.
  - **Plan**:
    - Audit orchestrator phase writes on resume: ensure start/update_progress/complete are called idempotently for each phase on every batch/chunk (including resumed batches).
    - Add lightweight phase-status reporter wrapper to centralize updates instead of scattered calls.
    - Add a small test/diagnostic to fetch `ingestion_phase_status` during a resumed run to verify transitions.
    - Keep job-view passive: return persisted phase rows; no counter/queue inference.
  - **Priority**: Medium – correctness of status reporting; does not block ingestion output but misleads operators.
