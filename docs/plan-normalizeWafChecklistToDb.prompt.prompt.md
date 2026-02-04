# Plan: Normalize WAF Checklist To DB

TL;DR: Introduce normalized SQL tables for checklist templates, items and evaluations; implement a `ChecklistEngine` service to sync ProjectState ↔ normalized rows and process agent results; add Alembic migration, backfill tools, routes, hooks, tests, and docs to enable analytics and robust agent-driven updates. Templates are fetched centrally from the Microsoft Learn MCP server (no per-project fetches) and cached locally before use.

Guardrail stance: informational, not blocking. Use percentage completion as the primary signal and explicitly highlight any uncovered critical/high items that could impact requirements/specs. The architect can proceed even if incomplete, but must see the risk.

### Steps
1. Add DB models and migration — create `backend/app/models/checklist.py` and an Alembic migration under `backend/migrations/versions/`.
2. Implement registry & engine — add `ChecklistRegistry` and `ChecklistEngine` in `backend/app/agents_system/checklists/registry.py` and `backend/app/agents_system/checklists/engine.py`. Registry must load only Microsoft Learn templates fetched via MCP/HTTP into a local cache under `backend/config/checklists/` (single fetch per template, not per project). (Suggested signature: `ChecklistEngine.process_agent_result(project_id: str, result: dict, db: AsyncSession) -> dict`)
3. Service wrapper + helpers — create `backend/app/agents_system/checklists/service.py` and normalization helpers in `backend/app/services/normalize_helpers.py`.
4. Hook into agent and router flows — register engine callbacks in `backend/app/agents_system/orchestrator/orchestrator.py` / `backend/app/agents_system/runner.py` and call sync in `backend/app/agents_system/agents/router.py` when `AAA_STATE_UPDATE` is merged.
5. API + CLI + maintenance scripts — add `backend/app/routers/checklists/checklist_router.py`, `scripts/backfill_waf.py`, and `scripts/maintain_checklists.py` for list/evaluate/resync operations.
6. Backfill, tests & docs — add backfill service `backend/app/services/backfill_service.py`, unit/integration tests under `backend/tests/` and update `docs/WAF_NORMALIZED_DB.md` and `docs/UX_IDE_WORKFLOW.md`.

### Further Considerations
1. Backfill: implement idempotent chunked backfill reading `ProjectState.state` (`backend/app/models/project.py`) and generating deterministic `item_id` (UUID v5) to avoid duplicates.
2. Consistency: dual-write (denormalized JSON + normalized rows) behind a feature flag during rollout; provide `sync_project_state_to_db(project_id, db)` and `sync_db_to_project_state(project_id, db)` helpers.
3. Performance & schema: add indexes on `(project_id, item_id)` and `(project_id, severity)`; prefer normalized tables for cross-project analytics.

---

**1) Schema (SQLAlchemy model field details)**

Create new models in `backend/app/models/checklist.py`:

- `ChecklistTemplate`
  - `id`: UUID PK
  - `slug`: string unique (e.g., "waf-2026-v1")
  - `title`: string
  - `description`: text
  - `version`: string
  - `source`: string (e.g., "microsoft-learn", "local")
    - `source_url`: string (required; Microsoft Learn URL)
    - `source_version`: string (required; doc version or fetched date)
  - `content`: JSON (original template)
  - `created_at`, `updated_at`: timestamps

- `Checklist` (an instantiated checklist for a project)
  - `id`: UUID PK
  - `project_id`: FK -> `Project.id` (index)
  - `template_id`: FK -> `ChecklistTemplate.id` (nullable)
  - `title`, `created_by`, `status` (open/archived)
  - `created_at`, `updated_at`

- `ChecklistItem`
  - `id`: UUID PK (deterministic from template + item path using UUID v5)
  - `checklist_id`: FK -> `Checklist.id` (indexed)
  - `template_item_id`: string (original id from template)
  - `title`: string
  - `description`: text
  - `pillar`: string (e.g., "network", "auth")
  - `severity`: enum (low/medium/high/critical)
  - `guidance`: JSON (recommended fix)
  - `metadata`: JSON (tags, remediations)
  - `created_at`, `updated_at`
  - Unique constraint on `(checklist_id, template_item_id)` and index on `(project_id, severity)` via join

- `ChecklistItemEvaluation`
  - `id`: UUID PK
  - `item_id`: FK -> `ChecklistItem.id` (indexed)
  - `project_id`: FK -> `Project.id`
  - `evaluator`: string (tool/agent/user)
  - `status`: enum (open/in-progress/fixed/false-positive)
  - `score`: integer or float (optional severity numeric)
  - `evidence`: JSON (artifacts, citations)
  - `source_type`: string (e.g., `agent-validation`, `manual`)
  - `source_id`: string (tool run id)
  - `created_at`, `updated_at`
  - Composite index on `(project_id, item_id, created_at)`

Notes:
- All tables should include `created_at`/`updated_at` timestamps and FK cascade rules.
- Add indexes: `IX_checklist_project_id`, `IX_item_checklist_id`, `IX_evaluation_project_item`.

---

**2) Alembic migration outline**

- Migration file `backend/migrations/versions/<ts>_create_waf_normalized.py`:
  - `upgrade`: create tables `checklist_templates`, `checklists`, `checklist_items`, `checklist_item_evaluations` with fields above, constraints, and indexes.
  - `downgrade`: drop evaluations, items, checklists, templates in reverse order.
- Add migration note about required backfill and estimated runtime.
- Include a helper script to run migration and `scripts/backfill_waf.py` in dry-run mode before execute.

---

**3) Service & Engine (method signatures + responsibilities)**

Add `ChecklistRegistry` in `backend/app/agents_system/checklists/registry.py`
- Responsibilities: load Microsoft-only templates from `backend/config/` that were fetched once via MCP/learn fetch (no per-project fetch), return `ChecklistTemplate` objects.
- Key API:
  - `def load_builtins() -> list[ChecklistTemplate]`
  - `def get_template(slug: str) -> Optional[ChecklistTemplate]`
  - `def register_template(template: ChecklistTemplate) -> None`

Add `ChecklistEngine` in `backend/app/agents_system/checklists/engine.py`
- Responsibilities: process agent results, sync `ProjectState.state` ↔ normalized rows, compute "next actions", generate AAA_STATE_UPDATE if needed.
- Suggested class and method signatures (no implementation here):
  - `class ChecklistEngine:`
    - `def __init__(self, db_session_factory: Callable[[], AsyncSession], registry: ChecklistRegistry, feature_flag: bool = False) -> None`
    - `async def process_agent_result(self, project_id: UUID, agent_result: dict) -> dict`
      - Extract `AAA_STATE_UPDATE` / `wafChecklist` from `agent_result`, normalize items, create/update `Checklist`, `ChecklistItem`, and `ChecklistItemEvaluation`. Return a merge summary dict.
    - `async def sync_project_state_to_db(self, project_id: UUID, project_state: dict, chunk_size: int = 500) -> dict`
      - Idempotent backfill of items and evaluations from `project_state`.
    - `async def sync_db_to_project_state(self, project_id: UUID) -> dict`
      - Rebuild `wafChecklist` JSON from normalized rows (for compatibility reads).
    - `async def evaluate_item(self, project_id: UUID, item_id: UUID, evaluation_payload: dict) -> ChecklistItemEvaluation`
    - `async def list_next_actions(self, project_id: UUID, limit: int = 20, severity: str | None = None) -> list[dict]`
    - `async def backfill_all_projects(self, batch_size: int = 50) -> dict`
- Use `uuid.uuid5(namespace_uuid, f"{project_id}:{template_slug}:{template_item_id}")` to generate deterministic `ChecklistItem.id`.
  - Deterministic namespace: `WAF_NAMESPACE_UUID` config value (repo-wide). Do not generate random IDs.

Add `ChecklistService` wrapper in `backend/app/agents_system/checklists/service.py`
- Thin adapter exposing engine methods to API, CLI, and hooks. Use dependency injection to get DB session (existing `get_db`).

Transaction & dual-write rules:
- When `FEATURE_WAF_NORMALIZED` is enabled, do dual-write within a DB transaction:
  1. Begin transaction
  2. Apply normalized writes (insert/update rows)
  3. Update `ProjectState.state` JSON (persist via `update_project_state`)
  4. Commit
- If feature disabled, keep existing single JSON path.

---

**4) Hook Integration (exact places to modify)**

- `AgentOrchestrator` initialization in `backend/app/agents_system/orchestrator/orchestrator.py`
  - Add optional `on_end` callback param or accept an events list. Register `ChecklistEngine.process_agent_result` as `on_end`.
  - Ensure `on_end` is awaited after agent execution completes and BEFORE persistence if you want to mutate/augment `AAA_STATE_UPDATE` pre-merge, or AFTER persistence if you prefer sync-from-state.

- `AgentRunner.initialize` in `backend/app/agents_system/runner.py`
  - Instantiate `ChecklistEngine` and pass `engine.process_agent_result` to `AgentOrchestrator` as `on_end`.

- Router processing in `backend/app/agents_system/agents/router.py`
  - In `_apply_legacy_updates` / where `update_project_state` is called: after `update_project_state(...)` completes, call `ChecklistEngine.sync_project_state_to_db(project_id, project_state)` (background task or awaited depending on consistency needs).
  - For synchronous guarantee, await the sync; for latency reduction, schedule background job and return early.
  - Add a cheap cached lookup for templates in engine/registry so per-request fetch does not hit MCP; MCP is used only by offline import script.

- LangGraph workflow integration
  - In LangGraph/agent orchestration nodes, after each tool call that yields `AAA_STATE_UPDATE` or validations, invoke a checklist update step that recomputes completion and records uncovered items.
  - Keep chat messaging conversational and only when relevant (e.g., after an update or when asked); avoid per-step spam. Allow the architect to correct.
  - Provide a LangGraph edge or node that can be reused across flows to avoid duplicate logic; ensure it is idempotent per run.
  - Add a status counter surfaced to FE (see FE section) with thresholds: <50% red, <80% yellow, >95% green.

- `aaa_record_validation_results` tool (already emits structured AAA_STATE_UPDATE):
  - No change required for tool; engine will normalize incoming evaluations and insert `ChecklistItemEvaluation` rows.

---

**5) API contract (endpoints)**

Create router `backend/app/routers/checklists/checklist_router.py` mounted under `/api/projects/{project_id}/checklists`

- GET `/api/projects/{project_id}/checklists`
  - Query params: `template_slug?`, `status?`, `severity?`, `limit?`, `offset?`
  - Response: `{ "checklists": [ { checklist metadata, items_count, last_synced_at } ] }`
  - 200 OK

- GET `/api/projects/{project_id}/checklists/{checklist_id}`
  - Response: `{ "id","project_id","template_id","title","items": [ { item fields + latest_evaluation } ] }`
  - 200 OK or 404

- PATCH `/api/projects/{project_id}/checklists/{checklist_id}/items/{item_id}`
  - Body: `{ "status": "fixed"|..., "assignee": "user@example.com"|null, "evidence": {...}, "comment": "string" }`
  - Behavior: create a new `ChecklistItemEvaluation` record with `source_type: manual` and update `ChecklistItem` metadata if needed.
  - Response: updated item + evaluation. 200 on success.

- POST `/api/projects/{project_id}/checklists/{checklist_id}/items/{item_id}/evaluate`
  - Body: `Validation payload` equivalent to `aaa_record_validation_results` tool shape (allow batch).
  - Behavior: engine.evaluation path. Returns merge summary and updated `wafChecklist` chunk.
  - 202 Accepted if processed async; 200 if sync.

- GET `/api/projects/{project_id}/checklists/{checklist_id}/progress`
  - Returns completion metrics: total items, completed items, percent complete, latest evaluation timestamp.
  - Returns a simple severity breakdown and a small list of top uncovered items (no paging; keep it simple).

- POST `/api/projects/{project_id}/checklists/resync`
  - Body: `{ "mode": "from_state"|"from_db", "dry_run": bool }`
  - Behavior: triggers `sync_project_state_to_db` or `sync_db_to_project_state`. Return task id or result summary.

Auth & validation: reuse existing project router dependencies and DB session injection.

Compatibility endpoints:
- Provide `/api/projects/{project_id}/project_state` unchanged; implement thin wrapper that reconstructs `wafChecklist` JSON from normalized tables if feature flag is on.

---

**6) Backfill algorithm (detailed, idempotent, chunked)**

Overview: For each project, read `ProjectState.state` JSON; if JSON contains `wafChecklist`, iterate template->items and create/merge normalized rows in chunks.

Algorithm steps (pseudocode description; avoid code blocks per plan style):
1. Acquire list of projects (batch by `project_id`, `limit`).
2. For each project:
   - Load `project_state = read_project_state(project_id)`
   - If no `project_state["wafChecklist"]`, skip.
   - For each `template` in `wafChecklist["templates"]`:
     - For each `item` in `template["items"]`:
       - Compute deterministic `item_uuid = uuid5(NAMESPACE_UUID, f"{project_id}:{template_slug}:{item['id']}")`
       - Upsert `ChecklistTemplate` (if not exists) based on `template_slug` and version.
       - Upsert `Checklist` (per project + template)
       - Upsert `ChecklistItem` by `item_uuid` with normalized fields (title, description, pillar, severity, guidance).
   - For each `evaluation` found in `wafChecklist["evaluations"]`:
     - Upsert `ChecklistItemEvaluation` with `item_id` as computed above. Use `source_id` to dedupe.
3. Commit every N items (chunk_size, default 500) to avoid long transactions.
4. After project-level backfill success, write a `backfill_progress` record to a local audit table (or file) with counts and checksum of migrated data.
5. Support `dry_run` mode: compute rows and validate but do not write.
6. Support retry/resume by checking `backfill_progress` and skipping completed projects.

Backfill safety: validate sample of normalized rows vs original JSON (random 1% sample) and report mismatches; do not mark project as migrated until verification passes.

---

**7) Tests (explicit)**

Unit tests (fast, isolated)
- `backend/tests/services/test_checklist_models.py`
  - Validate SQLAlchemy model constraints, indexes, and deterministic ID generation function produces stable UUIDs.
- `backend/tests/services/test_normalize_helpers.py`
  - Input: sample `wafChecklist` JSON; assert normalized output matches expected dict shape.
- `backend/tests/services/test_checklist_service.py`
  - Mock DB session; test `evaluate_item`, `list_next_actions`, `sync_project_state_to_db` in small scenarios.
  - Add progress computation test: total vs completed items yields expected percentage.

Integration tests (DB + router)
- `backend/tests/agents_system/test_agent_checklist_integration.py`
  - Run a mocked agent result containing an `AAA_STATE_UPDATE` with wafer evaluation; assert:
    - `ProjectState.state` merged correctly (existing behavior)
    - Normalized rows created/updated: `ChecklistItem`, `ChecklistItemEvaluation` exist and have correct fields.
  - Run both synchronous and async modes.
  - Verify progress endpoint returns expected completion percentage after evaluations.

Backfill tests
- `backend/tests/test_backfill.py`
  - Use temporary test DB fixture with few sample projects; run backfill in `dry_run` then `execute`, assert idempotency (two runs same results), chunking behavior, and verification sample.

API tests
- `backend/tests/test_api/test_waf_checklists.py`
  - Test GET, PATCH, POST evaluate endpoints; check auth, error cases, and 404s.
  - Test progress endpoint and response shape.

E2E
- Update `scripts/e2e/aaa_e2e_runner.py` to assert normalized DB rows exist for test projects.

How to run tests:
- Use existing test task: run backend unit tests with repository `pytest` tasks described in workspace (e.g., run `Run backend unit tests` task).

---

**8) Docs & UX changes**

Files to update:
- `docs/WAF_NORMALIZED_DB.md` — design doc: schema, rationale, FAQ, migration runbook.
- Update `docs/UX_IDE_WORKFLOW.md` — add checklist lifecycle: init, agent-evaluate, resync, manual evaluate.
- Add API reference in `docs/` showing example requests/responses for checklist endpoints (compatibility shapes).
- Add frontend notes: expose checklist progress, completion %, and latest evaluation per item in the UI; ensure type alignment with `frontend/src/types/api-artifacts.ts`.
 - Frontend display: keep existing UX layout—checklist entry in the left pane; clicking shows the checklist, and clicking an item shows details in the middle pane. Include status/severity, evidence link, last evaluated, a progress badge with thresholds (<50% red, <80% yellow, >95% green), and a simple “uncovered items” callout (top 3 by severity). Chat mentions only when asked or after meaningful updates.

Documentation must include:
- Backfill runbook with `dry_run` steps, expected runtime, verification steps, rollback instructions.
- Feature flag (`FEATURE_WAF_NORMALIZED`) behavioral note and default state.

---

**9) Rollout & operational plan (step-by-step)**

1. Implement schema + migration (merge in feature branch).
2. Deploy migration to staging DB.
3. Deploy app with `FEATURE_WAF_NORMALIZED=false`.
4. Run `scripts/backfill_waf.py --dry-run --batch-size=50` on staging; verify results.
5. Run `scripts/backfill_waf.py --execute` (staging) and run verification script.
6. Flip `FEATURE_WAF_NORMALIZED=true` on staging and enable dual-write mode for a period (30 days).
7. Monitor metrics (error rates, migration mismatch counts).
8. After confidence, run backfill on production (scheduled maintenance window if necessary).
9. Flip feature to normalized-only and deprecate denormalized artifacts with cleanup migration later (document retention window).

---

**10) Monitoring, metrics, and alerts**

Instrument and emit metrics:
- `waf.backfill.progress` (projects migrated / total)
- `waf.sync.errors` (count, project_id label)
- `waf.evaluations.per_minute`
- `waf.dup_items.detected` (if id collisions occur)
 - `waf.checklist.progress` (percent complete per project/checklist)

Note: template versioning and backfill enhancements are deferred; start with frozen template cached from MCP and revisit version migration later.
Evaluation history: keep only the latest evaluation per item (no full history) to keep payloads light; include minimal evidence fields needed for status and callouts.

Add alerts:
- Backfill failures > X projects
- Sync errors > Y per hour
- ProjectState vs DB mismatch rate > 0.5%

Log format:
- Include `project_id`, `checklist_id`, `item_id`, `source_type`, `source_id` in structured logs.

---

**11) Acceptance criteria (concrete)**

- Migration creates normalized tables and indexes without data loss in downgrade.
- Backfill dry-run reports no schema mapping errors for current test dataset.
- Backfill execute produces normalized rows; for a sample of projects, `sync_db_to_project_state(project_id)` reconstructs JSON identical (or semantically equivalent) to original `ProjectState.state` `wafChecklist`.
- Agent-driven `AAA_STATE_UPDATE` that includes WAF evaluation results results in at least one `ChecklistItemEvaluation` row created (for matching item) when processed.
- API endpoints return normalized data and pass integration tests.
- Dual-write mode does not produce duplicated item rows when run twice (idempotent).
- Performance: backfill completes at acceptable rate (document measured throughput).

---

**12) Files to create or modify (concise list with purpose)**

- Create: `backend/app/models/checklist.py` — SQLAlchemy models.
- Create migration: `backend/migrations/versions/<ts>_create_waf_normalized.py`.
- Create: `backend/app/agents_system/checklists/registry.py` — load templates.
- Create: `backend/app/agents_system/checklists/engine.py` — core engine.
- Create: `backend/app/agents_system/checklists/service.py` — API wrapper.
- Modify: `backend/app/agents_system/runner.py` — register callbacks.
- Modify: `backend/app/agents_system/orchestrator/orchestrator.py` — accept `on_end`.
- Modify: `backend/app/agents_system/agents/router.py` — call sync post-merge.
- Create: `backend/app/routers/checklists/checklist_router.py` — endpoints.
- Create: `scripts/backfill_waf.py`, `scripts/maintain_checklists.py` — admin tools.
- Create: `backend/app/services/backfill_service.py` — backfill logic.
- Create tests under `backend/tests/` as listed above.
- Create docs: `docs/WAF_NORMALIZED_DB.md` and update `docs/UX_IDE_WORKFLOW.md`.

---

**13) Estimated effort & phasing**

- Phase 1 (Schema, migration, simple service stubs, add engine signatures): 2–3 days
- Phase 2 (Backfill script, one-pass backfill in staging, tests): 3–5 days
- Phase 3 (Hooks integration, API endpoints, tests, docs): 2–4 days
- Phase 4 (Production backfill, monitoring, cutover): 1–3 days (operations)
- Total: ~2–3 weeks with testing and verification (can be split into multiple PRs per phase).

---

**14) Open decisions / clarifying questions**
1. Feature flag behavior: prefer dual-write (recommended) or immediate cutover? (dual-write recommended)
2. Deterministic ID namespace: do you want a repo-wide namespace UUID or per-template namespace? (recommend repo-wide `WAF_NAMESPACE_UUID` env var)
3. Retention policy: how long keep denormalized JSON after cutover? (recommend 30 days)
4. Alembic location: repo currently has `backend/migrations` — confirm migration style and current head.

---

Next: I can produce the SQLAlchemy model stubs + Alembic migration draft (Phase 1) or expand any section above into an implementation checklist. Which would you like me to produce now?
