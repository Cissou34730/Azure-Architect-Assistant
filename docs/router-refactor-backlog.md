# Router Refactor Backlog

Open items after the latest SRP/error-handling cleanup:

1. Unify dependency source across routers (`app.dependencies` vs `app.service_registry`).
2. Unify API versioning conventions (`/api` and `/api/v1` split).
3. Review whether thin `*_operations.py` layers (`kb_query`, `kb_management`) should be consolidated into `app/services/*`.
4. Remove remaining ad-hoc `except Exception` paths that still map to hardcoded status/details without shared helpers.

