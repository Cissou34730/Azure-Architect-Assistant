# Ingestion Codebase Remediation Implementation Plan

> **Created**: February 8, 2026  
> **Based on**: [review-ingestion-codebase-20260208.md](./review-ingestion-codebase-20260208.md)  
> **Status**: Phase 2 in progress (Task 2.1 implemented; Phase 1.4 audit fixes still pending)

## Executive Summary

This plan addresses all recommendations from the grumpy code review EXCEPT naming convention changes (we keep Python snake_case and TypeScript camelCase per project standards).

**Total Tasks**: 47 across 4 priority levels  
**Estimated Time**: 2-3 weeks  
**Risk Level**: Medium (touches core orchestration logic)

## Baseline Implementation Checklist (Repo Reality Check)

This section tracks what’s already true in the repo vs. what this plan still needs to implement.

- [x] Confirmed bare `except Exception` still present in backend ingestion DB utilities
- [x] Settings loading no longer uses bare `except Exception` (now catches `ValidationError`/`SettingsError`/`FileNotFoundError` and logs fallback)
- [ ] Transaction scope `get_session()` still catches broad `Exception` to rollback (intentional; revisit if you want BLE001-clean)
- [x] Removed `contextlib.suppress(Exception)` from ingestion orchestrator (now logs non-critical phase persistence failures)
- [x] Removed `asyncio.run()` + `run_until_complete()` fallback pattern in ingestion OpenAI embedder (now fails fast with clear message if called in a running event loop)
- [x] Confirmed orchestrator no longer uses module-level global shutdown event
- [x] Ingestion schema migrations now use Alembic (ingestion environment + initial migration)
- [x] Confirmed SQLAlchemy datetime columns still use `default=lambda: datetime.now(timezone.utc)`
- [x] Confirmed ingestion “Prometheus-style” metrics are still custom (not `prometheus_client`)
- [x] Confirmed frontend ingestion components still contain `void ` promise casts
- [x] Confirmed React `ErrorBoundary` exists, but ingestion route is not wrapped

---

## Phase 1: 🔴 CRITICAL Issues (Do First)

### Task 1.1: Fix Backend Exception Handling - Settings Loading
**Priority**: P0  
**File**: `backend/app/ingestion/ingestion_database.py`  
**Lines**: 31-33  
**Estimated Time**: 30 minutes

**Current Code**:
```python
try:
    app_settings = get_app_settings()
except Exception:  # noqa: BLE001
    app_settings = None
```

**Implementation Steps**:
1. Import specific exceptions from settings module
2. Replace bare `except Exception` with specific exceptions:
   - `ConfigurationError`
   - `FileNotFoundError`
   - `ValidationError`
3. Add proper logging for each exception type
4. Decide fallback behavior (raise vs. default)

**Success Criteria**:
- [x] Settings loading no longer uses bare `except Exception`
- [x] All settings-load exceptions are logged with context
- [ ] Tests added for each exception path
- [ ] Mypy passes without suppressions

---

### Task 1.2: Fix Exception Suppression in Orchestrator - Progress Updates
**Priority**: P0  
**File**: `backend/app/ingestion/application/orchestrator.py`  
**Lines**: 175-177, 180-188, 294-297, and all other occurrences  
**Estimated Time**: 2 hours

**Current Pattern**:
```python
with contextlib.suppress(Exception):
    self.phase_repo.update_progress(...)
```

**Implementation Steps**:
1. Audit all `contextlib.suppress(Exception)` calls in orchestrator.py (search for pattern)
2. For each occurrence:
   - Identify what specific exceptions are expected (e.g., `PhaseNotFoundError`, `DatabaseConnectionError`)
   - Replace with explicit try/except
   - Add logging with structured context (phase_id, kb_id, operation)
   - Determine if operation is truly optional or should propagate
3. Create custom exception class `NonCriticalPhaseError` for cases that should be suppressed
4. Update only truly non-critical operations to suppress `NonCriticalPhaseError`

**Example Replacement**:
```python
try:
    self.phase_repo.update_progress(phase_id, progress, message)
except (PhaseNotFoundError, DatabaseConnectionError) as e:
    logger.warning(
        "Failed to update phase progress (non-critical)",
        extra={
            "phase_id": phase_id,
            "progress": progress,
            "error": str(e),
            "error_type": type(e).__name__
        }
    )
except Exception as e:
    logger.error(
        "Unexpected error updating phase progress",
        extra={"phase_id": phase_id, "error": str(e)},
        exc_info=True
    )
    # Decide: re-raise or continue?
```

**Success Criteria**:
- [x] Zero `contextlib.suppress(Exception)` in orchestrator.py
- [x] All phase persistence failures are logged with context (job_id/phase_name/op)
- [ ] Custom exception classes created for domain-specific errors
- [ ] Tests cover exception paths
- [ ] Documentation updated with error handling strategy

---

### Task 1.3: Fix Event Loop Anti-Pattern in Embedder
**Priority**: P0  
**File**: `backend/app/ingestion/infrastructure/embedding/openai_embedder.py`  
**Lines**: 62-68  
**Estimated Time**: 3 hours

**Current Code**:
```python
def _execute_batch_embedding(self, texts: list[str]) -> list[list[float]]:
    try:
        return asyncio.run(self.ai_service.embed_batch(texts))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.ai_service.embed_batch(texts))
```

**Implementation Steps**:

**Option A: Make embedder async (Recommended)**
1. Change `OpenAIEmbedder` interface to async:
   ```python
   async def embed_batch(self, texts: list[str]) -> list[list[float]]:
       return await self.ai_service.embed_batch(texts)
   ```
2. Update all callers in orchestrator to await:
   ```python
   embeddings = await self.embedder.embed_batch(chunk_texts)
   ```
3. Ensure orchestrator methods calling embedder are async (they likely already are)

**Option B: Use thread pool (if sync interface required)**
1. Import `asyncio.to_thread`
2. Replace implementation:
   ```python
   def _execute_batch_embedding(self, texts: list[str]) -> list[list[float]]:
       # Run async function in thread pool
       return asyncio.run(self._embed_async(texts))
   
   async def _embed_async(self, texts: list[str]) -> list[list[float]]:
       return await self.ai_service.embed_batch(texts)
   ```

**Success Criteria**:
- [x] No `asyncio.run()` + `run_until_complete()` fallback pattern
- [x] Event loop handling fails fast with a clear error when called from a running loop
- [ ] Tests pass for both sync and async contexts
- [ ] Performance benchmarks show no regression
- [ ] Code review by async-savvy developer

---

### Task 1.4: Audit All Other Exception Suppressions
**Priority**: P0  
**Files**: All files in `backend/app/ingestion/`  
**Estimated Time**: 2 hours

**Implementation Steps**:
1. Run grep search: `grep -r "contextlib.suppress" backend/app/ingestion/`
2. Run grep search: `grep -r "except Exception:" backend/app/ingestion/`
3. Create spreadsheet of all occurrences:
   - File path
   - Line number
   - Context (what operation)
   - Current exception handling
   - Proposed fix
4. Prioritize by risk (database writes > progress updates > logging)
5. Apply same fix pattern as Task 1.2 to each

**Audit Snapshot (February 8, 2026)**
- `contextlib.suppress(...)` occurrences in `backend/app/ingestion/`: **0**
- `except Exception` occurrences in `backend/app/ingestion/`: **20**
  - `backend/app/ingestion/application/orchestrator.py`: lines 104, 184, 197, 422, 495, 564
  - `backend/app/ingestion/ingestion_database.py`: line 72
  - `backend/app/ingestion/domain/embedding/embedder.py`: line 95
  - `backend/app/ingestion/domain/loading/loader.py`: line 76
  - `backend/app/ingestion/domain/indexing/indexer.py`: lines 186, 214, 227
  - `backend/app/ingestion/domain/sources/youtube.py`: line 221
  - `backend/app/ingestion/domain/sources/markdown.py`: lines 86, 123
  - `backend/app/ingestion/domain/sources/pdf.py`: lines 102, 143
  - `backend/app/ingestion/domain/sources/website/content_fetcher.py`: line 65
  - `backend/app/ingestion/infrastructure/queue_repository.py`: line 162
  - `backend/app/ingestion/migrations/add_orchestrator_fields.py`: line 65

**Success Criteria**:
- [x] Initial audit snapshot recorded in this plan
- [x] `contextlib.suppress(...)` eliminated in `backend/app/ingestion/`
- [ ] High-risk suppressions eliminated
- [ ] Medium-risk suppressions have specific exception types
- [ ] Low-risk suppressions logged properly

---

## Phase 2: 🟡 MAJOR Issues (Do Second)

### Task 2.1: Refactor Orchestrator - Extract Pipeline Stages
**Priority**: P1  
**File**: `backend/app/ingestion/application/orchestrator.py`  
**Estimated Time**: 8 hours

**Current Problem**: 400+ line file with God Object anti-pattern

**Implementation Steps**:

1. **Create Pipeline Stage Interface** (1 hour)
   - File: `backend/app/ingestion/application/pipeline_stage.py`
   ```python
   from abc import ABC, abstractmethod
   from typing import Protocol
   
   class PipelineContext:
       """Shared context across pipeline stages"""
       def __init__(self, kb_id: str, job_id: str, config: dict):
           self.kb_id = kb_id
           self.job_id = job_id
           self.config = config
           self.results: dict[str, Any] = {}
   
   class PipelineStage(ABC):
       """Base class for pipeline stages"""
       
       @abstractmethod
       async def execute(self, context: PipelineContext) -> None:
           """Execute this stage of the pipeline"""
           pass
       
       @abstractmethod
       def get_stage_name(self) -> str:
           """Return human-readable stage name"""
           pass
   ```

2. **Extract Loading Stage** (1.5 hours)
   - File: `backend/app/ingestion/application/stages/loading_stage.py`
   - Extract logic from `_run_load_phase` method
   - Structure:
     ```python
     class LoadingStage(PipelineStage):
         def __init__(self, job_repo, phase_repo, loader_factory):
             self.job_repo = job_repo
             self.phase_repo = phase_repo
             self.loader_factory = loader_factory
         
         async def execute(self, context: PipelineContext) -> None:
             # Move logic from _run_load_phase here
             loader = self.loader_factory.create(context.config["source_type"])
             documents = await loader.load(context.config["source_config"])
             context.results["documents"] = documents
             await self.phase_repo.complete_phase(context.kb_id, "load")
     ```

3. **Extract Chunking Stage** (1.5 hours)
   - File: `backend/app/ingestion/application/stages/chunking_stage.py`
   - Extract logic from `_run_chunk_phase`
   - Similar structure to LoadingStage

4. **Extract Embedding & Indexing Stage** (2 hours)
   - File: `backend/app/ingestion/application/stages/embedding_stage.py`
   - Extract logic from `_run_embed_and_index_phase`
   - Handle progress callback complexity

5. **Create Pipeline Coordinator** (2 hours)
   - Refactor `IngestionOrchestrator` to coordinate stages:
   ```python
   class IngestionOrchestrator:
       def __init__(self, stages: list[PipelineStage], ...):
           self.stages = stages
       
       async def run_pipeline(self, kb_id: str, job_id: str) -> None:
           context = PipelineContext(kb_id, job_id, self._load_config(kb_id))
           
           for stage in self.stages:
               if self._should_stop(context):
                   break
               
               logger.info(f"Starting stage: {stage.get_stage_name()}")
               await stage.execute(context)
               logger.info(f"Completed stage: {stage.get_stage_name()}")
   ```

**Success Criteria**:
- [x] Orchestrator.py is < 200 lines
- [x] Each stage is in separate file
- [x] Each stage is < 100 lines
- [x] Each stage has unit tests
- [ ] Integration tests pass
- [x] No regression in unit-test functionality

---

### Task 2.2: Fix Migration System - Implement Proper Migrations
**Priority**: P1  
**File**: `backend/app/ingestion/ingestion_schema.py`  
**Lines**: 34-52  
**Estimated Time**: 4 hours

**Current Problem**: Placeholder migration system with no upgrade path

**Implementation Steps**:

1. **Audit Alembic Configuration** (30 minutes)
   - Check if `alembic.ini` is configured for ingestion schema
   - File: `backend/alembic.ini`
   - Ensure separate migration path for ingestion vs. main app

2. **Create Alembic Environment for Ingestion** (1 hour)
   - Directory: `backend/migrations/ingestion/`
   - Initialize: `alembic init backend/migrations/ingestion`
   - Configure `env.py` to use ingestion models
   - Update `alembic.ini` with ingestion connection string

3. **Generate Initial Migration** (1 hour)
   - Create baseline migration from current schema:
     ```bash
     alembic -c alembic_ingestion.ini revision --autogenerate -m "initial_ingestion_schema"
     ```
   - Review generated migration
   - Add data migrations if needed (populate default values)

4. **Create Migration for Current State** (30 minutes)
   - Mark current production schema version
   - Create stamp command for existing databases:
     ```bash
     alembic -c alembic_ingestion.ini stamp head
     ```

5. **Update Schema Init Code** (1 hour)
   - File: `backend/app/ingestion/ingestion_schema.py`
   - Replace manual schema version checking with Alembic
   - Update `ensure_schema()` to use Alembic programmatically:
     ```python
     from alembic.config import Config
     from alembic import command
     
     def ensure_schema():
         alembic_cfg = Config("alembic_ingestion.ini")
         command.upgrade(alembic_cfg, "head")
     ```

6. **Add Migration Testing** (1 hour)
   - Create test that applies migrations to empty database
   - Create test that applies migrations to previous version
   - Verify forward and rollback work

**Success Criteria**:
- [x] Alembic configured for ingestion schema
- [x] Initial migration created and tested
- [x] Schema init code uses Alembic
- [ ] Migration guide added to docs
- [x] Tests verify upgrade path

---

### Task 2.3: Remove Manual Enum Mapping Duplication
**Priority**: P1  
**File**: `backend/app/ingestion/infrastructure/job_repository.py`  
**Lines**: 84-91, 147, 167  
**Estimated Time**: 1 hour

**Current Problem**: Same status mapping dict repeated 3 times

**Implementation Steps**:

1. **Create Helper Method** (20 minutes)
   - Add to `JobRepository` class:
   ```python
   @staticmethod
   def _map_status_to_db(status: str) -> str:
       """Map API status string to database enum value"""
       status_map = {
           'not_started': DBJobStatus.NOT_STARTED.value,
           'running': DBJobStatus.RUNNING.value,
           'completed': DBJobStatus.COMPLETED.value,
           'failed': DBJobStatus.FAILED.value,
           'cancelled': DBJobStatus.CANCELLED.value,
           'paused': DBJobStatus.PAUSED.value,
       }
       if status not in status_map:
           raise ValueError(f"Invalid status: {status}")
       return status_map[status]
   
   @staticmethod
   def _map_status_from_db(db_status: str) -> str:
       """Map database enum value to API status string"""
       reverse_map = {
           DBJobStatus.NOT_STARTED.value: 'not_started',
           DBJobStatus.RUNNING.value: 'running',
           DBJobStatus.COMPLETED.value: 'completed',
           DBJobStatus.FAILED.value: 'failed',
           DBJobStatus.CANCELLED.value: 'cancelled',
           DBJobStatus.PAUSED.value: 'paused',
       }
       return reverse_map.get(db_status, db_status)
   ```

2. **Replace All Occurrences** (20 minutes)
   - Line 84-91: Replace with `self._map_status_to_db(status)`
   - Line 147: Replace with `self._map_status_to_db(status)`
   - Line 167: Replace with `self._map_status_from_db(row["status"])`

3. **Add Tests** (20 minutes)
   - Test valid status mappings
   - Test invalid status raises ValueError
   - Test round-trip mapping (to_db then from_db)

**Success Criteria**:
- [x] No duplicate mapping dicts
- [x] All mappings use helper methods
- [x] Tests cover all status values
- [x] ValueError raised for invalid status

---

### Task 2.4: Remove Global Shutdown Event
**Priority**: P1  
**File**: `backend/app/ingestion/application/orchestrator.py`  
**Lines**: 56-57  
**Estimated Time**: 2 hours

**Current Problem**: Module-level global state shared across all instances

**Implementation Steps**:

1. **Make Shutdown Event Instance-Level** (30 minutes)
   - Remove module-level `_shutdown_event`
   - Add to `__init__`:
     ```python
     def __init__(self, ...):
         self._shutdown_event = asyncio.Event()
     ```
   - Update all references to use `self._shutdown_event`

2. **Create Shutdown Manager** (1 hour)
   - File: `backend/app/ingestion/application/shutdown_manager.py`
   ```python
   class ShutdownManager:
       """Manages graceful shutdown for ingestion jobs"""
       
       def __init__(self):
           self._shutdown_events: dict[str, asyncio.Event] = {}
       
       def register_job(self, job_id: str) -> asyncio.Event:
           """Register a job and return its shutdown event"""
           event = asyncio.Event()
           self._shutdown_events[job_id] = event
           return event
       
       def request_shutdown(self, job_id: str | None = None) -> None:
           """Request shutdown for specific job or all jobs"""
           if job_id:
               if event := self._shutdown_events.get(job_id):
                   event.set()
           else:
               for event in self._shutdown_events.values():
                   event.set()
       
       def unregister_job(self, job_id: str) -> None:
           """Remove job from tracking after completion"""
           self._shutdown_events.pop(job_id, None)
   ```

3. **Integrate Shutdown Manager** (30 minutes)
   - Add ShutdownManager as dependency injection to orchestrator
   - Update orchestrator to register/unregister on job start/end
   - Update signal handlers to use ShutdownManager

4. **Add Tests** (30 minutes)
   - Test job-specific shutdown
   - Test global shutdown
   - Test multiple concurrent jobs

**Success Criteria**:
- [x] No module-level mutable state
- [x] Each job has isolated shutdown control
- [x] Signal handlers work correctly
- [x] Tests verify isolation between jobs

---

### Task 2.5: Fix SQLAlchemy Datetime Defaults
**Priority**: P1  
**File**: `backend/app/ingestion/models.py`  
**Lines**: 75-77 (and similar occurrences)  
**Estimated Time**: 1 hour

**Current Problem**: Lambda defaults instead of database-level defaults

**Implementation Steps**:

1. **Audit All Datetime Columns** (15 minutes)
   - Search for `DateTime` columns in models.py
   - List all columns using `default=lambda: datetime.now(timezone.utc)`

2. **Update to Server-Side Defaults** (30 minutes)
   - Change all occurrences to:
     ```python
     from sqlalchemy import func
     
     created_at: Mapped[datetime] = mapped_column(
         DateTime(timezone=True),
         nullable=False,
         server_default=func.now()
     )
     ```
   - Or for UTC-specific:
     ```python
     created_at: Mapped[datetime] = mapped_column(
         DateTime(timezone=True),
         nullable=False,
         server_default=text("(CURRENT_TIMESTAMP)")
     )
     ```

3. **Create Alembic Migration** (15 minutes)
   - Generate migration for column default changes
   - Test migration on dev database

4. **Update Tests** (15 minutes)
   - Verify timestamps are set by database
   - Test that timezone is UTC

**Success Criteria**:
- [ ] All datetime columns use server_default
- [ ] No lambda defaults in models
- [ ] Migration created and tested
- [ ] Timestamps use database time, not app server time

---

## Phase 3: 🟠 MODERATE Issues (Do Third)

### Task 3.1: Replace Custom Metrics with Prometheus
**Priority**: P2  
**File**: `backend/app/ingestion/observability/metrics.py`  
**Estimated Time**: 4 hours

**Current Problem**: Custom metrics implementation instead of standard library

**Implementation Steps**:

1. **Add Prometheus Client Dependency** (15 minutes)
   ```bash
   uv add prometheus-client
   ```

2. **Create Prometheus Metrics Module** (1 hour)
   - File: `backend/app/ingestion/observability/prometheus_metrics.py`
   ```python
   from prometheus_client import Counter, Gauge, Histogram, Info
   
   # Job metrics
   ingestion_jobs_total = Counter(
       'ingestion_jobs_total',
       'Total number of ingestion jobs started',
       ['kb_id', 'source_type']
   )
   
   ingestion_jobs_duration_seconds = Histogram(
       'ingestion_jobs_duration_seconds',
       'Duration of ingestion jobs in seconds',
       ['kb_id', 'status']
   )
   
   ingestion_jobs_active = Gauge(
       'ingestion_jobs_active',
       'Number of currently active ingestion jobs'
   )
   
   # Document metrics
   ingestion_documents_processed = Counter(
       'ingestion_documents_processed_total',
       'Total number of documents processed',
       ['kb_id', 'stage']
   )
   
   # Chunk metrics
   ingestion_chunks_created = Counter(
       'ingestion_chunks_created_total',
       'Total number of chunks created',
       ['kb_id']
   )
   
   # Embedding metrics
   ingestion_embeddings_generated = Counter(
       'ingestion_embeddings_generated_total',
       'Total number of embeddings generated',
       ['kb_id', 'model']
   )
   
   ingestion_embedding_duration_seconds = Histogram(
       'ingestion_embedding_duration_seconds',
       'Duration of embedding generation',
       ['model'],
       buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
   )
   ```

3. **Create Compatibility Wrapper** (1 hour)
   - Keep existing `IngestionMetrics` interface
   - Implement using Prometheus underneath:
   ```python
   class IngestionMetrics:
       """Metrics collector using Prometheus"""
       
       def track_job_start(self, kb_id: str, source_type: str) -> None:
           ingestion_jobs_total.labels(
               kb_id=kb_id,
               source_type=source_type
           ).inc()
           ingestion_jobs_active.inc()
       
       def track_job_complete(self, kb_id: str, duration: float, status: str) -> None:
           ingestion_jobs_duration_seconds.labels(
               kb_id=kb_id,
               status=status
           ).observe(duration)
           ingestion_jobs_active.dec()
       
       # ... etc
   ```

4. **Add Prometheus Endpoint** (30 minutes)
   - File: `backend/app/routes/metrics.py` (if not exists)
   ```python
   from fastapi import APIRouter
   from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
   
   router = APIRouter()
   
   @router.get("/metrics")
   async def metrics():
       return Response(
           content=generate_latest(),
           media_type=CONTENT_TYPE_LATEST
       )
   ```

5. **Update All Metric Calls** (1 hour)
   - Search for current metrics usage
   - Update to use new interface
   - Remove old custom metrics implementation

6. **Add Grafana Dashboard** (30 minutes)
   - Create JSON dashboard definition
   - File: `backend/app/ingestion/observability/grafana_dashboard.json`

**Success Criteria**:
- [ ] Prometheus client installed
- [ ] All metrics exposed in Prometheus format
- [ ] /metrics endpoint returns valid metrics
- [ ] Grafana dashboard created
- [ ] Old custom metrics code removed
- [ ] Documentation updated with metrics guide

---

### Task 3.2: Fix Frontend Promise Void Casting
**Priority**: P2  
**Files**: Multiple files in `frontend/src/components/ingestion/`  
**Lines**: Various (search for `void ` pattern)  
**Estimated Time**: 2 hours

**Current Problem**: Silent promise failures with void keyword

**Implementation Steps**:

1. **Search for All Void Casts** (15 minutes)
   ```bash
   cd frontend
   grep -r "void " src/components/ingestion/
   ```
   - Create list of all files and locations

2. **Create Error Handler Utility** (30 minutes)
   - File: `frontend/src/utils/errorHandlers.ts`
   ```typescript
   export function handleAsyncError(
     error: unknown,
     context: string
   ): void {
     console.error(`Error in ${context}:`, error);
     
     // Show toast notification
     toast.error(
       `Failed to ${context}. Please try again.`,
       { duration: 5000 }
     );
     
     // Optional: Send to error tracking service
     // trackError(error, { context });
   }
   
   export function wrapAsync<T>(
     promise: Promise<T>,
     context: string
   ): void {
     promise.catch((error) => handleAsyncError(error, context));
   }
   ```

3. **Fix Each Void Cast** (1 hour)
   - Example from KBList.tsx line 51:
   
   **Before**:
   ```tsx
   onClick={() => {
     onRefresh();
     void refetchJobs();
   }}
   ```
   
   **After (Option A - async handler)**:
   ```tsx
   onClick={async () => {
     onRefresh();
     try {
       await refetchJobs();
     } catch (error) {
       handleAsyncError(error, 'refresh jobs');
     }
   }}
   ```
   
   **After (Option B - wrapper)**:
   ```tsx
   onClick={() => {
     onRefresh();
     wrapAsync(refetchJobs(), 'refresh jobs');
   }}
   ```

4. **Add Loading States** (15 minutes)
   - For user-triggered actions, add loading state:
   ```tsx
   const [isRefreshing, setIsRefreshing] = useState(false);
   
   const handleRefresh = async () => {
     setIsRefreshing(true);
     try {
       await refetchJobs();
     } catch (error) {
       handleAsyncError(error, 'refresh jobs');
     } finally {
       setIsRefreshing(false);
     }
   };
   
   <button onClick={handleRefresh} disabled={isRefreshing}>
     {isRefreshing ? 'Refreshing...' : 'Refresh'}
   </button>
   ```

**Success Criteria**:
- [ ] No `void ` casts in frontend code
- [ ] All promise errors handled explicitly
- [ ] Error handler utility created
- [ ] User sees error messages for failures
- [ ] Loading states added for user actions

---

### Task 3.3: Convert IngestionWorkspace to useReducer
**Priority**: P2  
**File**: `frontend/src/components/ingestion/IngestionWorkspace.tsx`  
**Lines**: 14-16  
**Estimated Time**: 3 hours

**Current Problem**: Multiple related state variables instead of state machine

**Implementation Steps**:

1. **Define State Type** (30 minutes)
   - File: `frontend/src/components/ingestion/workspaceReducer.ts`
   ```typescript
   export type View = "list" | "create" | "progress" | "details";
   
   export interface WorkspaceState {
     view: View;
     selectedKbId: string | null;
     selectedJobId: string | null;
     isPending: boolean;
   }
   
   export type WorkspaceAction =
     | { type: "VIEW_LIST" }
     | { type: "VIEW_CREATE" }
     | { type: "VIEW_PROGRESS"; kbId: string; jobId: string }
     | { type: "VIEW_DETAILS"; kbId: string }
     | { type: "START_TRANSITION" }
     | { type: "END_TRANSITION" };
   
   export const initialState: WorkspaceState = {
     view: "list",
     selectedKbId: null,
     selectedJobId: null,
     isPending: false,
   };
   ```

2. **Implement Reducer** (45 minutes)
   ```typescript
   export function workspaceReducer(
     state: WorkspaceState,
     action: WorkspaceAction
   ): WorkspaceState {
     switch (action.type) {
       case "VIEW_LIST":
         return {
           ...state,
           view: "list",
           selectedKbId: null,
           selectedJobId: null,
         };
       
       case "VIEW_CREATE":
         return {
           ...state,
           view: "create",
           selectedKbId: null,
           selectedJobId: null,
         };
       
       case "VIEW_PROGRESS":
         return {
           ...state,
           view: "progress",
           selectedKbId: action.kbId,
           selectedJobId: action.jobId,
         };
       
       case "VIEW_DETAILS":
         return {
           ...state,
           view: "details",
           selectedKbId: action.kbId,
           selectedJobId: null,
         };
       
       case "START_TRANSITION":
         return { ...state, isPending: true };
       
       case "END_TRANSITION":
         return { ...state, isPending: false };
       
       default:
         return state;
     }
   }
   ```

3. **Update Component** (1 hour)
   ```typescript
   import { useReducer, useTransition } from 'react';
   import { workspaceReducer, initialState } from './workspaceReducer';
   
   export function IngestionWorkspace() {
     const [state, dispatch] = useReducer(workspaceReducer, initialState);
     const [isPending, startTransition] = useTransition();
     
     const handleViewProgress = (kbId: string, jobId: string) => {
       startTransition(() => {
         dispatch({ type: "VIEW_PROGRESS", kbId, jobId });
       });
     };
     
     const handleBackToList = () => {
       startTransition(() => {
         dispatch({ type: "VIEW_LIST" });
       });
     };
     
     // ... render based on state.view
   }
   ```

4. **Add Tests** (45 minutes)
   - File: `frontend/src/components/ingestion/workspaceReducer.test.ts`
   - Test each action type
   - Test invalid state transitions
   - Test that selectedKbId is cleared when returning to list

**Success Criteria**:
- [ ] Single useReducer instead of multiple useState
- [ ] All state transitions go through reducer
- [ ] Impossible states are prevented
- [ ] Tests cover all actions
- [ ] Component is easier to understand

---

### Task 3.4: Fix Wizard Step Logic Duplication
**Priority**: P2  
**File**: `frontend/src/components/ingestion/CreateKBWizard.tsx`  
**Lines**: 22-35  
**Estimated Time**: 1 hour

**Current Problem**: WIZARD_STEPS array defined twice in handlers

**Implementation Steps**:

1. **Extract Constant** (15 minutes)
   - Move to top of file:
   ```typescript
   const WIZARD_STEP_ORDER: WizardStep[] = ["basic", "source", "config", "review"];
   
   const WIZARD_STEPS = {
     basic: { title: "Basic Info", description: "..." },
     source: { title: "Data Source", description: "..." },
     config: { title: "Configuration", description: "..." },
     review: { title: "Review", description: "..." },
   };
   ```

2. **Create Navigation Helpers** (30 minutes)
   ```typescript
   function getNextStep(current: WizardStep): WizardStep | null {
     const currentIndex = WIZARD_STEP_ORDER.indexOf(current);
     if (currentIndex === -1 || currentIndex === WIZARD_STEP_ORDER.length - 1) {
       return null;
     }
     return WIZARD_STEP_ORDER[currentIndex + 1];
   }
   
   function getPreviousStep(current: WizardStep): WizardStep | null {
     const currentIndex = WIZARD_STEP_ORDER.indexOf(current);
     if (currentIndex <= 0) {
       return null;
     }
     return WIZARD_STEP_ORDER[currentIndex - 1];
   }
   
   function isFirstStep(current: WizardStep): boolean {
     return WIZARD_STEP_ORDER.indexOf(current) === 0;
   }
   
   function isLastStep(current: WizardStep): boolean {
     return WIZARD_STEP_ORDER.indexOf(current) === WIZARD_STEP_ORDER.length - 1;
   }
   ```

3. **Update Handlers** (15 minutes)
   ```typescript
   const handleNext = () => {
     const nextStep = getNextStep(step);
     if (nextStep) {
       setStep(nextStep);
     }
   };
   
   const handleBack = () => {
     const prevStep = getPreviousStep(step);
     if (prevStep) {
       setStep(prevStep);
     }
   };
   ```

4. **Update Button Rendering** (10 minutes)
   ```typescript
   <Button
     variant="outline"
     onClick={handleBack}
     disabled={isFirstStep(step)}
   >
     Back
   </Button>
   
   {!isLastStep(step) ? (
     <Button onClick={handleNext}>Next</Button>
   ) : (
     <Button onClick={handleSubmit}>Create Knowledge Base</Button>
   )}
   ```

**Success Criteria**:
- [ ] No duplicate step arrays
- [ ] Single source of truth for step order
- [ ] Helper functions for navigation
- [ ] Easy to add/remove/reorder steps

---

### Task 3.5: Consolidate API Action Functions
**Priority**: P2  
**File**: `frontend/src/services/ingestionApi.ts`  
**Lines**: 68-100  
**Estimated Time**: 1 hour

**Current Problem**: Three nearly identical functions for pause/resume/cancel

**Implementation Steps**:

1. **Create Generic Action Function** (30 minutes)
   ```typescript
   type JobAction = 'pause' | 'resume' | 'cancel';
   
   interface JobActionResponse {
     status: string;
     message: string;
   }
   
   async function executeJobAction(
     kbId: string,
     action: JobAction
   ): Promise<JobActionResponse> {
     return fetchWithErrorHandling<JobActionResponse>(
       `${API_BASE}/ingestion/kb/${kbId}/${action}`,
       { method: "POST" },
       `${action} ingestion`
     );
   }
   ```

2. **Create Specific Wrappers** (15 minutes)
   ```typescript
   export async function pauseIngestion(
     kbId: string
   ): Promise<JobActionResponse> {
     return executeJobAction(kbId, 'pause');
   }
   
   export async function resumeIngestion(
     kbId: string
   ): Promise<JobActionResponse> {
     return executeJobAction(kbId, 'resume');
   }
   
   export async function cancelIngestion(
     kbId: string
   ): Promise<JobActionResponse> {
     return executeJobAction(kbId, 'cancel');
   }
   ```

3. **Update Tests** (15 minutes)
   - Add tests for executeJobAction
   - Verify each wrapper calls with correct action

**Success Criteria**:
- [ ] No duplicate fetch logic
- [ ] Easy to add new actions
- [ ] Tests cover generic function
- [ ] Public API unchanged (backward compatible)

---

## Phase 4: 🔵 MINOR Issues (Do Last)

### Task 4.1: Add Documentation for Magic Numbers
**Priority**: P3  
**File**: `backend/app/ingestion/infrastructure/embedding/openai_embedder.py`  
**Lines**: 20-24  
**Estimated Time**: 30 minutes

**Implementation Steps**:

1. **Add Explanatory Comments** (15 minutes)
   ```python
   # Maximum length for document IDs to avoid index key size limits
   # Most vector stores have 255-char limits; we use 200 for safety margin
   MAX_DOC_ID_LENGTH = 200
   
   # Report progress callback every N documents during embedding
   # Balance between real-time updates and callback overhead
   PROGRESS_CB_INTERVAL = 10
   
   # Progress percentage values for embedding phase
   # Embedding phase spans 25%-75% of total ingestion progress
   # (Load: 0-25%, Chunk: N/A shown during load, Embed: 25-75%, Index: 75-100%)
   EMBEDDING_P_START = 25  # Start of embedding in overall progress
   EMBEDDING_P_SPAN = 50   # Span of embedding phase (75 - 25)
   EMBEDDING_P_END = 75    # End of embedding in overall progress
   ```

2. **Create Configuration Section** (15 minutes)
   - Move to class-level with docstring:
   ```python
   class OpenAIEmbedder:
       """
       OpenAI embedding provider with batching and progress tracking.
       
       Configuration Constants:
           MAX_DOC_ID_LENGTH: Maximum character length for document identifiers
                            to comply with vector store limitations (200 chars)
           
           PROGRESS_CB_INTERVAL: Number of documents between progress callbacks
                                during batch embedding (10 documents)
           
           EMBEDDING_P_START: Starting progress percentage for embedding phase
                            in overall pipeline (25%)
           
           EMBEDDING_P_SPAN: Progress span allocated to embedding phase (50%)
           
           EMBEDDING_P_END: Ending progress percentage for embedding phase (75%)
       """
   ```

**Success Criteria**:
- [ ] All magic numbers have explanatory comments
- [ ] Rationale for values documented
- [ ] Easy to find and modify if needed

---

### Task 4.2: Add Type Annotations (Enable Strict Mypy)
**Priority**: P3  
**Files**: Various backend files  
**Estimated Time**: 4 hours

**Implementation Steps**:

1. **Update Mypy Config** (15 minutes)
   - File: `mypy.ini`
   ```ini
   [mypy]
   python_version = 3.10
   strict = True
   warn_return_any = True
   warn_unused_configs = True
   disallow_untyped_defs = True
   disallow_any_generics = True
   
   [mypy-backend.app.ingestion.*]
   disallow_any_explicit = True
   disallow_any_expr = False  # Gradually enable
   ```

2. **Run Mypy and Generate Error Report** (30 minutes)
   ```bash
   mypy backend/app/ingestion/ > mypy_errors.txt 2>&1
   ```
   - Count errors
   - Categorize by type (Any, missing return type, etc.)

3. **Fix Type Annotations** (3 hours)
   - Priority order:
     1. Public API functions (most important)
     2. Return types
     3. Function parameters
     4. Local variables (only where needed)
   
   - Common fixes:
     ```python
     # Before
     def process_documents(docs):
         ...
     
     # After
     def process_documents(docs: list[Document]) -> list[Chunk]:
         ...
     ```
   
   - Replace `Any` with proper types:
     ```python
     # Before
     config: dict[str, Any]
     
     # After
     from typing import TypedDict
     
     class LoaderConfig(TypedDict):
         source_type: str
         path: str
         options: dict[str, str | int | bool]
     
     config: LoaderConfig
     ```

4. **Run Mypy Until Clean** (15 minutes)
   ```bash
   mypy backend/app/ingestion/
   ```

**Success Criteria**:
- [ ] Mypy strict mode enabled
- [ ] Zero mypy errors in ingestion module
- [ ] All public APIs fully typed
- [ ] TypedDict used for config dicts
- [ ] No `Any` types (except internal/private code if justified)

---

### Task 4.3: Add Integration Tests
**Priority**: P3  
**Files**: `backend/tests/integration/test_ingestion_pipeline.py` (new)  
**Estimated Time**: 6 hours

**Implementation Steps**:

1. **Create Test Fixtures** (1 hour)
   - File: `backend/tests/integration/conftest.py`
   ```python
   import pytest
   from pathlib import Path
   
   @pytest.fixture
   def test_knowledge_base(db_session):
       """Create a test KB"""
       kb = KnowledgeBase(
           id="test_kb_001",
           name="Test KB",
           description="Test"
       )
       db_session.add(kb)
       db_session.commit()
       return kb
   
   @pytest.fixture
   def sample_documents(tmp_path: Path) -> Path:
       """Create sample markdown files"""
       doc_dir = tmp_path / "docs"
       doc_dir.mkdir()
       
       (doc_dir / "doc1.md").write_text("# Test\nContent 1")
       (doc_dir / "doc2.md").write_text("# Test\nContent 2")
       
       return doc_dir
   ```

2. **Test Complete Pipeline** (2 hours)
   ```python
   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_full_ingestion_pipeline(
       test_knowledge_base,
       sample_documents,
       orchestrator,
   ):
       """Test complete pipeline from load to index"""
       # Arrange
       config = {
           "source_type": "local_files",
           "source_config": {"path": str(sample_documents)},
           "chunking": {"strategy": "markdown", "chunk_size": 500},
       }
       
       # Act
       job_id = await orchestrator.start_ingestion(
           kb_id=test_knowledge_base.id,
           config=config
       )
       
       # Wait for completion (with timeout)
       await orchestrator.wait_for_completion(job_id, timeout=30)
       
       # Assert
       job = await orchestrator.get_job_status(job_id)
       assert job["status"] == "completed"
       
       # Verify documents were indexed
       search_results = await orchestrator.search(
           kb_id=test_knowledge_base.id,
           query="Test content",
           top_k=5
       )
       assert len(search_results) > 0
   ```

3. **Test Error Scenarios** (2 hours)
   - Test invalid source path
   - Test embedding API failure
   - Test disk full during chunking
   - Test graceful shutdown
   - Test job cancellation

4. **Test Pause/Resume** (1 hour)
   ```python
   @pytest.mark.integration
   async def test_pause_and_resume(orchestrator, test_knowledge_base):
       """Test job can be paused and resumed"""
       # Start job
       job_id = await orchestrator.start_ingestion(...)
       
       # Pause after 2 seconds
       await asyncio.sleep(2)
       await orchestrator.pause_job(job_id)
       
       # Verify paused
       job = await orchestrator.get_job_status(job_id)
       assert job["status"] == "paused"
       
       # Resume
       await orchestrator.resume_job(job_id)
       
       # Wait for completion
       await orchestrator.wait_for_completion(job_id, timeout=30)
       
       job = await orchestrator.get_job_status(job_id)
       assert job["status"] == "completed"
   ```

**Success Criteria**:
- [ ] Full pipeline integration test passes
- [ ] Error scenarios covered
- [ ] Pause/resume functionality tested
- [ ] Tests run in CI/CD
- [ ] Test coverage > 80% for orchestrator

---

## Phase 5: Cross-Cutting Improvements

### Task 5.1: Add React Error Boundary
**Priority**: P2  
**File**: `frontend/src/components/ErrorBoundary.tsx` (new)  
**Estimated Time**: 1 hour

**Implementation Steps**:

1. **Create Error Boundary Component** (30 minutes)
   ```tsx
   import { Component, ErrorInfo, ReactNode } from 'react';
   
   interface Props {
     children: ReactNode;
     fallback?: (error: Error, reset: () => void) => ReactNode;
   }
   
   interface State {
     hasError: boolean;
     error: Error | null;
   }
   
   export class ErrorBoundary extends Component<Props, State> {
     constructor(props: Props) {
       super(props);
       this.state = { hasError: false, error: null };
     }
     
     static getDerivedStateFromError(error: Error): State {
       return { hasError: true, error };
     }
     
     componentDidCatch(error: Error, errorInfo: ErrorInfo) {
       console.error('Error boundary caught:', error, errorInfo);
       // Optional: send to error tracking service
     }
     
     reset = () => {
       this.setState({ hasError: false, error: null });
     };
     
     render() {
       if (this.state.hasError && this.state.error) {
         if (this.props.fallback) {
           return this.props.fallback(this.state.error, this.reset);
         }
         
         return (
           <div className="error-boundary">
             <h2>Something went wrong</h2>
             <details>
               <summary>Error details</summary>
               <pre>{this.state.error.message}</pre>
             </details>
             <button onClick={this.reset}>Try again</button>
           </div>
         );
       }
       
       return this.props.children;
     }
   }
   ```

2. **Wrap Ingestion Workspace** (15 minutes)
   - File: `frontend/src/App.tsx` (or wherever workspace is rendered)
   ```tsx
   <ErrorBoundary fallback={(error, reset) => (
     <IngestionError error={error} onReset={reset} />
   )}>
     <IngestionWorkspace />
   </ErrorBoundary>
   ```

3. **Create Custom Error Fallback** (15 minutes)
   ```tsx
   function IngestionError({ error, onReset }: {
     error: Error;
     onReset: () => void;
   }) {
     return (
       <div className="flex flex-col items-center justify-center min-h-screen">
         <AlertCircle className="w-16 h-16 text-destructive mb-4" />
         <h2 className="text-2xl font-semibold mb-2">
           Ingestion Error
         </h2>
         <p className="text-muted-foreground mb-4">
           An error occurred while processing your knowledge base
         </p>
         <pre className="bg-muted p-4 rounded max-w-2xl overflow-auto mb-4">
           {error.message}
         </pre>
         <div className="flex gap-2">
           <Button onClick={onReset}>Try Again</Button>
           <Button variant="outline" onClick={() => window.location.href = '/'}>
             Go Home
           </Button>
         </div>
       </div>
     );
   }
   ```

**Success Criteria**:
- [ ] Error boundary wraps ingestion components
- [ ] Errors displayed to user with context
- [ ] Reset functionality works
- [ ] Errors logged for debugging

---

### Task 5.2: Implement Structured Logging
**Priority**: P2  
**Files**: Various backend files  
**Estimated Time**: 3 hours

**Implementation Steps**:

1. **Add Structlog Dependency** (15 minutes)
   ```bash
   uv add structlog
   ```

2. **Configure Structlog** (30 minutes)
   - File: `backend/app/ingestion/observability/logging_config.py`
   ```python
   import structlog
   import logging
   
   def configure_logging(log_level: str = "INFO") -> None:
       """Configure structured logging for ingestion"""
       structlog.configure(
           processors=[
               structlog.contextvars.merge_contextvars,
               structlog.processors.add_log_level,
               structlog.processors.TimeStamper(fmt="iso"),
               structlog.processors.StackInfoRenderer(),
               structlog.processors.format_exc_info,
               structlog.processors.JSONRenderer()
           ],
           wrapper_class=structlog.make_filtering_bound_logger(
               logging.getLevelName(log_level)
           ),
           context_class=dict,
           logger_factory=structlog.PrintLoggerFactory(),
           cache_logger_on_first_use=True,
       )
   ```

3. **Update Orchestrator Logging** (1.5 hours)
   ```python
   import structlog
   
   logger = structlog.get_logger(__name__)
   
   # Before
   logger.info(f"Starting ingestion for KB {kb_id}")
   
   # After
   logger.info(
       "ingestion_started",
       kb_id=kb_id,
       job_id=job_id,
       source_type=config["source_type"]
   )
   
   # With context binding
   log = logger.bind(kb_id=kb_id, job_id=job_id)
   log.info("load_phase_started")
   log.info("load_phase_completed", document_count=len(documents))
   ```

4. **Add Request Context** (1 hour)
   - Middleware to add request_id to all logs
   - File: `backend/app/middleware/logging.py`
   ```python
   import uuid
   from starlette.middleware.base import BaseHTTPMiddleware
   import structlog
   
   class LoggingMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request, call_next):
           request_id = str(uuid.uuid4())
           structlog.contextvars.clear_contextvars()
           structlog.contextvars.bind_contextvars(
               request_id=request_id,
               path=request.url.path,
               method=request.method
           )
           
           response = await call_next(request)
           response.headers["X-Request-ID"] = request_id
           return response
   ```

**Success Criteria**:
- [ ] Structlog configured and used throughout
- [ ] All logs include context (kb_id, job_id, request_id)
- [ ] Logs are JSON formatted
- [ ] Easy to search/filter in log aggregation tools

---

### Task 5.3: Document Retry Policy
**Priority**: P3  
**File**: `docs/ingestion/ERROR_HANDLING.md` (new)  
**Estimated Time**: 2 hours

**Implementation Steps**:

1. **Document Current Retry Behavior** (1 hour)
   - Research current retry logic in:
     - Embedder
     - Loader
     - Indexer
   - Document in markdown

2. **Create Retry Policy Doc** (1 hour)
   ```markdown
   # Ingestion Error Handling and Retry Policy
   
   ## Overview
   This document describes how the ingestion pipeline handles errors and retries.
   
   ## Retry Strategy by Component
   
   ### Document Loading
   - **Retries**: 3 attempts
   - **Backoff**: Exponential (1s, 2s, 4s)
   - **Retryable Errors**: Network timeouts, temporary file locks
   - **Non-Retryable**: Invalid file format, missing file
   
   ### Embedding Generation
   - **Retries**: 5 attempts
   - **Backoff**: Exponential with jitter (1s, 2s, 4s, 8s, 16s)
   - **Retryable Errors**: Rate limits (429), service unavailable (503)
   - **Non-Retryable**: Authentication errors (401), invalid input (400)
   
   ### Vector Indexing
   - **Retries**: 3 attempts
   - **Backoff**: Fixed (5s between attempts)
   - **Retryable Errors**: Connection errors, temporary unavailability
   - **Non-Retryable**: Invalid vector dimensions, duplicate IDs
   
   ## Configuration
   
   Retry behavior can be configured via environment variables:
   
   ```bash
   INGESTION_RETRY_MAX_ATTEMPTS=3
   INGESTION_RETRY_BACKOFF_FACTOR=2.0
   INGESTION_RETRY_MAX_DELAY=60
   ```
   
   ## Best Practices
   
   1. Always log retry attempts with context
   2. Include error details in phase status
   3. Allow manual retry from UI
   4. Consider circuit breaker for repeated failures
   ```

**Success Criteria**:
- [ ] Retry policy documented
- [ ] Examples included
- [ ] Configuration options listed
- [ ] Linked from main docs

---

## Testing Strategy

### Per-Phase Testing
Each phase should include:
1. **Unit Tests**: Test individual functions/methods
2. **Integration Tests**: Test component interactions
3. **Manual Testing**: Verify UX changes work as expected

### Regression Testing
Before marking phase complete:
- [ ] Run full backend test suite
- [ ] Run full frontend test suite
- [ ] Test complete ingestion flow end-to-end
- [ ] Verify metrics still work
- [ ] Check logs for errors

### Performance Testing
After major refactors (Phase 2):
- [ ] Benchmark ingestion speed (should not regress)
- [ ] Profile memory usage
- [ ] Test with large document sets (10k+ docs)

---

## Rollout Plan

### Phase 1 (Week 1)
- Days 1-2: Tasks 1.1-1.2 (exception handling)
- Days 3-4: Tasks 1.3-1.4 (event loop and audit)
- Day 5: Testing and validation

### Phase 2 (Week 2)
- Days 1-2: Task 2.1 (orchestrator refactor)
- Day 3: Tasks 2.2-2.3 (migrations and mappings)
- Day 4: Tasks 2.4-2.5 (shutdown and datetime)
- Day 5: Testing and integration

### Phase 3 (Week 3)
- Days 1-2: Tasks 3.1-3.2 (metrics and promises)
- Days 3-4: Tasks 3.3-3.5 (state management)
- Day 5: Testing

### Phase 4 (As Time Allows)
- Can be done incrementally
- Not blocking for production

---

## Success Metrics

### Code Quality
- [ ] Ruff/ESLint pass with no warnings
- [ ] Mypy strict mode passes
- [ ] Test coverage > 85%
- [ ] No TODO/FIXME comments in critical paths

### Observability
- [ ] All errors logged with context
- [ ] Prometheus metrics exported
- [ ] Grafana dashboard functional
- [ ] Error rates tracked

### Reliability
- [ ] Zero production incidents related to exception swallowing
- [ ] Clean shutdown works 100% of time
- [ ] Failed jobs can be resumed successfully

---

## Risk Mitigation

### High-Risk Changes
1. **Orchestrator Refactor** (Task 2.1)
   - Risk: Breaking existing pipelines
   - Mitigation: Extensive integration tests, gradual rollout, feature flag

2. **Event Loop Changes** (Task 1.3)
   - Risk: Deadlocks or performance issues
   - Mitigation: Load testing, monitor event loop lag

3. **Migration System** (Task 2.2)
   - Risk: Data loss or corruption
   - Mitigation: Backup before migration, test on staging

### Rollback Plan
- Keep feature branches until validated in production
- Tag releases before each phase
- Document rollback procedures in CHANGELOG.md

---

## Appendix

### Related Documents
- [review-ingestion-codebase-20260208.md](./review-ingestion-codebase-20260208.md) - Original grumpy review
- [INGESTION_ARCHITECTURE.md](../PROJECT_OVERVIEW.md) - System architecture
- [DEVELOPMENT_GUIDE.md](../DEVELOPMENT_GUIDE.md) - Development setup

### Review Sections Excluded
- ✅ **Task Excluded**: Naming Convention Changes (Section 🔵 MINOR: Naming Inconsistency)
  - Rationale: Project uses Python snake_case and TypeScript camelCase per best practices
  - Mapping handled by `keysToSnake()` utility
  - No implementation needed

### Questions for Discussion
1. Should we use Celery instead of refactored orchestrator? (impacts Task 2.1)
2. Prometheus vs. OpenTelemetry for observability? (impacts Task 3.1)
3. Feature flag library recommendation? (for gradual rollouts)

---

**Document Version**: 1.0  
**Last Updated**: February 8, 2026  
**Next Review**: After Phase 1 completion
