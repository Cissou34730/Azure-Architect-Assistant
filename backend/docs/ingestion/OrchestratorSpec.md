# Ingestion Orchestrator Pattern — Simple Sequential Flow

Purpose: define a straightforward orchestrator that manages ingestion as a simple sequential pipeline with clear checkpoints.

## Goals
- Single orchestrator owns the entire flow: load → chunk → embed → index.
- Simple sequential execution with cooperative gates for pause/resume/cancel.
- Crash-safe via checkpoints and idempotency.
- No events, no pub/sub, no complex wiring—just a clear step-by-step process.

## Design Decisions (from Gap Analysis)

### **Adopted from CodeExampleOrchestrator**
1. **WorkflowDefinition class**: Defines step ordering and next-step logic cleanly
2. **RetryPolicy abstraction**: Makes retry behavior configurable and testable
3. **Explicit payload mapping**: Clear data contracts between steps via `build_next_payload()` pattern
4. **Task dataclass**: For clarity in logging and observability (without queue initially)

### **Kept from OrchestratorSpec**
1. **Batch processing**: More efficient than item-at-a-time for large-scale ingestion
2. **Idempotency via content_hash**: Critical for crash safety; check `(kb_id, content_hash)` before processing
3. **Checkpoint-based resumption**: Simple `last_batch_id` checkpoint with idempotency for duplicates
4. **Explicit check_gate() function**: Clear cooperative control with pause polling
5. **Direct function calls**: No dispatcher layer initially; start simple

### **Deferred for Later**
1. **Per-item state tracking**: Start with counters only; add per-document table if needed for better observability
2. **Task queue abstraction**: Use direct calls initially; add queue only if parallelization needed
3. **Complex error recovery**: Start with retry + count errors; enhance if needed

## Core Concept
An **Orchestrator** is a single component that:
- Calls each step in sequence (loader, chunker, embedder, indexer).
- Checks `jobs.status` between steps for pause/resume/cancel.
- Persists progress checkpoints after each batch/chunk.
## Components

### **Core Components (New)**
- **Orchestrator**
  - Single async class that runs the entire pipeline
  - Uses `WorkflowDefinition` to determine step order
  - Applies `RetryPolicy` for transient failures
  - Loads batches from source handler
  - Calls chunker for each batch
  - Calls embed+index for each chunk with idempotency check
  - Checks `jobs.status` via `check_gate()` between batches/chunks
  - Persists checkpoint after each batch
  - Updates counters in `jobs` table
  - Uses explicit payload mapping between steps

- **WorkflowDefinition**
  - Defines pipeline step order: `load → chunk → embed → index`
  - Provides `get_first_step()` and `get_next_step(current)` methods
  - Centralizes pipeline structure knowledge

- **RetryPolicy**
  - Configurable retry logic with max attempts and backoff
  - Decides whether to retry based on error type and attempt count
  - Applied per-chunk during embed+index operations

### **Domain Components (ONLY These Are Reused/Refactored)**

**IMPORTANT**: Only domain logic components are reused. All orchestration code (producer/consumer, phase tracker, queues) will NOT be reused.

- **Source Handler** (from `backend/app/ingestion/domain/sources/`)
  - **Reuse/Refactor**: Keep existing implementations (PDF, Markdown, Website, YouTube)
  - Factory pattern: `SourceHandlerFactory` creates handlers for different types
  - Generator that yields document batches
  - Supports resumption from checkpoint (cursor/batch_id)
  - May need minor refactoring for checkpoint format

- **Chunker** (from `backend/app/ingestion/domain/chunking/`)
  - **Reuse/Refactor**: Keep existing chunker implementations
  - Factory pattern: `ChunkerFactory` creates chunkers based on strategy
  - Pure function: takes documents → returns chunks with `content_hash`
  - Existing implementations should work as-is

- **Embedder** (extract/refactor from existing code)
  - **Refactor**: Extract embedding logic into standalone component
  - Generates vector embeddings for text chunks
  - Returns embeddings with metadata including `content_hash`
  - Pure async function, no dependencies on old orchestration

- **Indexer** (new, split from embedding)
  - **New**: Separate indexing from embedding
  - Checks if `(kb_id, content_hash)` exists (idempotency)
  - If not: persists embeddings to vector store
  - Atomic: commit only after successful write

**NOT Reused**:
- ❌ Producer/consumer pipeline code
- ❌ Phase tracker and phase tables
- ❌ Queue management code
- ❌ Old orchestration logic
- **Orchestrator**
  - Single async function that runs the entire pipeline.
  - Loads batches from source handler.
  - Calls chunker for each batch.
  - Calls embed+index for each chunk.
  - Checks `jobs.status` at regular gates (between batches, between chunks).
  - Persists checkpoint after each batch.
  - Updates counters in `jobs` table.

- **Source Handler**
  - Generator that yields document batches.
  - Supports resumption from checkpoint (cursor/batch_id).

- **Chunker**
  - Pure function: takes documents → returns chunks with `content_hash`.

- **Embed+Index**
  - Checks if `(kb_id, content_hash)` exists.
  - If not: embeds → indexes → returns result.
  - Atomic: commit only after successful index write.

## Control Gates
- `jobs.status`: `not_started | running | paused | completed | failed | canceled`
- Gates checked:
  - **Before fetching next batch**: If `paused`, sleep/backoff and re-check. If `canceled`, exit and trigger cleanup.
  - **Before processing each chunk**: Same checks.
  - **During long operations**: Optional periodic checks with timeout.
- **Cancel behavior**: When gate detects `canceled`, orchestrator exits and cleanup workflow runs to reset state to `not_started`.

## Pause/Resume/Cancel
- **Pause**: Orchestrator detects `status=paused` at next gate; parks in a sleep loop; continues when `status=running`.
- **Resume**: API flips `status` back to `running`; orchestrator continues from checkpoint.
- **Cancel**: 
  - Orchestrator detects `status=canceled`; exits gracefully at next gate
  - **Cleanup workflow triggered**:
    - Rollback: Delete all embeddings/chunks for this job from vector store
    - Clear checkpoint and counters
    - Reset `status=not_started`
    - Set `finished_at` and `last_error='Canceled by user'`
  - User can restart ingestion from scratch after cancel
  - Cleanup ensures no partial/orphaned data remains

## Crash Safety
- **Checkpoints**: 
  - Persist `last_batch_id` or source cursor after each batch.
  - On restart, orchestrator reads checkpoint and resumes from next batch.
  
- **Idempotency**:
  - Each chunk identified by `(kb_id, content_hash)`.
  - Embed+Index checks existence before processing; skips if present.
  - Safe to replay batches/chunks without duplication.

- **Atomic operations**:
  - Embed → Index → Commit as a single transaction.
  - If crash happens mid-chunk, restart reprocesses (idempotent).

## Data Model (minimal)
- `jobs`:
  - `id`, `kb_id`, `status`, `started_at`, `finished_at`, `last_error`
  - `checkpoint` (JSON: `{last_batch_id, cursor}`)
  - `counters` (JSON: `{docs_seen, chunks_seen, chunks_processed, chunks_skipped, chunks_error}`)

- `embeddings_index`:
  - Unique key: `(kb_id, content_hash)`
  - Stores: vector, metadata, indexed_at

- Optional `heartbeat`:
  - `job_id`, `last_seen_at`
  - Orchestrator updates every 5-10s to detect stalls.

## API Surface
- `POST /jobs/:kb_id/start`
  - Creates job with `status=running`.
  - Spawns orchestrator in background (asyncio task).
  
- `POST /jobs/:id/pause`
  - Sets `jobs.status=paused`.
  - Orchestrator parks at next gate.

- `POST /jobs/:id/resume`
  - Sets `jobs.status=running`.
  - Orchestrator continues from checkpoint.

- `POST /jobs/:id/cancel`
  - Sets `jobs.status=canceled`.
  - Orchestrator exits at next gate.
  - **Cleanup workflow runs**:
    - Delete all job data (embeddings, chunks) from vector store
    - Clear checkpoint and counters
    - Reset `status=not_started`
    - Record cancellation in `last_error`

- `GET /jobs/:id/status`
  - Returns `jobs.status`, counters, `last_error`, heartbeat age.

## Observability
- **Logs**: Batch/chunk progress, rates (docs/sec, chunks/sec), warnings on empty content, errors.
- **Counters**: Updated in DB after each batch; exposed via status endpoint.
## Implementation Sketch (Updated with Design Decisions)
```python
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

# Step definitions
class StepName(str, Enum):
    LOAD = "load"
    CHUNK = "chunk"
    EMBED = "embed"
    INDEX = "index"

# Workflow definition (from CodeExample)
class WorkflowDefinition:
    ORDER: List[StepName] = [StepName.LOAD, StepName.CHUNK, StepName.EMBED, StepName.INDEX]
    
    def get_first_step(self) -> StepName:
        return self.ORDER[0]
    
    def get_next_step(self, current: StepName) -> Optional[StepName]:
        idx = self.ORDER.index(current)
        return self.ORDER[idx + 1] if idx + 1 < len(self.ORDER) else None

# Retry policy (from CodeExample)
class RetryPolicy:
    def __init__(self, max_attempts: int = 3, backoff_multiplier: float = 2.0):
        self.max_attempts = max_attempts
        self.backoff_multiplier = backoff_multiplier
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        return attempt < self.max_attempts
    
    def get_backoff_delay(self, attempt: int) -> float:
        return min(2 ** attempt * self.backoff_multiplier, 60)  # Max 60s

# Task for logging/observability (from CodeExample)
@dataclass
class ProcessingTask:
    job_id: str
    kb_id: str
    step: StepName
    payload: Dict[str, Any]
    batch_id: Optional[int] = None
    chunk_index: Optional[int] = None

# Payload mapping (from CodeExample pattern)
def build_next_payload(step: StepName, prev_output: Dict[str, Any]) -> Dict[str, Any]:
    """Map output of one step to input of next step."""
    if step == StepName.CHUNK:
        return {"documents": prev_output["documents"]}
    elif step == StepName.EMBED:
        return {"chunks": prev_output["chunks"]}
    elif step == StepName.INDEX:
        return {"embeddings": prev_output["embeddings"], "metadata": prev_output["metadata"]}
    return prev_output

# Main orchestrator
class IngestionOrchestrator:
    def __init__(self, repo, workflow: WorkflowDefinition, retry_policy: RetryPolicy):
        self.repo = repo
        self.workflow = workflow
        self.retry_policy = retry_policy
    
    async def run(self, job_id: str, kb_id: str, kb_config: Dict[str, Any]):
        job = self.repo.get_job(job_id)
        checkpoint = job.checkpoint or {}
        counters = job.counters or {"docs_seen": 0, "chunks_seen": 0, "chunks_processed": 0, "chunks_skipped": 0, "chunks_error": 0}
        
        # Initialize components (reuse existing code)
        source_handler = self._create_source_handler(kb_config, checkpoint)
        chunker = self._create_chunker(kb_config)
        embedder = self._create_embedder(kb_config)
        indexer = self._create_indexer(kb_id)
        
        try:
            # Main loop: process batches
            for batch_id, batch in enumerate(source_handler.fetch_batches(), start=checkpoint.get('last_batch_id', 0) + 1):
                if not await self._check_gate(job_id):
                    break
                
                # Step 1: Chunk batch
                chunks = chunker.chunk(batch)
                counters['docs_seen'] += len(batch)
                counters['chunks_seen'] += len(chunks)
                
                # Step 2: Process each chunk (embed + index with idempotency)
                for chunk_idx, chunk in enumerate(chunks):
                    if not await self._check_gate(job_id):
                        break
                    
                    # Create task for logging
                    task = ProcessingTask(job_id=job_id, kb_id=kb_id, step=StepName.EMBED, 
                                         payload={"chunk": chunk}, batch_id=batch_id, chunk_index=chunk_idx)
                    
                    # Process with retry
                    result = await self._process_chunk_with_retry(task, chunk, embedder, indexer)
                    
                    if result["skipped"]:
                        counters['chunks_skipped'] += 1
                    elif result["success"]:
                        counters['chunks_processed'] += 1
                    else:
                        counters['chunks_error'] += 1
                
                # Persist checkpoint and counters after each batch
                checkpoint['last_batch_id'] = batch_id
                self.repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
                self.repo.update_heartbeat(job_id)
            
            # Complete
            self.repo.set_job_status(job_id, 'completed', finished_at=now())
            
        except Exception as e:
            self.repo.set_job_status(job_id, 'failed', last_error=str(e), finished_at=now())
            raise
    
    async def _process_chunk_with_retry(self, task, chunk, embedder, indexer):
        """Process chunk with retry policy."""
        attempt = 0
        while True:
            try:
## Trade-offs

### **Advantages**
- **Simple**: Easy to reason about, minimal moving parts, direct function calls
- **Debuggable**: Single call stack, clear logs, linear execution
- **Crash-safe**: Checkpoint + idempotency without complex state machines
- **Maintainable**: Clear step order via WorkflowDefinition, configurable retry via RetryPolicy
- **Observable**: Task dataclass for logging, counters for progress tracking
- **Testable**: Each component has clear interface and can be tested independently

### **Limitations**
- **Sequential**: Single-threaded per job (but can run multiple jobs in parallel)
- **No backpressure separation**: No queue between steps (but embeddings are slow anyway; natural throttle)
- **Coarse-grained recovery**: Batch-level checkpoint means partial batch reprocessing on crash
- **No per-document state**: Can't see individual document status (only counters)

### **Future Enhancements (Deferred)**
- Add per-document state table for better observability
- Add task queue for parallel chunk processing within batch
- Add circuit breaker for downstream service failures
- Add adaptive batch sizing based on performance metrics
                await indexer.index(embedding)
                return {"success": True, "skipped": False}
                
            except Exception as e:
                attempt += 1
                if self.retry_policy.should_retry(attempt, e):
                    delay = self.retry_policy.get_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                else:
                    return {"success": False, "skipped": False, "error": str(e)}
    
    async def _check_gate(self, job_id: str) -> bool:
        """Check status; park if paused, exit if canceled."""
        while True:
            status = self.repo.get_job_status(job_id)
            if status == 'running':
                return True
            elif status == 'paused':
                await asyncio.sleep(1)  # Backoff and re-check
            elif status == 'canceled':
                # Trigger cleanup workflow
                await self._cleanup_job(job_id, self.kb_id)
                return False
            elif status in ('failed', 'completed'):
                return False
    
    async def _cleanup_job(self, job_id: str, kb_id: str):
        """Cleanup workflow for canceled jobs: delete data and reset state."""
        try:
            # Delete all embeddings/chunks for this job from vector store
            await self.indexer.delete_by_job(job_id, kb_id)
            
            # Reset job state
            self.repo.update_job(
                job_id,
                status='not_started',
                checkpoint=None,
                counters=None,
                finished_at=now(),
                last_error='Canceled by user'
            )
        except Exception as e:
            # Log cleanup failure but don't crash
            logger.error(f"Cleanup failed for job {job_id}: {e}")
    
    def _create_source_handler(self, kb_config, checkpoint):
        """Reuse/refactor existing SourceHandlerFactory from domain/sources/"""
        from backend.app.ingestion.domain.sources import SourceHandlerFactory
        return SourceHandlerFactory.create(kb_config, checkpoint)
    
    def _create_chunker(self, kb_config):
        """Reuse/refactor existing ChunkerFactory from domain/chunking/"""
        from backend.app.ingestion.domain.chunking import ChunkerFactory
        return ChunkerFactory.create(kb_config)
    
    def _create_embedder(self, kb_config):
        """Refactor: extract embedding logic from existing code into new module"""
        # To be implemented: extract embedding logic from old embed+index code
        # NO reuse of orchestration logic, only embedding generation
        pass
    
    def _create_indexer(self, kb_id):
        """New: split indexing from embedding into separate module"""
        # To be implemented: idempotent indexing with cleanup support
        # Must support delete_by_job() for cancel cleanup
        pass
```         # Persist checkpoint and counters
            checkpoint['last_batch_id'] = batch_id
            repo.update_job(job_id, checkpoint=checkpoint, counters=counters)
            
            # Heartbeat
            repo.update_heartbeat(job_id)
        
        # Complete
        repo.set_job_status(job_id, 'completed', finished_at=now())
        
    except Exception as e:
        repo.set_job_status(job_id, 'failed', last_error=str(e), finished_at=now())
        raise

async def check_gate(repo, job_id):
    """Check status; park if paused, exit if canceled."""
    while True:
        status = repo.get_job_status(job_id)
        if status == 'running':
            return True
        elif status == 'paused':
            await asyncio.sleep(1)  # Backoff and re-check
        elif status in ('canceled', 'failed', 'completed'):
            return False
```

## Implementation Plan (Clean New Implementation)

### Phase 1: Core Components (Keep/Refactor)
1. **Loading module** (`backend/app/ingestion/domain/loading/`)
   - Review and keep existing `SourceHandlerFactory` and handlers
   - Ensure clean async interface returning batches of documents

2. **Chunking module** (`backend/app/ingestion/domain/chunking/`)
   - Review and keep existing `ChunkerFactory` and chunkers
   - Ensure clean interface: `chunk(docs) -> List[Chunk]`

3. **Embedding module** (`backend/app/ingestion/domain/embedding/`)
   - Extract embedding logic from current embed+index code
   - Interface: `embed(chunks) -> List[Embedding]`
   - Returns embeddings with content_hash for idempotency

4. **Indexing module** (`backend/app/ingestion/domain/indexing/`)
   - **NEW**: Split from embedding
   - Interface: `index(embeddings) -> None`
   - Idempotent: check `(kb_id, content_hash)` before insert
   - Handles database persistence only

### Phase 2: New Orchestration
5. **Orchestrator module** (`backend/app/ingestion/application/orchestrator.py`)
   - **NEW**: `IngestionOrchestrator` class
   - Sequential flow: load → chunk → embed → index
   - Cooperative gates checking `jobs.status`
   - Checkpoint persistence after each batch
   - Counter updates (pages, chunks, embeddings)

### Phase 3: API Layer
6. **New router module** (`backend/app/routers/ingestion_v2.py`)
   - **NEW**: Clean router with orchestrator endpoints
   - `POST /ingestion/jobs/{kb_id}/start`
   - `POST /ingestion/jobs/{kb_id}/pause`
   - `POST /ingestion/jobs/{kb_id}/resume`
   - `POST /ingestion/jobs/{kb_id}/cancel`
   - `GET /ingestion/jobs/{kb_id}/status`

7. **Wire new router in main.py**
   - Import and register `ingestion_v2` router
   - Replace old ingestion endpoints

### Phase 4: Data Model
8. **Update database schema**
   - Add `checkpoint` (JSONB) to `jobs` table
   - Add `counters` (JSONB) to `jobs` table
   - Verify `embeddings_index` has unique constraint on `(kb_id, content_hash)`
   - Migration script for schema changes

### Phase 5: Cleanup (After Validation)
9. **Remove legacy code**
   - Delete producer/consumer pipeline modules
   - Delete phase tracker and phase tables
   - Delete queue tables
   - Remove old router endpoints

## Trade-offs
- **Pro**: Extremely simple, easy to reason about, minimal moving parts.
- **Pro**: Easy to debug; single call stack; clear logs.
- **Pro**: Crash-safe via checkpoint + idempotency without complex state machines.
- **Con**: Single-threaded per job (but can run multiple jobs in parallel).
- **Con**: No natural backpressure separation (but embeddings can be slow anyway; natural throttle).

## When to Use
- Perfect for straightforward ETL-style pipelines where steps are naturally sequential.
- When simplicity and maintainability are top priorities.
- When you don't need horizontal scaling within a single job (scaling across jobs is still easy).
