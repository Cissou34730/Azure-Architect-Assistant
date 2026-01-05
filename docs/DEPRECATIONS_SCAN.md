# Deprecations Sanity Check (2025-12-24)

This report tracks deprecated or legacy patterns identified across the codebase and proposed fixes.

## Summary
- Backend tests pass cleanly; third‑party Pydantic `validate_default` noise is suppressed in pytest configuration.
- Pydantic v2 migration gaps found in two response models and fixed.
- SQLAlchemy v1‑style query usage present in ingestion repository; not hard‑deprecated but recommended to modernize.
- Frontend shows no `@deprecated` annotations or legacy React APIs.

## Findings

### Pydantic (v2)
- Fixed inner `class Config` usage (v1 style) by replacing with `model_config`:
  - backend/app/routers/diagram_generation/ambiguities.py
  - backend/app/routers/diagram_generation/diagram_sets.py
- No occurrences of other v1 patterns found:
  - `parse_obj(...)`, `parse_file(...)`, `Field(..., env=...)`, `allow_population_by_field_name`.
- Pytest warning filter added to ignore third‑party `validate_default` warning message.

### SQLAlchemy (v2)
- Legacy `session.query(...)` patterns detected in:
  - backend/app/ingestion/infrastructure/queue_repository.py
- Current usage includes `session.get(...)` and `select(...)` in other code. While `session.query` is still supported, prefer v2 patterns:
  - Replace query+filter/limit with `select(Model).where(...).order_by(...).limit(...); session.execute(select_stmt).scalars().all()`
  - Use `session.execute(delete(...))` for bulk deletes.

### Frontend (React/TypeScript)
- No `@deprecated` annotations found.
- No `ReactDOM.render(...)` usage; React 18+ `createRoot` appears to be in place.

## Recommendations
- Continue enforcing Pydantic v2 style with `model_config`, `field_validator`, and `SettingsConfigDict`.
- Plan a small refactor to migrate `QueueRepository` methods from `session.query` to `select()/execute` for consistency and forward compatibility.
- Optionally enable stricter pytest policy:
  - Treat `DeprecationWarning` as errors for first‑party code while ignoring third‑party messages.

## Verification
- Backend unit tests: 37 passed, 1 skipped, no deprecation warnings reported.
- Full warnings run: third‑party `validate_default` ignored via `pytest.ini`.
