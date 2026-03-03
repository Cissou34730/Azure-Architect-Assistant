# Router Refactor Backlog

Current status after latest SRP/error-handling/service-boundary refactors:

## Completed

1. Unified router dependency source on `app.dependencies` (removed direct router usage of `app.service_registry`).
2. Consolidated router-local `*_operations.py` orchestration layers into `app/services/kb/*_orchestration_service.py`.
3. Standardized ingestion router 500 mappings through shared helper (`internal_server_error`) and removed broad `Exception -> 404` mapping.
4. Unified API path convention to `/api` (removed runtime `/api/v1` router mount split).
5. Standardized checklist router exception mapping through shared helpers.
6. Added router guardrail tests enforcing:
   - no `/api/v1` routes,
   - no router-local `*_operations.py`,
   - no direct router imports of `app.service_registry`.

## Remaining (highest priority first)

1. Extend guardrails from tests to lint/CI policy checks (optional hardening).
