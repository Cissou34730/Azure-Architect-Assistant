# KB Status Lifecycle and Implementation Plan

## Overview
- Single source of truth: Persist canonical job lifecycle in `ingestion_jobs.status`.
- Distinct job states: `NOT_STARTED`, `RUNNING`, `PAUSED`, `COMPLETED`, `FAILED`, optionally `CANCELED`.
- Phase-driven: Each phase persists its own status in response to signals and input availability.
- Deterministic aggregation: Repository recomputes job.status from phase rows (no post-hoc UI derivations).
- UI alignment: KB-level status reads job.status directly and maps to `not_ready | pending | paused | ready`.

## Lifecycle Semantics
- Initial: Job = `NOT_STARTED`; all phases = `not_started`.
- Start: Loading = `running`; others = `pending` (watching input/queue).
- Running: Any phase actively processing → `running`; watching input → `pending` (phase-level only).
- Finished (per phase): Upstream dependency completed AND input drained; then set `completed`.
- Pause: Signal freezes phases as `paused`; job.status = `PAUSED`.
- Resume: Job.status = `RUNNING`; phases resume to `running` or `pending` based on input.
- Cancel: Reset phases to `not_started`, clear queue; job.status = `CANCELED` (or `NOT_STARTED` if cancel-as-reset).
- Fail: Infrastructure/config failure at phase; single-document errors do not set `failed` at phase or job.

## Status Aggregation Rules (Repository)
Recompute job.status from persisted phase rows:
- `COMPLETED`: all phases `completed`.
- `FAILED`: any phase `failed`.
- `RUNNING`: any phase `running`.
- `PAUSED`: any phase `paused` AND no `running` phases.
- `NOT_STARTED`: all phases `not_started`.
- `CANCELED`: set explicitly by cancel/reset flow (not inferred).
- Note: No `PENDING` at job level; `pending` remains phase-level only.

## KB-Level Status Mapping (API)
- `NOT_STARTED` → `not_ready`
- `RUNNING` → `pending`
- `PAUSED` → `paused`
- `COMPLETED` → `ready`
- `CANCELED` → `not_ready`
- `FAILED` → `not_ready` (include error details)

## Modules to Modify
1) `backend/app/ingestion/models.py`
   - Extend `JobStatus` with `NOT_STARTED`, `PAUSED`, `CANCELED` (optional).
   - Default `IngestionJob.status = NOT_STARTED`.

2) `backend/app/ingestion/infrastructure/repository.py`
   - `initialize_phase_statuses(job_id)`: set job.status → `NOT_STARTED` after creating rows.
   - `_recompute_and_persist_job_status(session, job_id)`: implement rules above; remove `PENDING` from job level.
   - Invoke recompute after `update_phase_status`, `pause_current_phase`, `resume_current_phase`, `cancel_job_and_reset`.
   - Ensure phases only complete when dependencies completed and inputs drained.

3) `backend/app/ingestion/application/status_query_service.py`
   - Return KB status via job.status mapping (include `paused`).
   - Keep `phase_details` for UI but do not derive KB readiness from it.

4) `backend/app/ingestion/application/consumer_pipeline.py`
   - Gate EMBEDDING start: queue has items AND chunking ready.
   - Gate INDEXING start: embedding completed AND embedded items exist.
   - Do not mark phases `completed` with zero totals unless dependency completed and input drained.
   - Persist phase states into `state.phases` and repository.

5) `backend/app/routers/kb_ingestion/ingestion_router.py`
   - Pause/Resume/Cancel endpoints: persist job.status (`PAUSED`, `RUNNING`, `CANCELED`/`NOT_STARTED`) and phase transitions.

6) `backend/app/routers/kb_management/management_router.py`
   - KB status endpoint returns `paused` when job.status is `PAUSED`.
   - Delete/Clear handlers set job.status appropriately and reset phases/queues.

7) Frontend (`src/types/ingestion.ts`, `src/services/ingestionApi.ts`, `src/hooks/useIngestionJob.ts`, `src/components/ingestion/KBList.tsx`)
   - Types include `paused` explicitly.
   - Controls per status:
     - `not_ready`: Start
     - `pending` (running): Pause, Cancel, View Progress
     - `paused`: Resume, Cancel, View Progress (hide Pause)
     - `ready`: Clear/Reset

## New Modules
- `backend/scripts/recompute_job_statuses.py`
  - Iterates jobs, reads phase rows, applies aggregation rules, updates `ingestion_jobs.status`.
  - Prints a summary of changes.

## Migrations & Justification
- Optional Alembic (`backend/alembic/`) for enum extension and future schema changes.
  - Justification: Safe, trackable schema evolution across environments.
  - If kept simple (dev-only), manual backfill can suffice without Alembic.

## Testing & Observability
- Unit tests:
  - Repository recompute with various phase mixes.
  - Consumer gating (zero items, paused, partial, full).
  - API KB status mapping including `paused`.
- Metrics/Logs:
  - Count phase/job transitions.
  - Warn when a phase attempts completion with zero total and no dependency completion.

## Implementation Phases
1) Enums/schema updates in models; repository defaults to `NOT_STARTED`.
2) Implement recompute rules and wire into write paths.
3) Adjust status API mapping; expose `paused`.
4) Harden consumer gating for phase starts/completions.
5) Update ingestion routers for pause/resume/cancel semantics.
6) Frontend alignment for new KB states.
7) Backfill script to align existing jobs; run locally.
8) Add tests and minimal instrumentation.

## Notes
- No new libraries required by default; Alembic recommended if you anticipate production migrations.
- Keep phase “pending” strictly phase-level; job-level avoids `PENDING` to reflect true lifecycle.
