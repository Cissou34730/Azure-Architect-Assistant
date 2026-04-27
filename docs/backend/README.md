# Backend Documentation

Comprehensive human-facing backend documentation.

## Contents

- [`BACKEND_REFERENCE.md`](./BACKEND_REFERENCE.md)
- [`AI_PROVIDER_ROUTING.md`](./AI_PROVIDER_ROUTING.md)
- [`AZURE_FOUNDRY_SETUP.md`](./AZURE_FOUNDRY_SETUP.md)
- [`DATA_ROOT_STORAGE_POLICY.md`](./DATA_ROOT_STORAGE_POLICY.md)
- [`TESTING_DEPENDENCY_INJECTION.md`](./TESTING_DEPENDENCY_INJECTION.md)
- [`EVAL_HARNESS.md`](./EVAL_HARNESS.md)

## Current focus areas

- `BACKEND_REFERENCE.md` now documents the broader Phase 4/5 ProjectState decomposition, the direct `app.shared.*` ownership of logging/projects-database/config helpers, the removal of obsolete `project_management`/database shim files, the canonical `/pending-changes` v1 review surface, the new dedicated `pending_change_sets` / `artifact_drafts` persistence backing that API, and the narrowed remaining compatibility surface (out-of-tree `app.core.app_settings` compatibility only, `/state`, hidden `/changes` aliases, and legacy blob fallback rows).
- `BACKEND_REFERENCE.md` also documents the new architect-profile settings endpoints, the normalized `project_notes` CRUD surface that backs the workspace notes tab, the `/api/projects/{projectId}/quality-gate` read surface plus `quality_gate_service.py`, and the dedicated `/api/projects/{projectId}/trace` timeline route backed by `trace_service.py` over persisted `project_trace_events`.
- `EVAL_HARNESS.md` documents the Phase 0 report-driven baseline harness under `backend/tests/eval/`, including the committed golden scenario layout and the targeted pytest command.
- `BACKEND_REFERENCE.md` now documents the typed stage-classification contract (`stage`, `confidence`, `source`, `rationale`), the SSE/workflow-result propagation path, and the narrower prompt-loader behavior where stage workers load dedicated prompt files without inheriting orchestrator routing text.
- `BACKEND_REFERENCE.md` now also covers the minimal server-side validation tool surface: `aaa_validate_mermaid_diagram` exposes Mermaid syntax checks with line-aware diagnostics, `aaa_validate_iac_bundle` validates ARM/JSON/YAML plus lightweight Bicep/Terraform structure, and both tools are stage-scoped through the canonical runtime tool registry.
- `BACKEND_REFERENCE.md` also documents the new unified `research` facade plus grounded evidence-packet shape for `propose_candidate`, and the standalone `azure_retail_prices` tool path that the cost tool now calls before persisting `costEstimates`.

- `BACKEND_REFERENCE.md` also documents P10 diagram quality improvements: the `diagram_explanation` and `how_to_read` optional fields on the `aaa_create_diagram_set` tool input, and the new pure `validate_diagram_semantics(diagram_code, diagram_type)` function in `semantic_validator.py` that performs non-blocking structural checks (missing actors, unlabeled flows, placeholder text, bare abbreviations, missing external dependencies) surfaced as warnings in the validation pipeline.

---

**Status**: Active  
**Last Updated**: 2026-04-18  
**Owner**: Engineering
