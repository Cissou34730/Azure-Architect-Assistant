# KB Status and Actions – Phased Plan (Persisted-Only)

This plan defines a persisted-only model to derive Knowledge Base (KB) status and align frontend actions accordingly. Runtime state is not relied upon; all derivations come from the database.

## Phase 1: State Model & Derivation
- States: `ready`, `pending`, `not_ready` (aka `not_started`).
- Canonical phases: `loading`, `chunking`, `embedding`, `indexing`.
- Derivation rules:
  - Ready: all canonical phases are `completed`.
  - Pending: any canonical phase is `running`, `paused`, or `pending`.
  - Not Ready: no phases are `completed` and either no job exists or all phases are `not_started`.
- Notes: Do not use `index_ready` as an input to status; status is strictly derived from phase rows in the DB.

## Phase 2: Repository/Data
- Implement `get_job_by_kb_id(kb_id)` to resolve the canonical `job.id` (UUID).
- Ensure `IngestionPhaseStatus` and queue lookups always use `job.id`.
- Provide repository methods:
  - `get_all_phase_statuses(job_id)` → list canonical phase rows.
  - `get_queue_stats(job_id)` → persisted queue counters (pending, processing, done, error).

## Phase 3: API Split
- `GET /api/kb/{kb_id}/status` (KB-level):
  - Returns: `{ kb_id, status: ready|pending|not_ready }` and optionally minimal counters (derived from persisted metrics).
  - No runtime calls; strictly uses DB rows.
- `GET /api/ingestion/kb/{kb_id}/details` (ingestion details):
  - Returns: `{ current_phase, overall_progress, phase_details[] }` from DB.
  - `overall_progress`: average of canonical phase progress; `100` when status is `ready`.
- Actions (unchanged endpoints, persisted effects):
  - `POST /api/ingestion/kb/{kb_id}/start`
  - `POST /api/ingestion/kb/{kb_id}/pause`
  - `POST /api/ingestion/kb/{kb_id}/resume`
  - `POST /api/ingestion/kb/{kb_id}/cancel` → stop job, clear queue, set phases/job to `not_started` (or failed per design).
  - `POST /api/kb/{kb_id}/clear` → delete index and reset job/phases to `not_started`.
  - `DELETE /api/kb/{kb_id}` → remove KB and all ingestion artifacts.

## Phase 4: Frontend UX & Actions
- Query split:
  - Poll `status` for `ready | pending | not_ready`.
  - When `pending`, also poll `details` for progress bars and per-phase info.
- Actions per state:
  - Not Ready: show `Start Ingestion` and `Delete` (available).
  - Ready: show `Delete` and `Clear`.
  - Pending: show `Pause/Resume`, `Cancel` (reset to `not_started`), and `Delete`.
- Mapping: ensure backend fields match UI types; remove “unknown” fallbacks by providing defaults.

## Phase 5: Backfill/Migration
- Script to backfill existing KBs (e.g., `waf`, `nist-sp`):
  - Resolve `job.id` via `kb_id`.
  - Ensure canonical phase rows exist and set each to `completed`.
  - Set job fields consistently (`current_phase = indexing`, `progress = 100`).

## Phase 6: Persistence on Actions
- `pause/resume`: update phase rows for the current phase without relying on runtime.
- `cancel`: mark job/phases as `not_started` (or `failed` as per design) and clear queue.
- `clear`: delete index and reset job/phases to `not_started`.
- Record timestamps and audit messages.

## Phase 7: Tests
- Unit tests for status derivation covering: ready, pending (running/paused), not_ready, failed.
- Integration tests for `status`, `details`, `clear`, and `cancel` endpoints.
- Frontend tests: controls visibility per state; progress rendering when pending.

## Phase 8: Rollout & Monitoring
- Deploy backend changes and run backfill script for known KBs.
- Monitor logs for status queries; confirm no reliance on runtime for completed KBs.
- Track derivation metrics (e.g., number of KBs in each state) to validate correctness.

## Acceptance Criteria
- Completed KBs derive `ready` without runtime presence.
- Pending reflects active ingestion phases; Not Ready shows when no work has started.
- Frontend presents correct actions for each state, with no “unknown” status in UI.