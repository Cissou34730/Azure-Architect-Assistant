# Purpose

Define the single storage rule for agents: all persisted backend runtime data is rooted at `DATA_ROOT`.

# Current State

- `DATA_ROOT` is the canonical base path.
- Storage paths are derived from `DATA_ROOT` by default.
- Startup validation rejects any storage/database path outside `DATA_ROOT`.

# Do / Don't

- **Do** set `DATA_ROOT` in `.env` for each environment.
- **Do** keep `PROJECTS_DATABASE`, `INGESTION_DATABASE`, `DIAGRAMS_DATABASE`, cache dirs, and uploaded docs under `DATA_ROOT`.
- **Don't** add new runtime file writes to hardcoded repo-local paths.
- **Don't** bypass `AppSettings` for storage paths.

# Decision Summary

- Single source of truth for persistence location: `DATA_ROOT`.
- Any explicit storage override remains allowed only if still under `DATA_ROOT`.
- If violated, fail fast at startup.

# Update Triggers

Update this doc when:

- new persisted storage type is introduced,
- path validation rules change,
- defaults for derived storage paths change.
