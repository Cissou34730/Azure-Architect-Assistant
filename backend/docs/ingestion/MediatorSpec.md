# Ingestion Mediator Pattern — Minimal Event-Driven Streaming

Purpose: define a simple in-process mediator that routes ingestion events without phases, queues, or over-engineering.

## Goals
- Single pipeline with clear responsibilities per step.
- Event-driven chaining: loader → chunker → embed+index.
- Cooperative control via `jobs.status` for pause/resume/cancel.
- Crash-safe and idempotent by design.

## Events
- `BatchRead`
  - Payload: `{ job_id: str, kb_id: str, batch: Document[] }`
  - Emitted by: Loader after fetching a batch from source.
- `ChunksReady`
  - Payload: `{ job_id: str, kb_id: str, chunks: Array<{ content: str, metadata: dict, content_hash: str }> }`
  - Emitted by: Chunker after chunking a batch.
- `ChunkProcessed`
  - Payload: `{ job_id: str, kb_id: str, content_hash: str, ok: bool, error?: str }`
  - Emitted by: EmbedIndexer after embed+index step per chunk.
- `Heartbeat`
  - Payload: `{ job_id: str, ts: datetime }`
  - Emitted by: Mediator on interval to detect stalls.

## Components
- **Mediator**
  - Wires subscriptions, dispatches events, and enforces control gates.
  - Checks `jobs.status` before dispatch; pauses/resumes/cancels uniformly.
  - Emits `Heartbeat(job_id)` every 5–10s.
  - Finalizes job: sets `completed/failed/canceled`.
- **Loader**
  - Reads batches from source handler generator.
  - Before emitting, persists checkpoint (cursor/batch id).
  - Publishes `BatchRead` per batch.
- **Chunker**
  - Subscribed to `BatchRead`.
  - Produces chunks, computes `content_hash` per chunk.
  - Publishes `ChunksReady`.
- **EmbedIndexer**
  - Subscribed to `ChunksReady`.
  - Skips if `(kb_id, content_hash)` exists in index (idempotent fast-path).
  - Otherwise embed → index → emit `ChunkProcessed` with `ok/error`.
- **Metrics**
  - Subscribed to `ChunkProcessed`.
  - Updates counters: `chunks_processed`, `chunks_skipped`, `chunks_error`, rates.

## Control Model
- `jobs.status`: `not_started | running | paused | completed | failed | canceled`.
- Events: `start, pause, resume, cancel, complete, error` handled by API; mediator reads status only.
- Gates:
  - Loader: check status before fetching and before publishing `BatchRead`.
  - Chunker & EmbedIndexer: check status before heavy work; park on `paused`, exit on `canceled`.

## Crash Safety & Idempotency
- **Checkpointing**: Loader persists cursor/batch id before publishing; on restart it resumes from checkpoint.
- **Atomic processing**: EmbedIndexer wraps embed→index→commit before emitting `ChunkProcessed`.
- **Idempotency**: Unique `(kb_id, content_hash)` in index ensures safe replays and skips.
- **Restart**: Mediator re-wires; Loader resumes; downstream re-emits; EmbedIndexer skips already done.

## API Surface
- `POST /jobs/:kb_id/start`: mediator initializes, wires handlers, sets `running`, starts Loader.
- `POST /jobs/:id/pause|resume|cancel`: flips `jobs.status` only; mediator gates dispatch accordingly.
- `GET /jobs/:id/status`: returns `jobs.status`, counters, `last_error`, heartbeat age.

## Data Model (minimal)
- `jobs`: `id`, `kb_id`, `status`, `started_at`, `finished_at`, `last_error`, counters (`docs_seen`, `chunks_seen`, `chunks_processed`, `chunks_skipped`, `chunks_error`).
- `embeddings_index`: unique `(kb_id, content_hash)` with vector + metadata.
- `pipeline_heartbeat`: `job_id`, `last_seen_at` (optional for stall detection).

## Observability
- Logs per event: batch sizes, chunk counts, processing rate.
- Metrics subscriber aggregates counters and exposes them via status endpoint.
- Heartbeat-based stall alert when `status=running` but heartbeat is stale.

## Non-Goals
- No phase tracker, no external brokers/queues, no hierarchical FSM.
- Keep subscriptions and handlers in-process and small.

## Implementation Notes
- Tiny pub/sub interface:
  - `subscribe(event_type: str, handler: Callable)`
  - `publish(event_type: str, payload: dict)` (async-aware)
- Cooperative checks use short sleeps/backoff during pause.
- Configurable knobs: `chunk_size`, `overlap`, `max_attempts`, `pause_poll_interval`, timeouts.
