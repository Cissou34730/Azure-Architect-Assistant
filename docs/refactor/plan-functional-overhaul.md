# AAA Functional Overhaul — Master Plan

> **Status**: Review corrections applied — ready for implementation  
> **Supersedes**: `docs/refactor/AAA-refactor.md` (13-phase plan)  
> **Branch**: TBD (one branch per lane or per phase, per repo conventions)  
> **Date**: 2026-04-17  
> **Origin**: Functional analysis of assistant UX, prompt surface, orchestration, tools, and frontend

---

## Design decisions captured from review

| Decision | Choice | Rationale |
|---|---|---|
| Relationship to AAA-refactor.md | **Supersede** | Single source of truth for all runtime, UX, and tool work |
| Azure live tool auth | **No authenticated Azure connectivity in v1**. B.1 (Retail Prices) is public/no-auth. B.2/B.3/B.6 removed from v1 scope. | Auth/runtime complexity is premature; requirements don't mandate live subscriptions |
| IaC validation | **Syntax + schema** validation of generated code before delivery | IaC is a deliverable, not deployed by the agent; quality assurance before handoff |
| Legacy AgentChatWorkspace | **Retire** once unified workspace reaches parity | Single chat surface reduces maintenance |
| Storage backend | **SQLite** (current stack) | Simpler deployment; sufficient for single-user architect tool |
| Pending changes v1 scope | **Approve and Reject only** — no Edit, no Revise | Edit/Revise add UX and backend complexity without v1 payoff |
| PCS rejection reason | **Stored durably** in `pending_change_sets.rejection_reason` column | Audit trail for rejected proposals |
| Diff "before" source | **Computed at review time** against canonical state | No snapshots; diffs always show current state vs proposed patches |
| Approval-first universality | **All stages** use PendingChangeSet — including `clarify` and `pricing` | No stage bypasses canonical state mutation |
| FR-018 | **Typed contract** via `WorkflowStageResult.structured_payload` | No text-pattern parsing in the frontend |
| Streaming transport | **`fetch` + `ReadableStream`** (not `EventSource`) | Allows POST body, custom headers, fine-grained backpressure |
| `agent_prompts.yaml` role | **Manual backup only** — not an automatic fallback | Prevents duplication with modular prompt system |
| ArchitectProfile | **Strictly single-user** in v1 — no user_id FK | No multi-user hints in schema |
| Stale ADR rule | **None in v1** — no age-based staleness detection | Premature without real usage data |
| `project_notes.source_message_id` | **Required** (optional field) | Supports "pin from chat" traceability |
| `orchestrator_routing.yaml` scope | **Classifier/orchestrator only** — not injected into every stage worker | Prevents token waste in stage prompts |
| User-facing prompt fragments | **`prompts/templates/`** folder | i18n-ready, separate from stage logic |
| SaaS advisor activation | **Only when SaaS is a valid design option** | Don't waste tokens on SaaS analysis for on-prem-only requirements |
| SSE incremental text event | **New `text` event type** for progressive token rendering | Enables word-by-word streaming in the chat UI |

---

## Non-negotiable principles (from AAA-refactor, carried forward)

1. **Approval-first state model**: No mutation of canonical state without explicit approval. **All stages** — including `clarify` and `pricing` — first produce PendingChangeSets. No exceptions.
2. **Typed contracts over free text**: No parsing of state from LLM output. Eliminate `AAA_STATE_UPDATE` regex. All outputs structured and validated via Pydantic. Frontend never parses text patterns — structured UI interactions use `WorkflowStageResult.structured_payload`.
3. **Deterministic domain services**: Mindmap coverage computed by deterministic backend code (not LLM). WAF evaluation is a deterministic matcher (LLM generates findings only). Deterministic merge for dedup, clustering, provenance.
4. **SSE streaming preservation**: Backend SSE streaming (via `execute_project_chat_stream`) must be preserved and never broken throughout every phase of implementation. Every stage worker must support the existing `event_callback` streaming pattern. Transport: `fetch` + `ReadableStream` (not `EventSource`).
5. **Worker tool-call iteration limit**: LLM workers are limited to **5–10 tool call iterations max** per worker invocation to prevent runaway loops and cost explosion.
6. **Prompt hot-reload**: All prompts loadable from YAML without backend restart. `PromptLoader` singleton with file-watch / explicit reload preserved.
7. **Evaluation-driven refactoring**: No refactor without measurable improvement. Every phase ships with golden test scenarios. Baseline measured before work begins.

---

## Plan structure

The plan is organized into **6 parallel lanes** and **4 sequential phases**.  
Within each phase, all listed lanes can execute **in parallel**.

```
Phase 0 — Foundation (contracts, types, API surface)          ← sequential, blocks all lanes
Phase 1 — Core work (Lanes A–E run in parallel)              ← bulk of implementation
Phase 2 — Integration & frontend UX (Lanes C + F in parallel)← needs Phase 1 APIs
Phase 3 — Cleanup, documentation, retire legacy              ← sequential wrap-up
```

### Lane index

| Lane | Scope | Primary area |
|---|---|---|
| **A** | Prompt & Orchestration | Backend — prompts, stage routing, graph factory |
| **B** | Azure Ground-Truth Tools | Backend — new tool integrations |
| **C** | Frontend UX | Frontend — chat, approval, stage visibility |
| **D** | Memory & Personalization | Backend + Frontend — checkpointer, architect profile |
| **E** | Retrieval & Research | Backend — search facade, evidence packets |
| **F** | Observability & Eval | Backend + Frontend — trace, quality gates |

---

# Phase 0 — Foundation

> **Goal**: Establish shared contracts, types, API surface, and evaluation baseline that all lanes depend on.  
> **Constraint**: Must complete before Lanes A–F begin implementation.

## 0.0 — Evaluation framework (baseline before changes)

**Goal**: Establish quality measurements so every subsequent phase can prove improvement.

### 0.0.1 Golden scenarios

Create 15+ scenarios mapped to user stories:

| Category | Count | Examples |
|---|---|---|
| US1 — Requirements extraction | 3 | Ambiguous RFP, multi-format docs, NFR-heavy spec |
| US2 — Candidate architecture | 3 | Simple web app, multi-region HA, microservices |
| US3 — ADR management | 2 | Create ADR, supersede ADR |
| US4 — WAF validation | 2 | Full validation run, incremental checklist update |
| US5a — IaC generation | 2 | Bicep for App Service, Terraform for AKS |
| US5b — Cost estimation | 2 | Basic web app TCO, multi-region cost comparison |
| US6 — Export | 1 | Full project export with traceability chain |
| US7 — Proactive iteration | 1 | Agent challenges bad design choices |

### 0.0.2 Scoring rubric

Per scenario, score 1–5 on:
- **Specificity**: not generic/boilerplate (cites project-specific details)
- **Tool usage**: called appropriate tools (MCP, KB, AAA)
- **Persistence**: state correctly updated via PendingChangeSet
- **Structure**: headings, tables, actionable items (not wall of text)
- **Challenge quality**: pushes back on bad choices with WAF citations
- **Citation grounding**: references Microsoft Learn URLs, WAF pillars
- **Completeness**: addresses the full request, doesn't leave gaps

### 0.0.3 Eval harness

Location: `backend/tests/eval/`

Capabilities:
- Replay test messages through full pipeline
- Capture agent outputs + tool calls + state changes
- Score automatically against rubric
- Generate comparison report (baseline vs current)

### 0.0.4 Baseline current system

Document for each scenario:
- Failure mode (generic, no tools, no persistence, etc.)
- Hallucination instances
- Missing structure
- Score per rubric dimension

**Files**: `backend/tests/eval/golden_scenarios/`, `backend/tests/eval/eval_runner.py`, `backend/tests/eval/reporting.py`

Status update: the Phase 0 foundation now uses `backend/tests/eval/eval_runner.py` plus committed golden scenario snapshots, while `backend/tests/eval/reporting.py` remains the single scoring/reporting layer.

**Tests**: Eval harness can load the committed baseline scenario set; the broader 15+ live replay matrix still belongs to later phases.

## 0.1 — Workflow stage result contract

**Files**: New `backend/app/agents_system/contracts/workflow_result.py`

Define the canonical output shape every stage worker must return:

```python
class WorkflowStageResult(BaseModel):
    stage: str                                    # Which stage produced this
    summary: str                                  # Human-readable summary
    pending_change_set: PendingChangeSet | None   # Changes requiring approval
    citations: list[Citation]                     # Sources consulted
    warnings: list[str]                           # Risks, gaps detected
    next_step: NextStepProposal                   # Structured next-step
    reasoning_summary: str                        # Collapsible reasoning for UI
    tool_calls: list[ToolCallTrace]               # Tool-call log for trace panel
    structured_payload: dict | None = None        # Machine-readable payload for typed UI interactions
```

The `structured_payload` field carries stage-specific typed data that the frontend renders without text parsing:
- `clarify` stage: `{"type": "clarification_questions", "questions": [{"id": ..., "text": ..., "pillar": ...}]}`
- `propose_candidate` with conflicts (FR-018): `{"type": "architect_choice", "options": [{"id": ..., "title": ..., "tradeoffs": ...}]}`
- Other stages: `None` (frontend uses `summary` text rendering)

```python
class NextStepProposal(BaseModel):
    stage: str                  # Recommended next stage
    tool: str | None            # Recommended tool if applicable
    rationale: str              # Why this is the next step
    blocking_questions: list[str]  # Questions that block progress
```

```python
class ToolCallTrace(BaseModel):
    tool_name: str
    args_preview: str           # First 200 chars of serialized args
    result_preview: str         # First 200 chars of result
    citations: list[str]        # URLs extracted from result
    duration_ms: int
```

**Tests**: Unit tests validating Pydantic serialization, edge cases (empty citations, null pending_change_set).

## 0.2 — Pending change set DB schema

**Files**: New Alembic migration, new `backend/app/agents_system/contracts/pending_change_set.py`

```python
class PendingChangeSet(BaseModel):
    id: str                          # UUID
    project_id: str                  # FK
    stage: str                       # Which stage produced this
    status: ChangeSetStatus          # pending | approved | rejected | superseded
    created_at: datetime
    source_message_id: str
    superseded_by: str | None
    bundle_summary: str              # Human-readable description
    proposed_patches: list[ArtifactPatch]  # Structured diffs
    waf_delta: dict | None
    mindmap_delta: dict | None

class ArtifactPatch(BaseModel):
    artifact_type: str               # requirement | assumption | adr | candidate | finding | ...
    operation: str                   # add | update | remove
    artifact_id: str | None          # For update/remove
    content: dict                    # Full artifact payload
    citations: list[Citation]

class ChangeSetStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
```

**DB tables** (two new tables, Alembic migration):

1. `pending_change_sets` (id, project_id, stage, status, created_at, source_message_id, superseded_by, rejection_reason, bundle_summary, waf_delta TEXT/JSON, mindmap_delta TEXT/JSON)
2. `artifact_drafts` (id, change_set_id FK, artifact_type, operation, artifact_id, content TEXT/JSON, citations TEXT/JSON)

**Migration note**: Both are new additive tables. No existing data is affected. Uses the same FK pattern as existing tables (`projects.id`, `ondelete='CASCADE'`). Must use SQLite-compatible column types (String, Text — store JSON as Text and parse in code, matching the `project_state_components` pattern). The `artifact_drafts` table has an FK to `pending_change_sets.id` with `ondelete='CASCADE'`. `rejection_reason` is nullable Text (populated only on reject).

**API endpoints** (new):
- `GET /api/projects/{projectId}/pending-changes` — list pending change sets
- `GET /api/projects/{projectId}/pending-changes/{changeSetId}` — detail with artifact drafts; includes diff computed against **current canonical state** at request time
- `POST /api/projects/{projectId}/pending-changes/{changeSetId}/approve` — approve and merge via `MergeService`
- `POST /api/projects/{projectId}/pending-changes/{changeSetId}/reject` — reject with reason (stored durably in `rejection_reason`)

> **v1 scope**: Approve and Reject only. Edit and Revise endpoints are **deferred to v2**.

### Merge service (deterministic)

Implement `MergeService.apply_change_set(project_id, change_set_id)` for deterministic merge into canonical state.

**Per-artifact merge rules**:
- **Requirements**: merge by artifact ID + lineage (update existing, append new)
- **Assumptions**: merge by ID, update content
- **Candidate architectures**: append versions (don't overwrite — keep history)
- **Diagrams**: versioned (keep history, update `previous_version_id`)
- **WAF checklist updates**: append evidence to checklist items
- **ADRs**: append, support supersession chain (`supersedes_adr_id`)
- **Cost estimates**: replace (latest wins)
- **IaC artifacts**: replace (latest wins)
- **Findings**: append (findings are additive)

### Conflict detection

When canonical state was modified by human between bundle creation and approval:
- Detect: compare `ProjectState.updated_at` with `PendingChangeSet.created_at`
- For artifact-level conflicts: compare per-artifact timestamps
- Surface conflicts in human-readable format (list conflicting artifacts)
- Require explicit resolution (no silent overwrite)

### Supersession chain

> **Deferred to v2.** Supersession (revise, `superseded_by` linkage) is out of v1 scope. The `superseded_by` column is retained in the schema for forward-compatibility but is not populated in v1.

**New files**:
- `backend/app/features/projects/application/pending_changes_merge_service.py`
- `backend/app/features/projects/application/conflict_detection_service.py`

**Tests**: CRUD lifecycle, approve merges via MergeService, reject records reason durably, conflict detection, per-artifact merge rules.

Status update: the current backend slice now persists pending change sets and artifact drafts in dedicated SQLite tables (`pending_change_sets`, `artifact_drafts`), keeps `reviewReason` responses stable while storing reject reasons durably, strips `pendingChangeSets` from new blob writes, and recomposes those rows back into `projectState` for existing v1 routes.

## 0.3 — SSE event contract extension

**Files**: Update `backend/app/agents_system/langgraph/adapter.py`, new TypeScript types in `frontend/src/features/agent/types/`

Extend the SSE event vocabulary beyond `reasoning` and `final`:

| Event | Payload | When |
|---|---|---|
| `stage` | `{ stage: string, confidence: number }` | After stage classification |
| `tool_call` | `{ tool: string, args_preview: string }` | When a tool is invoked |
| `tool_result` | `{ tool: string, result_preview: string, citations: string[] }` | When a tool returns |
| `text` | `{ delta: string }` | Incremental text token for progressive chat rendering |
| `pending_change` | `{ changeSetId: string, summary: string, patchCount: number }` | When a change set is created |
| `reasoning` | `{ step: string, content: string }` | Existing — reasoning steps |
| `final` | `{ answer: string, thread_id: string, projectState?: ... }` | Existing — final answer |

**Frontend TypeScript types**: `SSEStageEvent`, `SSEToolCallEvent`, `SSEToolResultEvent`, `SSETextEvent`, `SSEPendingChangeEvent`.

**Tests**: SSE event serialization round-trip, malformed event handling, incremental text event assembly.

## 0.4 — Stage classification contract

**Files**: Update `backend/app/agents_system/langgraph/nodes/stage_routing.py`

Add `StageClassification` result type:

```python
class StageClassification(BaseModel):
    stage: str
    confidence: float            # 0.0–1.0
    rationale: str               # Why this stage was chosen
    method: str                  # "rule" | "keyword" | "state" | "llm"
    alternative_stage: str | None  # Second-best guess if ambiguous
```

This is returned by `classify_next_stage` and stored in `GraphState["stage_classification"]` for logging, SSE, and eval.

**Tests**: Classification result serialization, confidence ranges.

---

# Phase 1 — Core work (parallel lanes)

## Lane A — Prompt & Orchestration

### A.1 — Split the monolith system prompt

**Problem**: [agent_prompts.yaml](backend/config/prompts/agent_prompts.yaml) is ~400 lines containing stage-specific instructions the graph already handles. The LLM wastes tokens on delegation reasoning it cannot act on.

**Changes**:

1. **Reduce `agent_prompts.yaml` to manual backup only** (~60–80 lines):
   - Retain as a read-only reference copy of the base persona for debugging/comparison
   - **Not used as automatic fallback** — if the modular prompt assembly fails, it should fail loudly (not silently fall back to a stale monolith)
   - Remove: sections 5 (Tools — moved to `tool_strategy.yaml`), 6 (Sub-Agent Delegation — deleted), 8 (Orchestration stages — deleted), 10 (Direct Answers — moved to `tool_strategy.yaml`)

2. **Promote existing per-stage YAMLs to authoritative**:
   - `orchestrator_routing.yaml` — expand from 12 lines to include stage-classification rules. **Used only in the classifier/orchestrator path** — not injected into every stage worker prompt
   - `tool_strategy.yaml` — absorb the tool-usage block (section 5) and direct-answer preference (section 10)
   - `clarification_planner.yaml`, `requirements_extraction.yaml`, `architecture_planner_prompt.yaml`, `cost_estimator_prompt.yaml`, `iac_generator_prompt.yaml`, `waf_validator.yaml`, `adr_writer.yaml`, `saas_advisor_prompt.yaml` — already exist, verify they are self-contained

3. **Delete from `agent_prompts.yaml`**:
   - "Your Role as Orchestrator" block
   - "When to Delegate to Sub-Agents" block (Architecture Planner, IaC Generator delegation)
   - "Stages (choose the next one explicitly)" block
   - "Delegation Decision Points" block
   - Duplicate tool listing (already in `tool_strategy.yaml`)
   - `clarification_prompt` and `conflict_resolution_prompt` templates (move to their own stage YAMLs or i18n-ready strings)

4. **Update `prompt_loader.py`**:
   - Assemble the final system prompt from: `base_persona.yaml` + `guardrails.yaml` + `tool_strategy.yaml` + stage-specific YAML (selected by `GraphState["next_stage"]`)
   - Enforce token budget per section (from `AAA_CONTEXT_MAX_BUDGET_TOKENS`)
   - Log assembled prompt hash for eval reproducibility

**Files touched**:
- `backend/config/prompts/agent_prompts.yaml` — reduce
- `backend/config/prompts/orchestrator_routing.yaml` — expand
- `backend/config/prompts/tool_strategy.yaml` — expand
- `backend/app/agents_system/config/prompt_loader.py` — update assembly logic

**Tests**:
- Assembled prompt for each stage stays under token budget
- No duplicate instruction blocks across YAML files
- Prompt hash stability test (same inputs → same hash)

---

### A.2 — Hybrid stage classifier

**Problem**: Keyword-based stage classification in [stage_routing.py](backend/app/agents_system/langgraph/nodes/stage_routing.py) is brittle — `"code"` routes to IaC, `"security"` routes to validate regardless of context. Missing keywords for `propose_candidate` (the primary user intent).

**Changes**:

1. **Expand keyword rules** — add missing intents:
   ```python
   # propose_candidate keywords (currently MISSING)
   (["architecture", "design", "candidate", "topology", "blueprint",
     "landing zone", "propose", "suggest architecture", "draw",
     "diagram", "c4", "container diagram", "system context"], ProjectStage.PROPOSE_CANDIDATE)
   ```

2. **Add negative-keyword guards** to prevent false positives:
   ```python
   # "code" alone → ambiguous; require IaC-specific context
   # "security" → only VALIDATE if no architecture keywords present
   # "infrastructure code" → IaC; "code review" → GENERAL
   ```

3. **Deferred follow-up** — keep the optional LLM fallback scoped for a later pass. Phase 0.4 now lands the smallest safe seam: richer rules, negative guards, and a typed `StageClassification` payload without adding another model hop to the runtime.
   - New function `_classify_with_llm(user_message, project_state_summary) -> StageClassification`
   - Uses a dedicated `stage_classifier_prompt.yaml` (~30 lines, structured output)
   - Returns `StageClassification` with confidence + rationale
   - Called only when keyword match is ambiguous (adds ~200ms, ~100 tokens)
   - Bounded: 1 LLM call max, no tool use

4. **Emit `StageClassification` into GraphState** for SSE and eval.

**New files**:
- `backend/config/prompts/stage_classifier_prompt.yaml`

**Files touched**:
- `backend/app/agents_system/langgraph/nodes/stage_routing.py` — refactor `classify_next_stage`
- `backend/app/agents_system/langgraph/state.py` — add `stage_classification` to `GraphState`
- `backend/app/agents_system/langgraph/adapter.py` — emit `stage` SSE event after classification

**Tests**:
- Keyword classification: "design the architecture" → `propose_candidate`
- Keyword classification: "validate WAF compliance" → `validate`
- Keyword classification: "code review the ADR" → `general` (not IaC)
- Ambiguous message triggers LLM fallback
- LLM fallback returns valid `StageClassification`
- SSE `stage` event emitted with correct payload

---

### A.3 — Stage-contextual prompt injection

**Problem**: `orchestrator_routing.yaml` is 12 lines; the LLM inside each stage still receives the full generic prompt.

**Changes**:

1. **Update `prompt_loader.py`** to compose the system prompt as:
   ```
   base_persona.yaml (role, WAF, behavior, guardrails)
   + tool_strategy.yaml (tool usage rules)
   + <stage-specific>.yaml (e.g., architecture_planner_prompt.yaml for propose_candidate)
   ```
   
   > **Note**: `orchestrator_routing.yaml` is injected **only** for the classifier/orchestrator step, not for every stage worker. Stage workers receive only the base persona + tool strategy + their own stage YAML.

2. **Each stage YAML becomes self-contained**: it carries all the instructions the LLM needs for that stage, including examples, output format, and tool-usage guidance specific to the stage.

3. **Reduce monolith coupling without wholesale rewrite**: keep `agent_prompts.yaml` as an orchestrator fallback, add an explicit file-only `load_prompt_file(...)` path for stage workers, and keep modular composition from silently pulling stage sections out of the monolith.

**Files touched**:
- `backend/app/agents_system/config/prompt_loader.py`
- All `backend/config/prompts/*.yaml` files — audit for self-containment

**Tests**:
- Each stage assembles a valid prompt under token budget
- No section text appears in more than one YAML (dedup lint)

---

### A.4 — Prompt hygiene CI

**Problem**: 16 YAML prompts with overlapping sections, manual version numbers, no automated validation.

**Changes**:

1. **New script `scripts/lint_prompts.py`**:
   - Parse all `backend/config/prompts/*.yaml`
   - Check: `version` and `last_updated` present in every file
   - Check: no text block appears in more than one file (dedup detection via sentence hashing)
   - Check: all `${placeholder}` variables have documented values
   - Check: assembled prompt for each stage is under configured token budget
   - Check: no `clarification_prompt` / `conflict_resolution_prompt` templates remain outside their stage YAML

2. **Add to CI pipeline** (GitHub Actions or local pre-commit).

3. **Move user-facing phrasing** (`clarification_prompt`, `conflict_resolution_prompt`) to a dedicated `backend/config/prompts/templates/` folder with i18n-ready naming.

**New files**:
- `scripts/lint_prompts.py`
- `backend/config/prompts/templates/clarification.yaml`
- `backend/config/prompts/templates/conflict_resolution.yaml`

**Tests**:
- `lint_prompts.py` passes on current YAML state (after cleanup)
- Introducing a duplicate block causes lint failure

---

### A.5 — Typed tool persistence (eliminate AAA_STATE_UPDATE regex)

**Problem**: AAA tools return `AAA_STATE_UPDATE` text blocks that `postprocess.py` extracts via regex and `state_update_parser.py` merges heuristically. This is fragile, untyped, and produces silent data corruption.

**Status update**: landed as a focused compatibility slice. `backend/app/agents_system/tools/tool_registry.py` is now the canonical registry for pending-change tools, `tool_wrappers.py` upgrades registered legacy tool outputs into typed `pending_change_confirmation` payloads, and those payloads are persisted through the DB-backed pending-change service before the graph reaches `postprocess.py`. The legacy parser remains only as a fallback for non-migrated paths; canonical tool observations are now authoritative.

**Changes**:

1. **Replace tool persistence model**:
   - Registered AAA tools now persist through `pending_change_sets` + `artifact_drafts` via the pending-change service
   - Tool wrappers return structured confirmations (`pending_change_confirmation`) with the typed `pendingChangeSet`
   - `postprocess.py` prefers canonical tool observations and bypasses legacy text extraction when that typed path is available

2. **Introduce canonical tool registry** (`backend/app/agents_system/tools/tool_registry.py`):
   - Central registry maps stage → allowed pending-change tools
   - Registry normalizes typed confirmation payloads and centralizes pending-change artifact drafting
   - `tool_wrappers.py` remains as the compatibility seam until every AAA tool returns canonical payloads natively

3. **Remove dead parsing code**:
   - Canonical tool observations now bypass `AAA_STATE_UPDATE` extraction in `nodes/postprocess.py`
   - `state_update_parser.py` remains as a narrow legacy fallback until the remaining text-only paths are migrated
   - Remove ReAct template YAML sections (code uses `llm.bind_tools()` native function calling)

**New files**:
- `backend/app/agents_system/tools/tool_registry.py` — canonical tool registration surface

**Files to delete** (after all tools migrated):
- `backend/app/agents_system/tools/tool_wrappers.py`
- Any remaining `state_update_parser.py` or `AAA_STATE_UPDATE` handlers

**Files touched**:
- All `backend/app/features/agent/infrastructure/tools/aaa_*.py` — add Pydantic input schemas, write to PCS
- `backend/app/agents_system/langgraph/nodes/postprocess.py` — remove regex
- `backend/config/prompts/agent_prompts.yaml` — remove ReAct template sections

**Tests**:
- Tools return structured JSON, not text blocks
- PendingChangeSet + ArtifactDrafts created by tool calls
- No regex patterns in postprocess.py
- Tool input validation with invalid Pydantic data

---

## Lane B — Azure Ground-Truth Tools

### B.1 — Azure Retail Prices tool

**Problem**: `aaa_record_cost_estimate` stores whatever the LLM invents. The cost estimator prompt references the Retail Prices API but there is no actual tool that calls it.

**Status update (v1 landed)**: `backend/app/features/agent/infrastructure/tools/azure_retail_prices_tool.py` now provides the standalone public/no-auth lookup surface with pagination metadata + cache, `tool_registry.py` stage-scopes it through the canonical runtime registry, and `aaa_cost_tool.py` calls that tool path before persisting reviewable `costEstimates`. B.2/B.3/B.6 remain out of v1 scope.

**Changes**:

1. **New tool `azure_retail_prices_tool.py`** in `backend/app/features/agent/infrastructure/tools/`:
   - Calls `https://prices.azure.com/api/retail/prices` (public, no auth required)
   - Accepts: `service_name`, `region`, `sku_name`, `currency_code` (default USD)
   - Returns: structured pricing items (retail price, unit of measure, meter name, reservation options)
   - Pagination handling for multi-page results
   - Response caching (in-memory TTL 1 hour) to avoid repeated API calls

2. **Register via canonical tool registry** (new `backend/app/agents_system/tools/tool_registry.py` — see A.5) and expose to the cost_estimator stage worker.

3. **Update `cost_estimator_prompt.yaml`** to instruct the LLM to use the tool for real pricing instead of estimating from memory.

**Auth model**: No auth needed — Azure Retail Prices API is public. This satisfies both MCP-dev and direct-SDK-production paths since it's the same unauthenticated REST endpoint.

**New files**:
- `backend/app/features/agent/infrastructure/tools/azure_retail_prices_tool.py`

**Files touched**:
- `backend/app/agents_system/tools/tool_registry.py` — register new tool (see A.5)
- `backend/config/prompts/cost_estimator_prompt.yaml` — update tool usage instructions

**Tests**:
- Tool returns structured prices for known SKU (mocked API)
- Pagination handling for >100 items
- Cache hit on repeat query
- Error handling for invalid service name / region

---

### B.2 — Azure Resource Graph & Advisor tools

> **Deferred to v2.** Requires authenticated Azure connectivity (subscription credentials), which is out of v1 scope. The MCP path (`mcp_azure_mcp_advisor`, `azure_resources-query_azure_resource_graph`) remains available for development/demo use but is not integrated into the production graph in v1.

---

### B.3 — Azure Quota tool

> **Deferred to v2.** Requires authenticated Azure connectivity. Same rationale as B.2.

---

### B.4 — IaC syntax + schema validation

**Status update (minimal slice landed)**: a focused validator surface now exists in `backend/app/features/agent/infrastructure/tools/aaa_iac_validation_tool.py`. It validates ARM template shape (`$schema`, `contentVersion`, `resources`), parses JSON/YAML outputs, and performs lightweight delimiter/declaration checks for Bicep and Terraform without introducing CLI/runtime coupling.

**Problem**: IaC generator prompt claims "validated" but `aaa_iac_tool.py` only persists the LLM output. No actual syntax/schema validation.

**Changes**:

1. **Bicep validation tool** (`bicep_validate_tool.py`):
   - Write generated Bicep to a temp file
   - Run `az bicep build --file <temp.bicep> --stdout` (requires `az` CLI on backend host)
   - Parse output: success or error with line numbers + messages
   - Return structured `BicepValidationResult`
   - Graceful fallback if `az` CLI not available: skip validation, warn user

2. **Terraform validation tool** (`terraform_validate_tool.py`):
   - Write generated Terraform to a temp directory
   - Run `terraform init -backend=false` + `terraform validate`
   - Parse output: success or diagnostics with severity + message
   - Return structured `TerraformValidationResult`
   - Graceful fallback if `terraform` CLI not available

3. **Schema validation** (no CLI dependency):
   - Validate Bicep JSON output against Azure resource provider schemas (downloaded from `azure-rest-api-specs` or cached)
   - Validate Terraform HCL structure via `hcl2json` library
   - This runs even when CLI tools are unavailable

4. **Integration into IaC stage worker**:
   - After LLM generates IaC code → validate → if errors: feed errors back to LLM for self-correction (1 retry) → persist validated output
   - Validation results included in `WorkflowStageResult.warnings`

**New files**:
- `backend/app/features/agent/infrastructure/tools/bicep_validate_tool.py`
- `backend/app/features/agent/infrastructure/tools/terraform_validate_tool.py`
- `backend/app/features/agent/infrastructure/tools/schema_validate_tool.py`

**Dependencies**: `hcl2json` (Python package, add to `pyproject.toml`)

**Tests**:
- Valid Bicep passes validation
- Invalid Bicep returns errors with line numbers
- Valid Terraform passes validation
- Invalid Terraform returns diagnostics
- Fallback when CLI not available
- Self-correction retry on first failure

---

### B.5 — Mermaid validator

**Status update (minimal slice landed)**: `backend/app/features/agent/infrastructure/tools/aaa_mermaid_validation_tool.py` now exposes the existing server-side Mermaid syntax validator as a dedicated tool with line-aware diagnostics, and the canonical runtime tool registry stage-scopes it to general/candidate/validate turns.

**Problem**: Invalid Mermaid diagrams fail silently in the UI. Architecture proposals with broken diagrams degrade the architect experience.

**Changes**:

1. **New tool `mermaid_validate_tool.py`**:
   - Parse Mermaid syntax server-side using `mermaid-py` or subprocess call to `mmdc` (Mermaid CLI)
   - Return: valid/invalid + error messages with line numbers
   - Graceful fallback: regex-based basic syntax check if `mmdc` not available (bracket matching, keyword validation)

2. **Integration**:
   - After architecture_planner generates Mermaid → validate → if invalid: feed errors back for self-correction (1 retry)
   - Surface validation status in the `WorkflowStageResult`

**New files**:
- `backend/app/features/agent/infrastructure/tools/mermaid_validate_tool.py`

**Tests**:
- Valid Mermaid passes
- Invalid Mermaid returns error with position
- Self-correction retry

---

### B.6 — Region availability lookup

> **Deferred to v2.** Requires authenticated Azure connectivity (resource provider API). Same rationale as B.2.

---

## Lane C — Frontend UX

> **Dependency**: Phase 0 contracts (SSE events, pending change set API, `WorkflowStageResult` shape) must be defined. Implementation can use mocked/stubbed data initially.

### C.1 — SSE streaming chat

**Problem**: `useChatMessaging.ts` uses `fetch` + `await response.json()` — no streaming. The user sees a spinner until the full response arrives.

**Changes**:

1. **New hook `useSSEChat.ts`**:
   - Use `fetch` with `ReadableStream` to consume SSE events from `/api/agent/projects/{projectId}/chat/stream` (not `EventSource` — requires POST body and custom headers)
   - Parse events: `stage`, `tool_call`, `tool_result`, `text`, `reasoning`, `pending_change`, `final`
   - Update state incrementally: show stage badge, show tool calls as they happen, stream `text` deltas token-by-token for progressive rendering

2. **Update `agentService.ts`**:
   - Add `projectChatStream(projectId, message): ReadableStream` method
   - Keep `projectChat()` as fallback for non-streaming mode

3. **Update `useChatMessaging.ts`**:
   - Default to SSE streaming; fall back to non-streaming on error
   - Progressive message assembly: user sees partial response during streaming

4. **Backend streaming endpoint**: Verify `execute_project_chat_stream` in `adapter.py` emits the new event types from Phase 0.3.

**New files**:
- `frontend/src/features/agent/components/hooks/useSSEChat.ts`

**Files touched**:
- `frontend/src/features/agent/api/agentService.ts`
- `frontend/src/features/agent/components/hooks/useChatMessaging.ts`

**Tests**:
- SSE events parsed correctly
- Fallback to non-streaming on connection error
- Progressive message rendering

---

### C.2 — Stage badge + progress rail

**Problem**: The architect has no visibility into which stage the assistant is working on. No progress indicator beyond a generic spinner.

**Changes**:

1. **New component `StageBadge.tsx`**:
   - Display current stage name (human-readable label)
   - Color-coded by stage category (input=blue, design=purple, validation=green, delivery=orange)
   - Animate on stage transition

2. **New component `StageProgressRail.tsx`**:
   - Horizontal rail showing all stages: `Requirements → Clarify → Architecture → ADR → Validate → Cost → IaC → Export`
   - Current stage highlighted, completed stages checked, future stages dimmed
   - Clickable for stage details (shows last result summary)

3. **Integration**:
   - Render `StageBadge` in chat panel header (next to "Chatbot / Assistant" label)
   - Render `StageProgressRail` below the header in the unified project workspace
   - Populate from SSE `stage` event during streaming, from `WorkflowStageResult.stage` after completion

**New files**:
- `frontend/src/features/projects/components/unified/StageBadge.tsx`
- `frontend/src/features/projects/components/unified/StageProgressRail.tsx`

**Tests**:
- Stage transitions animate correctly
- Completed stages show checkmark
- Clicking stage shows summary tooltip

---

### C.3 — Pending change set UI (Approve / Reject / Edit)

**Problem**: The backend implements review-first (approval before state mutation), but the architect sees only plain text. No visible affordance to approve, reject, or diff pending changes.

**Changes**:

1. **New component `PendingChangeCard.tsx`**:
   - Renders a pending change set as a diff-style card
   - Shows: change set summary, stage origin, list of artifact patches
   - For each patch: show operation (add/update/remove), artifact type, diff view (computed against **current canonical state** at review time — no snapshots)
   - Actions: **Approve**, **Reject** (with reason text input — stored durably)

   > **v1 scope**: Approve and Reject only. Edit (inline editing) is deferred to v2.

2. **New component `PendingChangeDrawer.tsx`**:
   - Slide-in drawer that lists all pending change sets for the current project
   - Badge count on trigger button
   - Grouped by stage

3. **API integration**:
   - `GET /api/projects/{projectId}/pending-changes` → list
   - `POST /api/projects/{projectId}/pending-changes/{id}/approve` → approve
   - `POST /api/projects/{projectId}/pending-changes/{id}/reject` → reject with reason

4. **Auto-open**: When SSE `pending_change` event received, auto-open the drawer or show a toast notification with "Review changes" action.

5. **Chat integration**: After approval, insert a system message in chat: "✅ Changes approved: {summary}" with a link to the updated artifacts.

**New files**:
- `frontend/src/features/projects/components/unified/PendingChangeCard.tsx`
- `frontend/src/features/projects/components/unified/PendingChangeDrawer.tsx`
- `frontend/src/features/projects/api/pendingChangesService.ts`

**Tests**:
- Approve flow: card disappears, ProjectState updates
- Reject flow: card shows rejected status, reason persisted
- Auto-open on SSE event
- Empty state when no pending changes

---

### C.4 — Structured clarification form

**Problem**: Clarify planner produces grouped WAF-pillar questions, but the chat renders them as a wall of bullet-point markdown. No structured answer form.

**Changes**:

1. **New component `ClarificationForm.tsx`**:
   - Render from `WorkflowStageResult.structured_payload` (type `clarification_questions`)
   - Render questions grouped by WAF pillar / theme
   - Per-question: text area for answer, "Skip with assumption" button (generates a default assumption)
   - Submit: sends all answers as a single message that maps to the clarification_resolution worker

2. **Detection**: When `WorkflowStageResult.structured_payload.type === "clarification_questions"`, render `ClarificationForm` instead of plain text. **No text-pattern parsing** — uses the typed contract exclusively.

3. **Backend support**: Ensure the clarify stage worker populates `WorkflowStageResult.structured_payload` with the question array. The `summary` field contains a human-readable fallback.

**New files**:
- `frontend/src/features/projects/components/unified/ClarificationForm.tsx`

**Files touched**:
- `backend/app/agents_system/langgraph/nodes/clarify.py` — ensure structured question output

**Tests**:
- Questions grouped by pillar
- Skip generates assumption text
- Submit sends correctly formatted message
- Fallback to plain text if parsing fails

---

### C.5 — Architect-choice picker

**Problem**: FR-018 mandates presenting options when sources conflict, but there is no structured UI component for option selection.

**Changes**:

1. **New component `ArchitectChoicePicker.tsx`**:
   - Render from `WorkflowStageResult.structured_payload` (type `architect_choice`)
   - Display options as radio-card list with summary + trade-offs per option
   - Selection sends the choice as the next user turn: "I choose Option {N}: {title}"

2. **Detection**: When `WorkflowStageResult.structured_payload.type === "architect_choice"`, render the picker. **No text-pattern parsing** (`Architect choice required:` is not used) — uses the typed contract exclusively.

3. **Backend support**: When sources conflict (FR-018), the stage worker populates `structured_payload` with `{"type": "architect_choice", "options": [...]}`. The `summary` field contains a human-readable fallback for non-interactive contexts.

**New files**:
- `frontend/src/features/projects/components/unified/ArchitectChoicePicker.tsx`

**Tests**:
- Typed payload renders picker correctly
- Selection sends correct message
- Fallback to summary text if `structured_payload` is `None`

---

### C.6 — Live tool trace panel

**Problem**: Tool calls are invisible during the turn. Reasoning steps are shown post-hoc, truncated to 100 chars.

**Changes**:

1. **New component `ToolTraceTimeline.tsx`**:
   - Collapsible timeline below the assistant message (or in a side panel)
   - Shows each tool call: tool name, args preview, result preview, citations, duration
   - Populated from SSE `tool_call` and `tool_result` events during streaming
   - Post-hoc: populated from `WorkflowStageResult.tool_calls`

2. **Replace existing reasoning steps toggle** with this richer trace panel.

**New files**:
- `frontend/src/features/projects/components/unified/ToolTraceTimeline.tsx`

**Tests**:
- Timeline updates during streaming
- Collapsed by default, expandable
- Citations shown as links

---

### C.7 — Citations panel

**Problem**: Citations are scattered throughout responses. No deduplicated, grouped view.

**Changes**:

1. **New component `CitationsPanel.tsx`**:
   - Aggregate all Microsoft Learn URLs from the current turn
   - Deduplicate and group by domain (learn.microsoft.com, techcommunity, etc.)
   - Show as a collapsible sidebar section or bottom panel
   - Clickable links open in new tab

2. **Integration**: Populate from `WorkflowStageResult.citations` and extracted URLs in the assistant message.

**New files**:
- `frontend/src/features/projects/components/unified/CitationsPanel.tsx`

**Tests**:
- Deduplication works
- Links grouped correctly
- Empty state when no citations

Status update: the unified project workspace right panel now ships a single focused `ChatReviewPanel` that consumes the typed stream / `workflowResult` contract end-to-end for the smallest safe slice: stage rail visibility, grouped clarification answers, pending-change review against the canonical `/pending-changes` API, and collapsible tool-trace / citation visibility all reuse the existing workspace shell without introducing a second chat surface.

---

### C.8 — Diagram preview with validation

**Problem**: Mermaid diagrams are rendered as code blocks. No inline preview. Invalid diagrams fail silently.

**Changes**:

1. **Mermaid renderer in chat**: When assistant message contains ` ```mermaid ` code blocks, render them inline using `mermaid` JS library.
2. **Validation indicator**: If backend validation (B.5) flagged errors, show a warning badge on the diagram.
3. **Export options**: "Copy as PNG", "Copy as SVG", "Open in editor" buttons on each diagram.

**New files**:
- `frontend/src/features/projects/components/unified/MermaidPreview.tsx`

**Dependencies**: `mermaid` npm package (add to `frontend/package.json`)

**Tests**:
- Valid Mermaid renders correctly
- Invalid Mermaid shows error message
- Export buttons produce valid output

---

### C.9 — Retire legacy AgentChatWorkspace

**Problem**: Two chat surfaces exist — `AgentChatWorkspace.tsx` (legacy 2-pane) and the unified workspace. Maintenance cost, UX inconsistency.

**Changes**:

1. **Verify parity**: Ensure the unified workspace's `RightChatPanel` + `CenterChatArea` covers all features of `AgentChatWorkspace`:
   - Project selector ✓ (header)
   - Chat panel ✓ (right sidebar)
   - Project state panel ✓ (left sidebar)
   - Reasoning toggle → replaced by `ToolTraceTimeline` (C.6)
   - Clear chat → header action

2. **Remove `AgentChatWorkspace.tsx`** and its child components:
   - `frontend/src/features/agent/components/AgentChatWorkspace.tsx`
   - `frontend/src/features/agent/components/AgentChatPanel.tsx`
   - `frontend/src/features/agent/components/WorkspaceHeader.tsx`
   - `frontend/src/features/agent/components/ProjectSelector.tsx`
   - `frontend/src/features/agent/components/ProjectStatePanel.tsx`
   - `frontend/src/features/agent/components/ProjectState/` folder
   - Associated hooks in `frontend/src/features/agent/components/hooks/` that are not shared with the unified workspace

3. **Update routes**: Remove any route pointing to the legacy workspace. Redirect to unified workspace.

**Tests**:
- No broken imports after removal
- Routes redirect correctly
- Unified workspace covers all legacy features

---

## Lane D — Memory & Personalization

### D.1 — SQLite-backed persistent checkpointer

**Problem**: `MemorySaver` is in-memory only. Thread memory is lost on backend restart.

**Changes**:

1. **Replace `MemorySaver` with `SqliteSaver`** from `langgraph-checkpoint-sqlite`:
   - Configure DB path: `data/checkpoints.db`
   - Connection pooling: match existing SQLite settings

2. **Update `graph_factory.py`**:
   ```python
   from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

   checkpointer = AsyncSqliteSaver.from_conn_string("data/checkpoints.db") if settings.aaa_thread_memory_enabled else None
   ```

3. **Migration**: No data migration needed (in-memory state has no persistence). The `data/checkpoints.db` file is a separate SQLite database managed by langgraph's checkpoint library — it does not touch the main projects database.

4. **Enable existing disabled feature flags**:
   - Set `aaa_thread_memory_enabled=True` (currently `False` — enables LangGraph checkpointer)
   - Set `aaa_context_compaction_enabled=True` (currently `False` — enables context compaction for long conversations)
   - Verify both work correctly with the SQLite checkpointer before enabling by default

**Dependencies**: `langgraph-checkpoint-sqlite` (add to `pyproject.toml`)

**Files touched**:
- `backend/app/agents_system/langgraph/graph_factory.py`

**Tests**:
- Thread memory survives backend restart
- Checkpoint DB created on first run
- Graph compiles with SQLite checkpointer

---

### D.2 — Architect profile

**Problem**: No personalization. Every session starts from scratch — no preferred region, compliance posture, IaC flavor, or cost ceiling.

**Changes**:

1. **New model `ArchitectProfile`**:
   ```python
   class ArchitectProfile(BaseModel):
       default_region_primary: str = "eastus"
       default_region_secondary: str | None = None
       default_iac_flavor: str = "bicep"          # "bicep" | "terraform"
       compliance_baseline: list[str] = []         # ["GDPR", "SOC2", ...]
       monthly_cost_ceiling: float | None = None   # USD
       preferred_vm_series: list[str] = []         # ["D", "E", "F"]
       team_devops_maturity: str = "basic"         # "none" | "basic" | "advanced"
       notes: str = ""                             # Free-form notes
   ```

2. **Storage**: SQLite table `architect_profiles` (id, profile JSON, updated_at). One profile per installation (single-user tool — no `user_id` column).

   **Implementation note**: Added as a new SQLAlchemy-backed table in the existing projects database. No FK to `projects` — installation-level. No existing data affected. Strictly single-user in v1 — no multi-user schema hints.

3. **API endpoints**:
   - `GET /api/settings/architect-profile` — read current profile
   - `PUT /api/settings/architect-profile` — update profile

4. **Frontend**: Settings page section for editing the architect profile (form with the fields above).

   **Implementation note (2026-04-17)**: Delivered via `GET/PUT /api/settings/architect-profile`, persisted `architect_profiles` rows in the projects SQLite database, and the `ArchitectProfileForm` modal launched from `NavigationSettingsControls`.

**New files**:
- `backend/app/features/settings/domain/architect_profile.py`
- `backend/app/features/settings/application/architect_profile_service.py`
- `backend/app/features/settings/contracts/architect_profile.py`
- `frontend/src/features/settings/components/ArchitectProfileForm.tsx`

**Tests**:
- Profile CRUD (create, read, update)
- Default values when no profile exists

---

### D.3 — Per-project long-term notes

**Problem**: No way for the architect to pin decisions, rationale, rejected candidates, or key questions that persist across chat sessions.

**Changes**:

1. **New `project_notes` table**: id, project_id, category (decision | context | question | risk), content, source_message_id (optional — for "pin from chat" traceability), created_at, updated_at.

   **Implementation note**: Added as a new SQLAlchemy-backed table in the existing projects database. FK to `projects.id` with `ondelete='CASCADE'`. No existing data affected.

2. **API endpoints**:
   - `GET /api/projects/{projectId}/notes` — list notes
   - `POST /api/projects/{projectId}/notes` — create note
   - `PUT /api/projects/{projectId}/notes/{noteId}` — update
   - `DELETE /api/projects/{projectId}/notes/{noteId}` — delete

3. **Frontend**: Notes tab in the left sidebar of the unified workspace.

   **Implementation note (2026-04-17)**: Delivered via normalized `project_notes` persistence, CRUD endpoints under `/api/projects/{projectId}/notes`, and the `ProjectNotesPanel` workspace tab.

**New files**:
- `backend/app/features/projects/application/project_notes_service.py`
- `backend/app/features/projects/contracts/project_notes.py`
- `backend/app/features/projects/api/project_notes_router.py`
- `frontend/src/features/projects/components/unified/ProjectNotesPanel.tsx`

**Tests**:
- Notes CRUD lifecycle

---

## Lane E — Retrieval & Research

### E.1 — Unified research facade

**Problem**: `kb_tool`, `rag_tool`, `project_document_tool`, `mcp_tool` overlap. System prompt says "MCP-First" but also "kb_search FIRST". Agents pick inconsistently.

**Status update (minimal v1 slice landed)**: `backend/app/agents_system/tools/research_tool.py` now provides the internal unified facade used by the research worker, combining project-document recall, KB retrieval, and Microsoft Learn lookups into one grounded evidence result shape. Legacy low-level tools remain in place; broader agent-facing retrieval redesign stays out of this v1 slice.

**Changes**:

1. **New `research_tool.py`** — single tool that the LLM calls for any research need:
   - Input: `query: str`, `scope: "project" | "kb" | "microsoft_docs" | "all"` (default: `"all"`)
   - Execution pipeline:
     1. `project_document_search` (if scope includes project) — highest priority for project-specific context
     2. `kb_search` (if scope includes kb) — curated Azure KB
     3. `microsoft_docs_search` via MCP (if scope includes microsoft_docs) — Microsoft Learn
     4. `microsoft_docs_fetch` via MCP — only for high-scoring results from step 3
   - Re-rank results across all sources by relevance to query
   - Return unified `EvidencePacket` shape:
     ```python
     class EvidencePacket(BaseModel):
         id: str
         source: str              # "project_document" | "kb" | "microsoft_docs"
         title: str
         excerpt: str
         url: str | None
         relevance_score: float   # 0.0–1.0
         source_document: str | None  # For project documents
     ```

2. **Deprecate individual tool exposure to the LLM**: The LLM sees only `research` as a tool. Internal routing is deterministic.

3. **Update `tool_strategy.yaml`**: Replace per-tool instructions with single `research` tool guidance.

**New files**:
- `backend/app/features/agent/infrastructure/tools/research_tool.py`

**Files touched**:
- `backend/app/agents_system/tools/tool_registry.py` — replace kb_tool/rag_tool/mcp_tool exposure with research_tool
- `backend/config/prompts/tool_strategy.yaml` — update

**Tests**:
- Research with scope="all" hits all sources
- Research with scope="project" hits only project documents
- Re-ranking orders by relevance
- EvidencePacket serialization

---

### E.2 — Evidence packet traceability

**Problem**: Architecture planner prompt references "evidence packets" but there is no structured contract or traceability from requirement → research → architectural decision.

**Status update (minimal v1 slice landed)**: the research worker now emits a stable packet shape with `evidence`, `consultedSources`, and `groundingStatus`, and the architecture synthesizer/runtime prompt builders render those grounded excerpts directly. Reference validation in planner output remains a later hardening step.

**Changes**:

1. **Add `evidence_packets` field to `GraphState`**: List of `EvidencePacket` produced during research.

2. **Require architecture_planner to reference packet IDs** in its output (already in prompt, but not enforced or validated).

3. **Validate**: Post-process architecture planner output to verify all referenced packet IDs exist.

4. **Surface in UI**: Evidence packets appear in the `ToolTraceTimeline` and in the pending change set detail.

**Files touched**:
- `backend/app/agents_system/langgraph/state.py` — add `evidence_packets` to GraphState
- `backend/app/agents_system/langgraph/nodes/research.py` — produce EvidencePackets
- `backend/app/agents_system/langgraph/nodes/architecture_planner.py` — validate references

**Tests**:
- Evidence packets stored in GraphState after research
- Architecture planner output references valid packet IDs
- Invalid reference raises warning in WorkflowStageResult

---

## Lane F — Observability & Eval

### F.1 — In-app trace tab

**Problem**: No in-app visibility into stage → evidence → tool calls → pending change → approval → state delta for a given turn.

**Changes**:

1. **New workspace tab `TraceTab`**:
   - Renders a timeline for the selected message
   - Sections: Stage Classification → Research (evidence packets) → Tool Calls → Pending Changes → State Updates
   - Data source: **Existing `project_trace_events` table** — already stores per-thread execution trace events

2. **Backend**: Store `WorkflowStageResult` as a `project_trace_events` row with `event_type='workflow_stage_result'` and the full result as JSON in the `payload` column. **No new table or column needed** — reuses the existing trace infrastructure from migration `20260329_0001`.

3. **API endpoint**: `GET /api/projects/{projectId}/messages/{messageId}/trace` — queries `project_trace_events` filtered by **message_id** (message-scoped, not thread-scoped) and returns the `WorkflowStageResult` payloads.

4. **Register in workspace manifest**: New tab `"trace"` in the center tab catalog.

**New files**:
- `frontend/src/features/projects/components/unified/TraceTab.tsx`
- `backend/app/features/agent/api/trace_router.py` (thin router querying existing `project_trace_events` table)

**Migration note**: No DB migration needed — reuses existing `project_trace_events` table. Only adds a new `event_type` value (`'workflow_stage_result'`).

**Tests**:
- Trace tab renders timeline
- Empty state for messages without trace data
- Tab registered in workspace manifest
- WorkflowStageResult round-trips through project_trace_events storage

---

### F.2 — Quality gate report

**Problem**: No project-level view of coverage: WAF %, mindmap %, unanswered clarifications, missing artifacts.

**Changes**:

1. **New workspace tab `QualityGateTab`**:
   - Sections:
     - WAF Coverage: per-pillar progress bar (covered / partial / not covered)
     - Mindmap Coverage: per-topic coverage (from existing mindmap service)
     - Open Clarifications: count + list of unanswered questions
     - Missing Artifacts: stages not yet executed (no cost estimate, no IaC, etc.)
   - Data source: Existing ProjectState fields, computed server-side

   > **v1**: No age-based "stale ADR" detection. ADR staleness is deferred until real usage data clarifies what "stale" means.

2. **Backend**: New service `quality_gate_service.py` that computes the quality gate report from ProjectState.

3. **API endpoint**: `GET /api/projects/{projectId}/quality-gate` — returns the report.

4. **Register in workspace manifest**: New tab `"quality-gate"` in the center tab catalog.

**New files**:
- `frontend/src/features/projects/components/unified/QualityGateTab.tsx`
- `backend/app/features/projects/application/quality_gate_service.py`
- `backend/app/features/projects/api/quality_gate_router.py`

**Tests**:
- Quality gate computes correct percentages
- Tab renders all sections

Status update: the quality-gate slice now ships as a focused `/api/projects/{projectId}/quality-gate` backend report plus a manifest-registered `quality-gate` workspace tab, reusing composed `ProjectState` data and persisted trace events for weighted WAF coverage, 13-topic mindmap coverage, unanswered clarifications, missing deliverables, and recent workflow activity without introducing new storage.

---

# Phase 2 — Integration

> **Goal**: Wire all lane outputs together. Verify end-to-end flows.

## 2.1 — End-to-end flow validation

For each stage, verify the complete cycle works:

| Stage | Input | Expected flow |
|---|---|---|
| `extract_requirements` | Upload RFP document | Document parsed → requirements extracted → pending change set → approve → ProjectState updated |
| `clarify` | "We need high availability" | Clarification form rendered (from `structured_payload`) → answers submitted → **pending change set** → approve → requirements updated |
| `propose_candidate` | "Design the architecture" | Stage badge shows "Architecture" → research → architecture planner → Mermaid preview → pending change set → approve |
| `manage_adr` | "Create ADR for database choice" | ADR drafted → pending change set → approve → ADR persisted |
| `validate` | "Validate WAF compliance" | WAF evaluator runs → findings surfaced → pending change set → approve → findings persisted |
| `pricing` | "Estimate costs" | Retail Prices API called → cost breakdown → **pending change set** → approve → pricing lines persisted |
| `iac` | "Generate Bicep" | IaC generated → validated (syntax + schema) → pending change set → approve → IaC artifacts persisted |
| `export` | "Export the project" | Export package generated with traceability + mindmap scorecard |

Each flow must be covered by at least one E2E test (Playwright for frontend, pytest for backend).

> **Note**: The full 15-scenario acceptance matrix and automated guardrails are defined in the *Appendix: Acceptance scenarios & guardrails*. Phase 2.1 tests must cover all 15 scenarios. Automated guardrails must be enforced as assertions in the eval harness (Phase 0.0).

## 2.2 — SSE event pipeline validation

- Verify all SSE event types (`stage`, `tool_call`, `tool_result`, `text`, `pending_change`, `reasoning`, `final`) emitted correctly
- Verify frontend consumes and renders each event type
- Verify fallback to non-streaming mode works

## 2.3 — Tool registration audit

- Verify each stage worker has access to exactly the tools it needs (no excess)
- Verify the unified `research` tool is the only research surface exposed to LLM workers
- Verify Azure ground-truth tools (retail prices, quota, IaC validation) are wired to their respective stages

---

# Phase 3 — Cleanup & Documentation

## 3.1 — Remove dead code

**Frontend (from C.9)**:
- Delete `AgentChatWorkspace.tsx` and all associated legacy components
- Delete unused hooks (`useAgentChat.ts`, `useAgentHealth.ts`, `useProjects.ts`, `useProjectState.ts` in `features/agent/components/hooks/` if superseded)

**Backend — prompt cleanup (from A.1, A.5)**:
- Delete removed prompt sections from `agent_prompts.yaml` (delegation, orchestration stages, duplicate tool listing)
- Delete ReAct template YAML sections from `agent_prompts.yaml`, `architecture_planner_prompt.yaml`, `iac_generator_prompt.yaml` (code uses `llm.bind_tools()` native function calling, not text-based ReAct)

**Backend — dead runtime code (from A.5)**:
- Delete `AAA_STATE_UPDATE` regex extraction from `nodes/postprocess.py`
- Delete `state_update_parser.py` heuristic merge logic
- Delete `backend/app/agents_system/tools/tool_wrappers.py` (replaced by `tool_registry.py` + Pydantic input schemas per tool)
- Delete any remaining `multi_agent.py` stubs if not already removed
- Remove `enable_multi_agent` / `enable_stage_routing` flags if any survive

**Backend — generic agent path**:
- Clean up `nodes/agent.py` if the generic agent path is fully replaced by stage-specific workers
- Remove inline f-string prompt templates from `llm_service.py` if still present (migrate to YAML)
- Remove duplicate compaction prompt from `compaction_service.py` (use PromptLoader)

## 3.2 — Update documentation

**Must update**:
- `docs/refactor/AAA-refactor.md` — mark as superseded, link to this plan
- `docs/architecture/multi-agent-architecture.md` — reflect current single-graph + stage-worker architecture
- `docs/backend/BACKEND_REFERENCE.md` — add new API endpoints (pending changes, quality gate, trace, architect profile, project notes)
- `docs/frontend/FRONTEND_REFERENCE.md` — add new components (PendingChangeDrawer, ClarificationForm, StageBadge, ArchitectChoicePicker, ToolTraceTimeline, etc.)
- `docs/agents/system-architecture.agent.md` — update with new prompt assembly, stage classifier, research facade
- `backend/app/agents_system/langgraph/README.md` — update flow diagram, add new tools and validation steps
- `docs/README.md` — add link to this plan

**New docs**:
- `docs/backend/AZURE_TOOLS_INTEGRATION.md` — document all Azure ground-truth tools, auth modes, configuration
- `docs/frontend/CHAT_UX_COMPONENTS.md` — document all new UX components, their triggers, and data requirements
- `docs/architecture/PROMPT_ARCHITECTURE.md` — document prompt assembly strategy, per-stage YAML ownership, token budgets

## 3.3 — Prompt lint CI gate

- Add `scripts/lint_prompts.py` to CI (A.4)
- Add ESLint rule preventing import of removed legacy components
- Add test that verifies all workspace tabs in manifest have corresponding render entries

---

# Appendix: Dependency graph

```
Phase 0 (Foundation)
  ├── 0.0 Evaluation framework (baseline)
  ├── 0.1 WorkflowStageResult contract
  ├── 0.2 PendingChangeSet DB + API + MergeService + ConflictDetection
  ├── 0.3 SSE event contract
  └── 0.4 StageClassification contract
      │
      ├─────────────────────────────────────────────────────────────────┐
      │                                                                 │
Phase 1 (parallel lanes)                                                │
  ├── Lane A: Prompt & Orchestration                                    │
  │     ├── A.1 Split monolith prompt                                   │
  │     ├── A.2 Hybrid stage classifier ────────────────────────────┐   │
  │     ├── A.3 Stage-contextual prompt injection                   │   │
  │     ├── A.4 Prompt hygiene CI                                   │   │
  │     └── A.5 Typed tool persistence (kill regex) ←── 0.2 PCS    │   │
  │                                                                 │   │
  ├── Lane B: Azure Tools                                         │   │
  │     ├── B.1 Azure Retail Prices tool (public, no auth)          │   │
  │     ├── B.2 Azure Resource Graph + Advisor (v2 — deferred)     │   │
  │     ├── B.3 Azure Quota tool (v2 — deferred)                  │   │
  │     ├── B.4 IaC validation (bicep + terraform + schema)         │   │
  │     ├── B.5 Mermaid validator                                   │   │
  │     └── B.6 Region availability (v2 — deferred)               │   │
  │                                                                 │   │
  ├── Lane C: Frontend UX                                           │   │
  │     ├── C.1 SSE streaming chat ←──────── 0.3 SSE contract      │   │
  │     ├── C.2 Stage badge + progress rail ←── A.2 classification  ┘   │
  │     ├── C.3 Pending change UI ←────────── 0.2 PCS API              │
  │     ├── C.4 Structured clarification form                           │
  │     ├── C.5 Architect-choice picker                                 │
  │     ├── C.6 Live tool trace panel ←──── 0.3 SSE contract           │
  │     ├── C.7 Citations panel                                         │
  │     ├── C.8 Diagram preview + validation ←── B.5 Mermaid validator  │
  │     └── C.9 Retire legacy workspace                                 │
  │                                                                     │
  ├── Lane D: Memory & Personalization                                  │
  │     ├── D.1 SQLite persistent checkpointer                         │
  │     ├── D.2 Architect profile                                       │
  │     └── D.3 Per-project notes                                       │
  │                                                                     │
  ├── Lane E: Retrieval & Research                                      │
  │     ├── E.1 Unified research facade                                 │
  │     └── E.2 Evidence packet traceability                            │
  │                                                                     │
  └── Lane F: Observability & Eval                                      │
        ├── F.1 In-app trace tab ←───── 0.1 WorkflowStageResult        │
        └── F.2 Quality gate report                                     │
                                                                        │
Phase 2 (Integration)                                                   │
  ├── 2.1 E2E flow validation (all stages) ←── all lanes               │
  ├── 2.2 SSE pipeline validation                                       │
  └── 2.3 Tool registration audit                                       │
                                                                        │
Phase 3 (Cleanup) ←──────────────────────────────────────────────────────┘
  ├── 3.1 Remove dead code
  ├── 3.2 Update documentation
  └── 3.3 Add CI gates
```

---

# Appendix: New files summary

| Lane | New files |
|---|---|
| Phase 0 | `contracts/workflow_result.py`, `contracts/pending_change_set.py`, Alembic migration, SSE types |
| A | `tool_registry.py`, `stage_classifier_prompt.yaml`, `prompts/templates/*.yaml`, `scripts/lint_prompts.py` |
| B | `azure_retail_prices_tool.py`, `bicep_validate_tool.py`, `terraform_validate_tool.py`, `schema_validate_tool.py`, `mermaid_validate_tool.py` |
| C | `useSSEChat.ts`, `StageBadge.tsx`, `StageProgressRail.tsx`, `PendingChangeCard.tsx`, `PendingChangeDrawer.tsx`, `pendingChangesService.ts`, `ClarificationForm.tsx`, `ArchitectChoicePicker.tsx`, `ToolTraceTimeline.tsx`, `CitationsPanel.tsx`, `MermaidPreview.tsx` |
| D | `architect_profile.py`, `architect_profile_router.py`, `ArchitectProfileForm.tsx`, `project_notes.py`, `project_notes_router.py`, `ProjectNotesPanel.tsx` |
| E | `research_tool.py` |
| F | `TraceTab.tsx`, `trace_router.py`, `QualityGateTab.tsx`, `quality_gate_service.py`, `quality_gate_router.py` |

---

# Appendix: New dependencies

| Package | Lane | Purpose |
|---|---|---|
| `langgraph-checkpoint-sqlite` | D | Persistent thread memory |
| `hcl2json` | B | Terraform HCL parsing for schema validation |
| `mermaid` (npm) | C | Client-side Mermaid diagram rendering |

> **v2 dependencies** (deferred with B.2/B.3/B.6): `azure-mgmt-resourcegraph`, `azure-mgmt-advisor`, `azure-mgmt-quota`, `azure-identity`

---

# Appendix: Acceptance scenarios & guardrails

> Imported from AAA-refactor Section 4. Every phase must pass relevant scenarios.

## Core acceptance scenarios (15)

| # | Scenario | Expected Result | Spec Ref |
|---|---|---|---|
| 1 | Upload RFP → extraction | Structured requirements + ambiguity flags + C4 L1 diagram | US1 |
| 2 | Approve extraction bundle | Requirements appear in canonical state via MergeService | US1 + approval |
| 3 | Clarification round | 3–5 targeted questions grouped by theme | US1 |
| 4 | Request architecture | Specific Azure architecture with C4 diagrams + NFR analysis | US2 |
| 5 | Request 2 variants | Two distinct candidates with trade-offs | US2 |
| 6 | Create ADR | ADR with context/decision/consequences + traceability links | US3 |
| 7 | Supersede ADR | New ADR links to old, supersession chain intact | US3 |
| 8 | Run WAF validation | Findings with severity + WAF checklist updates | US4 |
| 9 | Estimate cost | TCO breakdown with per-service costs + optimization tips | US5b |
| 10 | Generate Bicep | Validated Bicep with parameters + deployment instructions | US5a |
| 11 | Reject bundle | No state mutation occurs, change set status = rejected | Approval |
| 12 | Revise bundle | **Deferred to v2** — not testable in v1 | Approval |
| 13 | Agent challenges bad choice | Pushes back on single-region for HA with WAF citations | US7 |
| 14 | Export project | Full traceability chain, all 13 mindmap topics accounted | US6 |
| 15 | Conflicting sources | Agent presents 2–3 options, asks for architect choice (FR-018) | Edge case |

## Automated guardrails

- **No hallucinated requirements**: all traced to source document
- **No silent state overwrites**: all mutations via PendingChangeSet + MergeService
- **Conflicting sources → multiple options**: never auto-select (FR-018)
- **Failed MCP research → explicit fallback message**: never hallucinate
- **No generic boilerplate**: specificity score ≥ 3/5 on eval rubric
- **Streaming preserved**: every stage worker emits SSE events

---

# Appendix: Risks & mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Over-engineering internal workers | Delays, complexity | Workers must pass eval improvement test before shipping |
| PendingChangeSet migration complexity | Blocks all stages | Phase 0.2 is self-contained; existing persistence works as fallback |
| Incorrect merge semantics | Data corruption | Deterministic merge with conflict detection; never auto-overwrite |
| Token/context explosion | Bad LLM output | Token budget enforcement in `compose_prompt()`; context compaction enabled (D.1) |
| Phase dependency chain too long | Slow delivery | Each lane is independently measurable; can ship partial improvements |
| Breaking SSE streaming | UX regression | Streaming preservation is non-negotiable principle; tested per phase |
| Regression on working stages | Quality loss | Eval harness (Phase 0.0) runs full suite after every phase |
| v1 scope drift | Delays, complexity | B.2/B.3/B.6 and Edit/Revise explicitly deferred to v2; any new scope requires approval |

---

# Appendix: Open decisions

> These items require architect/owner input before implementation.

| # | Question | Context | Default if unanswered |
|---|---|---|---|
| 1 | **Memory compaction strategy**: Current `memory_compaction_prompt.yaml` exists. Should compaction be time-based (after N turns), token-based (when context exceeds budget), or manual? | Affects D.1 | Token-based (compact when thread context > 80% of budget) |
| 2 | **Export format**: Current export is JSON. Should the quality gate report (F.2) be exportable as PDF, Markdown, or both? | Affects F.2 | Markdown (already supported) |

> **Resolved decisions** (captured in Decision Log above): Azure auth descoped from v1, ArchitectProfile single-user, PCS v1 = Approve/Reject only, FR-018 uses typed contract, streaming uses fetch+ReadableStream, agent_prompts.yaml is backup-only, SaaS advisor activated conditionally.

---

**Status**: Review corrections applied — ready for implementation  
**Last Updated**: 2026-04-17  
**Owner**: Engineering

