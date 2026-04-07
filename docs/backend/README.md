# Backend Documentation

Comprehensive human-facing backend documentation.

## Contents

- [`BACKEND_REFERENCE.md`](./BACKEND_REFERENCE.md)
- [`AI_PROVIDER_ROUTING.md`](./AI_PROVIDER_ROUTING.md)
- [`AZURE_OPENAI_SETUP.md`](./AZURE_OPENAI_SETUP.md)
- [`DATA_ROOT_STORAGE_POLICY.md`](./DATA_ROOT_STORAGE_POLICY.md)
- [`TESTING_DEPENDENCY_INJECTION.md`](./TESTING_DEPENDENCY_INJECTION.md)

## Current focus areas

- `BACKEND_REFERENCE.md` now documents the broader Phase 4/5 ProjectState decomposition, the direct `app.shared.*` ownership of logging/projects-database/config helpers, the removal of obsolete `project_management`/database shim files, and the narrowed remaining compatibility surface (out-of-tree `app.core.app_settings` compatibility only, `/state`, and legacy blob fallback rows).

---

**Status**: Active  
**Last Updated**: 2026-04-02  
**Owner**: Engineering
