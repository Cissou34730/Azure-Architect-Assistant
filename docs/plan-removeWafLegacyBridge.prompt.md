# Plan: Remove Legacy WAF Checklist Bridge

## TL;DR
Eliminate the dual-write bridge layer that converts between the legacy `wafChecklist` JSON format and the normalized DB schema. The normalized DB tables (`Checklist`, `ChecklistItem`, `ChecklistItemEvaluation`) become the single source of truth. Agent tool output also migrates to normalized enum values. Executed in 5 independent phases, each verifiable and safe to merge separately.

---

## Phase 0 — Enable normalized path by default (1 file, zero risk)

1. In `backend/app/core/settings/waf.py`, change `aaa_feature_waf_normalized` default from `False` to `True`.
   - All dual-write and DB-read paths are already implemented and gated on this flag; flipping it activates them with no code change.

**Verification**: Run backend tests; existing tests that mock the flag must pass.

---

## Phase 1 — Decouple wafChecklist writes from the JSON state blob

**Goal**: `wafChecklist` data is written directly from `persist.py` to the engine, never merged into `ProjectState.state`. The JSON blob stops storing WAF data.

Steps (independent within phase):

1. **`persist.py` (`apply_state_updates_node`)**: Before calling `update_project_state()`, pop `wafChecklist` from `combined_updates`. Call `engine.sync_project_state_to_db(project_id, {"wafChecklist": waf_data})` directly (reuse existing method). Pass remaining updates to `update_project_state()`.

2. **`project_context.update_project_state()`**: Remove the `engine.sync_project_state_to_db()` dual-write call (now handled exclusively in persist.py). The merge/validate/persist pipeline operates with no WAF knowledge.

3. **`project_context.read_project_state()`**: Remove the feature-flag guard — always reconstruct `wafChecklist` from DB for agent context. The JSON blob no longer populates it. If DB is empty and JSON blob has legacy data, keep the one-time backfill trigger (temporary, removed in Phase 4).

4. **`/resync` endpoint** (`checklist_router.py`): Update `resync_from_project_state` to read from the legacy JSON blob only if it still exists (backward compat for pre-migration projects). Flag for deletion in Phase 4.

**Relevant files**:
- `backend/app/agents_system/langgraph/nodes/persist.py`
- `backend/app/agents_system/services/project_context.py`

**Verification**: Integration test — run an agent cycle, confirm `ProjectState.state` JSON has no `wafChecklist` key, confirm `ChecklistItemEvaluation` rows are created.

---

## Phase 2 — Remove wafChecklist from state models

**Goal**: `AAAProjectState` no longer has a `waf_checklist` field. The frontend `ProjectState` type drops it.

Steps:

1. **`aaa_state_models.py`**: Remove `waf_checklist: WafChecklist = Field(...)` from `AAAProjectState`. Remove `WafChecklist`, `WafChecklistItem`, `WafEvaluation` classes (if no other consumer). Update `ensure_aaa_defaults()` to not initialize `wafChecklist`.

2. **`frontend/src/types/api-project.ts`**: Remove `wafChecklist: WafChecklist` from the `ProjectState` interface. Remove import of `WafChecklist` if it becomes orphaned here.

3. **`frontend/src/features/projects/components/unified/LeftInputsArtifactsPanel.tsx` (line ~75)**: The `waf: projectState.wafChecklist.items.length` count badge reads from the legacy state — replace with a call to the normalized API (`checklistService.fetchNormalizedChecklist`) or use the summary count from the checklist API response.

*Depends on Phase 1 completing so the JSON blob no longer populates wafChecklist.*

**Verification**: TypeScript compiles with no errors. `LeftInputsArtifactsPanel` still shows item count.

---

## Phase 3 — Migrate agent tool output to normalized enum values

**Goal**: `aaa_validation_tool` emits `status: "fixed"|"in_progress"|"open"` instead of `"covered"|"partial"|"notCovered"`. The bridge mapping functions become unused.

Steps:

1. **`aaa_validation_tool.py`**:
   - Change `WafCoverageStatus` enum values to `"fixed"`, `"in_progress"`, `"open"` (remove `"covered"`, `"partial"`, `"notCovered"`).
   - Update docstrings and tool description string accordingly.

2. **`aaa_state_models.py`**: Update `WafEvaluation.status` type annotation to match new enum.

3. **`frontend/src/types/api-artifacts.ts`**: Update `WafEvaluation.status` union type from `"covered"|"partial"|"notCovered"` to `"fixed"|"in_progress"|"open"`.

4. **`frontend/src/services/checklistService.ts`**: Update `mapNormalizedStatusToLegacy()` — with both sides now using normalized values, this function becomes an identity mapping; inline or rename to `mapStatusToDisplay()`.

5. **Engine direct write**: With the tool now outputting normalized values, `sync_project_state_to_db()` receiving `wafChecklist` items no longer needs `map_legacy_status()`. The `_normalize_evaluation_status()` in `sync_writer.py` no longer needs to call `map_legacy_status`. Verify the mapping still round-trips correctly (or becomes a direct pass-through).

*Parallel with Phase 2. Depends on Phase 1.*

**Verification**: Agent test with new status values — confirm `ChecklistItemEvaluation.status` stored as `EvaluationStatus.FIXED` directly.

---

## Phase 4 — Delete legacy bridge code

Once Phases 1–3 are complete and verified, delete the bridge:

1. **`engine.py`**: Remove `process_agent_result()` (replaced by direct persist.py→engine call). Remove feature flag guard (`self.feature_flag` field and all `if not self.feature_flag` checks). Remove compatibility helpers (`default_template_slug()`, `_select_bootstrap_template_slugs()`, `_extract_known_pillars()`).

2. **`sync_writer.py`**: Remove `sync_legacy_item()`, `_extract_legacy_evals()`, `_create_evaluation()`, `_existing_eval_fingerprints()`, `_evidence_fingerprint()`. Remove `_get_or_create` TypeVar `_T` and the `Callable/Awaitable` imports if unused. Remove `status_value()` module function.

3. **`state_parser.py`**: Remove `parse_project_state()`, `extract_checklists_from_waf_data()`, `normalize_items_container()`. If class becomes empty, delete the file and the `ChecklistStateParser` import in `engine.py`.

4. **`normalize_helpers.py`**: Remove `LEGACY_STATUS_MAP`, `NORMALIZED_STATUS_MAP`, `map_legacy_status()`, `map_normalized_status()`. Remove `_resolve_pillars`, `_extract_evidence_text`, `_build_legacy_item`, `reconstruct_legacy_waf_json()`. Only `merge_reconstructed_waf_payloads()`, `validate_normalized_consistency()`, and `_extract_item_ids()` stay (used by assembler and tests). Consider renaming the file from `normalize_helpers.py` to `waf_helpers.py` or similar.

5. **`read_assembler.py`**: Update `reconstruct_from_checklists()` to use normalized status values directly (no `map_normalized_status()` call back to legacy strings).

6. **`waf.py` (settings)**: Remove `aaa_feature_waf_normalized` flag entirely (always on now). Remove from `ChecklistEngine.__init__` and all callers.

7. **`/resync` endpoint**: Delete or repurpose to only reconstruct from already-normalized DB data (no legacy JSON source).

8. **`backfill_service.py`**: Remove legacy JSON→DB sync path; backfill service can remain for seeding from templates but not for JSON migration.

**Relevant files**:
- `backend/app/agents_system/checklists/engine.py`
- `backend/app/agents_system/checklists/sync_writer.py`
- `backend/app/agents_system/checklists/state_parser.py`
- `backend/app/agents_system/checklists/normalize_helpers.py`
- `backend/app/agents_system/checklists/read_assembler.py`
- `backend/app/core/settings/waf.py`

**Verification**: `uvx ruff check` passes. No references to `sync_legacy_item`, `map_legacy_status`, `wafChecklist` in engine/writer/parser.

---

## Phase 5 — Update tests

1. **`test_checklist_engine.py`**: Remove `wafChecklist`-keyed input fixtures; replace with direct calls to `ensure_project_checklists` + `evaluate_item`.

2. **`test_processor.py`**: Remove `AAA_STATE_UPDATE.wafChecklist` mock payloads using old status values; update to normalized values.

3. **`test_validation_tool_and_models.py`**: Update `WafCoverageStatus` assertions to new enum values.

4. **`test_backfill_service.py`**, **`test_normalize_helpers.py`**: Update or delete tests for removed functions.

5. **Frontend `checklist-panel.spec.ts`, `waf-normalized.spec.ts`**: Update mock status values to `"fixed"|"in_progress"|"open"`.

6. Any test referencing `aaa_feature_waf_normalized` should remove that mock/override.

---

## Decisions
- Tool output migrates to normalized enum values (Phase 3) — no more covered/partial/notCovered in agent output
- `ProjectState.state` JSON blob stops storing `wafChecklist` after Phase 1
- Agents still receive `wafChecklist` in context (reconstructed from DB by `sync_db_to_project_state`)
- `/resync` endpoint is removed (no more legacy JSON source to resync from)
- Phases 2 and 3 are parallel (both depend on Phase 1)
- Phase 4 requires Phases 1–3 complete

## Scope exclusions
- Agent prompt rewording (out of scope)
- WAF template management changes (out of scope)
- Alembic migration for `project_states.state` column (column stays; only the JSON content changes — no schema migration needed)

---

## Further considerations
1. **Pre-migration projects**: Projects created before Phase 1 ships still have `wafChecklist` in their JSON blob. The one-time backfill trigger in `read_project_state()` handles this automatically on first read — it must stay until Phase 4 and only be removed once all production projects have been backfilled.
2. **Rollback**: Since `ProjectState.state` content changes organically, rollback to pre-Phase-1 means the JSON blob has no `wafChecklist` — the old code would show an empty checklist. Consider adding a DB column `has_waf_normalized` flag per project for safe rollback if needed.
