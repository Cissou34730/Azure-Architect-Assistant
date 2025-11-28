# Ingestion State (KB-Centric)

This document describes the KB-centric ingestion state model.

- Single active job per KB: at any time, only one ingestion runs for a given `kbId`.
- State keyed by `kbId`: start/pause/resume/cancel and status queries are all per KB.
- Persistence: runtime snapshots stored under `backend/data/ingestion/jobs/<kbId>.json` (ignored by git).

## API (KB-Centric)
- POST `/ingestion/{kbId}/start`
- POST `/ingestion/{kbId}/pause`
- POST `/ingestion/{kbId}/resume`
- POST `/ingestion/{kbId}/cancel`
- GET `/ingestion/{kbId}/status`
- GET `/ingestion/list` (optional, returns KB states)

## Snapshot Format
A minimal example:
```json
{
  "kbId": "kb-123",
  "status": "RUNNING",
  "phase": "CRAWLING",
  "progress": 42,
  "paused": false,
  "cancelRequested": false,
  "metrics": {"urlsProcessed": 120, "documentsSaved": 35},
  "timestamps": {"startedAt": "2025-11-28T10:00:00Z"},
  "message": "Crawling site..."
}
```

## Notes
- Snapshots are runtime artifacts; do not commit them.
- Service enforces single active task per `kbId`.
- Frontend components query/update KB state (no per-job UI).
