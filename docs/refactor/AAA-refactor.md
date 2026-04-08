# AAA Runtime Rebuild — Unified Plan

> **Status**: Approved after review session 2026-04-07
> **Branch**: `feature/parallel-work-architecture-implementation`
> **Spec reference**: `specs/002-azure-architect-assistant/spec.md` (7 user stories)

## Objective

Rebuild the AAA runtime into a **deterministic, workflow-driven system** that:
- Produces **high-quality, structured, reviewable outputs** (not generic boilerplate)
- Enforces **approval-first state mutation** via PendingChangeSets
- Maintains **traceability, WAF alignment, and mindmap coverage**
- Eliminates fragile prompt-driven state inference (no regex, no text-block parsing)
- Remains **chat-first UX** with strong internal structure
- Preserves **SSE streaming** throughout the rebuild
- Implements **all 7 user stories** from the spec

---

## Root Causes (Why Current System Fails)

| # | Root Cause | Evidence (code reference) |
|---|---|---|
| 1 | **1000+ line monolithic prompt** that dilutes instructions | `backend/config/prompts/agent_prompts.yaml` — system_prompt section |
| 2 | **Sub-agent delegation never implemented** | `adapter.py` hardcodes `enable_multi_agent=False`; specialist nodes in `nodes/multi_agent.py` are stubs |
| 3 | **ReAct template is dead code** | Prompt defines text-based `Thought/Action/Final Answer` but `nodes/agent_native.py` uses `llm.bind_tools()` (native function calling) |
| 4 | **State persistence via regex** | `nodes/postprocess.py` parses `AAA_STATE_UPDATE` text blocks; tools return text blocks, not DB writes |
| 5 | **Critical prompts lack examples** | `architecture_planner_prompt.yaml` has 0 C4/Mermaid examples; `iac_generator_prompt.yaml` has 0 code snippets |
| 6 | **No structured output validation** | Agent output is free-form text; persistence is fragile and often missed |
| 7 | **Tool input normalization is fragile** | `tools/tool_wrappers.py` does JSON parsing with multiple fallbacks instead of proper Pydantic schemas |
| 8 | **Context window bloat** | System prompt + context summary + mindmap + research plan + guardrails can exceed 4000+ tokens before the user speaks |

---

# 0. Core Principles (Non-Negotiable)

## 0.1 Workflow-first architecture
The system is structured around **explicit workflow stages**, not a general-purpose agent.

### Canonical stages (10 total — maps to all 7 user stories)

| Stage | Spec User Story | Description |
|---|---|---|
| `extract_requirements` | US1 — Ingest & Extract | Transform documents into structured requirements |
| `clarify` | US1 — Gap-filling | Interactive clarification of ambiguities |
| `propose_candidate` | US2 — Candidate Architectures | Generate architecture candidates with diagrams |
| `manage_adr` | US3 — Decisions & ADRs | Create and manage architecture decision records |
| `validate` | US4 — Validation & Findings | WAF + security baseline validation |
| `estimate_cost` | US5b — Cost Estimation | Azure pricing, TCO analysis (separate from IaC) |
| `generate_iac` | US5a — IaC Generation | Bicep/Terraform code generation (separate from cost) |
| `export` | — | Final deliverable export with traceability |
| `review_pending_changes` | — | Approval/rejection of pending change sets |
| `general_chat` | US7 — Document-Driven Iteration | Fallback conversational mode, next-step driving |

**Note**: US6 (Mind Map & Traceability) and US7 (Document-Driven Iteration) are cross-cutting behaviors, not dedicated stages.

## 0.2 Approval-first state model
- No mutation of canonical state without **explicit approval**
- All outputs are first produced as **PendingChangeSets**
- Human-authored content is always authoritative
- Primary approval via **API endpoints with UI buttons**; chat-parsed commands as fallback

## 0.3 Typed contracts over free text
- No parsing of state from LLM output (eliminate `AAA_STATE_UPDATE` regex)
- All outputs are structured and validated via Pydantic schemas
- Tools persist directly to DB and return structured JSON confirmation

## 0.4 Deterministic domain services
- **Mindmap coverage** is computed by backend service (not LLM)
- **WAF evaluation** is a deterministic matcher (not LLM) — LLM generates findings/recommendations only
- **Deterministic merge** for deduplication, clustering, provenance tracking

## 0.5 Specialists are internal, not architectural
- No "9 top-level agents" with independent orchestration
- Specialists exist as **workers inside stages**
- Workers are either **LLM-based** (need specialized prompt) or **deterministic** (pure code)

## 0.6 Evaluation-driven refactoring
- No refactor without measurable improvement
- Every phase ships with golden test scenarios
- Baseline measured before work begins

## 0.7 Streaming preservation
- **SSE streaming must be preserved** throughout the entire rebuild
- Every stage worker must support the existing `event_callback` streaming pattern

## 0.8 Prompt hot-reload
- All prompts loadable from YAML without backend restart
- `PromptLoader` singleton with file-watch / explicit reload support preserved

---

# 1. Target Runtime Architecture

## 1.1 High-level flow

```
User Message
    ↓
Conversation Router (hybrid: state-rules + lightweight LLM classification)
    ↓
Stage Worker (deterministic entrypoint, one per stage)
    ↓
Internal Workers (LLM or deterministic, filtered tools per worker)
    ↓
WorkflowStageResult (typed, validated)
    ↓
PendingChangeSet (persisted to new DB table)
    ↓
Review / Approval (API endpoint + UI buttons, chat fallback)
    ↓
Canonical State Update (via deterministic merge services)
```

## 1.2 Router Design

The **Conversation Router** uses a hybrid approach:

1. **State-based rules (cheapest, first pass)**:
   - No requirements → `extract_requirements`
   - Requirements but no architecture → `propose_candidate`
   - Pending changes exist → `review_pending_changes`

2. **Keyword intent detection (second pass)**:
   - "validate", "waf", "security" → `validate`
   - "cost", "pricing", "budget" → `estimate_cost`
   - "bicep", "terraform", "iac" → `generate_iac`
   - "adr", "decision" → `manage_adr`
   - "export", "report" → `export`

3. **Lightweight LLM classification (fallback, ~100 tokens structured output)**:
   - Only when rules 1-2 are ambiguous
   - Returns `ConversationIntent` enum via structured output
   - Adds ~200ms latency, used sparingly

## 1.3 Internal Layering

### Level 1 — Workflow (product level)
- Defines system behavior
- Drives UX and semantics
- Owns the 10-stage lifecycle

### Level 2 — Stage Workers
- One per workflow stage
- Owns orchestration logic within the stage
- Calls internal workers in sequence or parallel
- Produces `WorkflowStageResult` → `PendingChangeSet`

### Level 3 — Internal Workers

| Worker | Type | LLM Call? | Prompt Needed? | Tools |
|---|---|---|---|---|
| Requirements extractor | **LLM** | Yes | `requirements_extraction.yaml` | `project_document_search`, `aaa_manage_artifacts` |
| Clarification planner | **LLM** | Yes | `clarification_planner.yaml` | `kb_search`, `aaa_manage_artifacts` |
| Architecture synthesizer | **LLM** | Yes | `architecture_planner_prompt.yaml` (existing, add examples) | `mcp_*`, `kb_search`, `aaa_generate_candidate_architecture`, `aaa_create_diagram_set` |
| Researcher | **LLM** | Yes | `research.yaml` | `mcp_*` (Microsoft Learn search/fetch/code samples) |
| WAF evaluator | **Deterministic** | No | — | Backend service: match architecture components against checklist rules |
| Mindmap coverage calculator | **Deterministic** | No | — | Backend service: compute coverage from artifact links |
| Diagram generator | **Hybrid** | Partial | Mermaid generation is LLM; versioning/storage is deterministic | `aaa_create_diagram_set` |
| Cost estimator | **LLM** | Yes | `cost_estimator_prompt.yaml` (existing — **reference quality**, preserve as-is) | `mcp_*`, `aaa_record_cost_estimate` |
| IaC generator | **LLM** | Yes | `iac_generator_prompt.yaml` (existing, add Bicep/Terraform examples) | `mcp_*`, `aaa_record_iac_artifacts` |
| ADR drafter | **LLM** | Yes | `adr_writer.yaml` (new) | `kb_search`, `aaa_manage_adr` |
| SaaS advisor | **LLM** | Yes | `saas_advisor_prompt.yaml` (existing — **reference quality**, preserve activation filters) | `mcp_*`, `kb_search` |
| Deterministic merge | **Deterministic** | No | — | Dedup, cluster, provenance tracking by artifact ID |

**Rules for all workers:**
- Scoped tools per worker (not full tool set)
- No independent orchestration (stage worker controls flow)
- 5-10 tool call iterations max per LLM worker
- Must support streaming via `event_callback`

## 1.4 Reasoning Visibility

- **User sees**: reasoning summary (collapsible section in response)
- **User sees**: tool call names + result summaries in stream events
- **Debug access**: full reasoning chain stored in DB, accessible via API for debugging
- **Intermediate steps**: preserved in `intermediate_steps` field as today

---

# 2. Data Model & Contracts

## 2.1 Core Types

### ConversationIntent (10 values)
```python
class ConversationIntent(str, Enum):
    EXTRACT_REQUIREMENTS = "extract_requirements"
    CLARIFY = "clarify"
    PROPOSE_CANDIDATE = "propose_candidate"
    MANAGE_ADR = "manage_adr"
    VALIDATE = "validate"
    ESTIMATE_COST = "estimate_cost"
    GENERATE_IAC = "generate_iac"
    EXPORT = "export"
    REVIEW_PENDING_CHANGES = "review_pending_changes"
    GENERAL_CHAT = "general_chat"
```

### WorkflowStageResult
```python
class WorkflowStageResult(BaseModel):
    summary: str                                 # Human-readable summary of what was done
    pending_change_set: PendingChangeSet | None  # Produces changes? → bundle them
    citations: list[Citation]                    # All sources consulted
    warnings: list[str]                          # Issues, gaps, risks detected
    next_recommended_action: str                 # Proactive next-step proposal
    reasoning_summary: str                       # Collapsible reasoning for user
    intermediate_steps: list[dict]               # Tool call traces for debug
```

## 2.2 PendingChangeSet

**Storage: New DB table** (`pending_change_sets`)

```python
class PendingChangeSet(BaseModel):
    id: str                         # UUID
    project_id: str                 # FK to project
    stage: ConversationIntent       # Which stage produced this
    status: ChangeSetStatus         # pending | approved | rejected | superseded
    created_at: datetime
    source_message_id: str          # Conversation message that triggered this
    superseded_by: str | None       # If superseded, link to replacement

    bundle_summary: str             # Human-readable description of changes
    proposed_patch: dict            # Structured diff to apply

    artifact_drafts: list[ArtifactDraft]  # All proposed artifacts
    citations: list[Citation]
    waf_delta: dict | None          # WAF checklist status changes
    mindmap_delta: dict | None      # Mindmap coverage changes
```

```python
class ChangeSetStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
```

**DB Schema** (Alembic migration in Phase 3):
- `pending_change_sets` table: id, project_id, stage, status, created_at, source_message_id, superseded_by, bundle_summary, proposed_patch (JSON), waf_delta (JSON), mindmap_delta (JSON)
- `artifact_drafts` table: id, change_set_id (FK), artifact_type, content (JSON), citations (JSON)

## 2.3 ArtifactDraft Types

```python
class ArtifactDraftType(str, Enum):
    REQUIREMENT = "requirement"
    ASSUMPTION = "assumption"
    CLARIFICATION_QUESTION = "clarification_question"
    CANDIDATE_ARCHITECTURE = "candidate_architecture"
    DIAGRAM = "diagram"                    # C4, Mermaid
    WAF_UPDATE = "waf_update"
    ADR = "adr"
    COST_ESTIMATE = "cost_estimate"
    IAC = "iac"
    FINDING = "finding"                    # Validation findings
```

## 2.4 ApprovalCommand

**Primary: API endpoints with UI buttons** (preferred)
```
POST /api/projects/{project_id}/changes/{change_set_id}/approve
POST /api/projects/{project_id}/changes/{change_set_id}/reject
POST /api/projects/{project_id}/changes/{change_set_id}/revise
GET  /api/projects/{project_id}/changes?status=pending
GET  /api/projects/{project_id}/changes/{change_set_id}
```

**Fallback: Chat-parsed commands** (routed to `review_pending_changes` stage)
- "approve latest"
- "reject latest"
- "approve bundle {id}"
- "revise latest"

## 2.5 State Separation

### Canonical State
- Approved artifacts only
- Source of truth for all downstream stages
- Stored in existing `ProjectState` model

### Pending State
- Reviewable bundles in `pending_change_sets` table
- Each bundle is immutable once created
- Supersession creates a new bundle, marks old as superseded

### Rules
- Never mix pending and canonical
- Never auto-promote (all changes require explicit approval)
- Canonical state is read-only input to all stage workers

---

# 3. Phase Plan (Full Execution — 13 Phases)

Each functional phase (4–10) follows the same pattern:
1. Define stage worker entry point
2. Create/update stage-specific prompt (if LLM workers involved)
3. Implement internal workers (LLM or deterministic)
4. Wire into router + PendingChangeSet output
5. Add golden test scenarios + eval
6. Measure improvement against Phase 0 baseline

---

# Phase 0 — Evaluation Framework (MANDATORY FIRST)

## Goals
- Establish baseline quality measurements
- Prevent regression throughout rebuild
- Quantify improvement per phase

## Actions

### 0.1 Golden scenarios

Create 15+ scenarios mapped to user stories:

| Category | Count | Examples |
|---|---|---|
| US1 — Requirements extraction | 3 | Ambiguous RFP, multi-format docs, NFR-heavy spec |
| US2 — Candidate architecture | 3 | Simple web app, multi-region HA, microservices |
| US3 — ADR management | 2 | Create ADR, supersede ADR |
| US4 — WAF validation | 2 | Full validation run, incremental checklist update |
| US5a — IaC generation | 2 | Bicep for App Service, Terraform for AKS |
| US5b — Cost estimation | 2 | Basic web app TCO, multi-region cost comparison |
| US7 — Proactive iteration | 1 | Agent challenges bad design choices |

### 0.2 Scoring rubric

Per scenario, score 1-5 on:
- **Specificity**: not generic/boilerplate (cites project-specific details)
- **Tool usage**: called appropriate tools (MCP, KB, AAA)
- **Persistence**: state correctly updated via PendingChangeSet
- **Structure**: headings, tables, actionable items (not wall of text)
- **Challenge quality**: pushes back on bad choices with WAF citations
- **Citation grounding**: references Microsoft Learn URLs, WAF pillars
- **Completeness**: addresses the full request, doesn't leave gaps

### 0.3 Eval harness

Location: `backend/tests/eval/`

Capabilities:
- Replay test messages through full pipeline
- Capture agent outputs + tool calls + state changes
- Score automatically against rubric
- Generate comparison report (baseline vs current)

### 0.4 Baseline current system

Document for each scenario:
- Failure mode (generic, no tools, no persistence, etc.)
- Hallucination instances
- Missing structure
- Score per rubric dimension

---

# Phase 1 — Runtime Stabilization

## Goals
- Remove structural inconsistencies that cause confusion
- Prepare codebase for deterministic routing

## Actions

### 1.1 Fix stage routing
- Stage must be resolved **before** context assembly (currently happens in parallel)
- Remove reliance on inferred stage from agent output

### 1.2 Remove dual runtime paths

Unify into single LangGraph path. Currently there are:
- `execute_chat()` → non-project path in `adapter.py`
- `execute_project_chat()` → project path in `adapter.py`
- `LLMService` inline prompts in `llm_service.py` (document analysis, architecture proposal, chat refinement)

**Decision**: Single path through `build_project_chat_graph()`. Move `LLMService` inline prompts to YAML.

### 1.3 Remove dead code

| What | Where | Why dead |
|---|---|---|
| `react_template` YAML section | `agent_prompts.yaml` | Code uses `llm.bind_tools()` native function calling, not text-based ReAct |
| `AAA_STATE_UPDATE` regex extraction | `nodes/postprocess.py` | Will be replaced by direct tool persistence in Phase 3 |
| Stub specialist nodes | `nodes/multi_agent.py` | `adr_specialist_node()`, `validation_specialist_node()`, etc. are empty stubs |
| `tool_wrappers.py` | `agents_system/tools/tool_wrappers.py` | Replace with proper Pydantic schemas on each tool |
| Hardcoded `enable_multi_agent=False` | `adapter.py` lines 113, 163 | Remove flag; new architecture uses stage workers, not multi-agent |
| Inline prompts (3 f-string templates) | `llm_service.py` lines 48, 303, 417 | Move to YAML; eliminate f-string injection risk |
| Inline compaction prompt duplicate | `compaction_service.py` line 18 | Duplicates `memory_compaction_prompt.yaml`; use PromptLoader |

### 1.4 Keep endpoints stable
- `/api/agent/projects/{project_id}/chat` — no change
- `/api/agent/projects/{project_id}/chat/stream` — no change
- Add new: `/api/projects/{project_id}/changes/*` — approval endpoints (Phase 3)

---

# Phase 2 — Prompt Architecture Refactor

## Goals
- Reduce prompt entropy (1000+ lines → modular ~80 line components)
- Enable per-stage specialization
- Preserve hot-reload

## Actions

### 2.1 Split monolithic `agent_prompts.yaml` into:

| File | Lines (target) | Content |
|---|---|---|
| `base_persona.yaml` | ~80 | Role, WAF methodology, behavioral core (proactive, challenge, cite) |
| `orchestrator_routing.yaml` | ~60 | Intent classification rules, delegation triggers, stage transitions |
| `tool_strategy.yaml` | ~40 | When/how to use MCP, KB, AAA tools; citation rules |
| `guardrails.yaml` | ~30 | Hallucination prevention, out-of-scope refusal, conflict resolution (FR-018) |

### 2.2 Stage-specific prompts (new + updated)

| File | Status | Stage |
|---|---|---|
| `requirements_extraction.yaml` | **New** | `extract_requirements` |
| `clarification_planner.yaml` | **New** | `clarify` |
| `architecture_planner_prompt.yaml` | **Update** — add C4 Mermaid examples | `propose_candidate` |
| `adr_writer.yaml` | **New** | `manage_adr` |
| `waf_validator.yaml` | **New** (for LLM findings generation, not deterministic matching) | `validate` |
| `cost_estimator_prompt.yaml` | **Preserve as-is** — reference quality (scored 9-10/10) | `estimate_cost` |
| `iac_generator_prompt.yaml` | **Update** — add Bicep/Terraform code snippets | `generate_iac` |
| `saas_advisor_prompt.yaml` | **Preserve as-is** — excellent activation filters | (cross-cutting) |
| `research.yaml` | **New** | (cross-cutting worker) |

### 2.3 Add mandatory few-shot examples

| Prompt | Examples to add |
|---|---|
| `architecture_planner_prompt.yaml` | 2-3 complete Mermaid C4 diagrams (System Context + Container) with NFR analysis |
| `iac_generator_prompt.yaml` | 3-5 Bicep/Terraform snippets (App Service, SQL DB, Storage, parameterization, modules) |
| `requirements_extraction.yaml` | 1-2 structured extraction examples from raw text → categorized requirements |
| `adr_writer.yaml` | 1 complete ADR example with context/decision/consequences/alternatives |

### 2.4 Prompt loader upgrade

```python
# New method on PromptLoader
compose_prompt(
    agent_type: str,        # "orchestrator", "requirements_extractor", etc.
    stage: str,             # ConversationIntent value
    context_budget: int,    # Max tokens for context injection
) -> str
```

Features:
- Assembles: base_persona + stage-specific + tool_strategy + guardrails
- Token budget enforcement: truncates context summary to fit
- Hot-reload preserved: file watcher on YAML directory
- No f-string injection: use `string.Template` or YAML variables

---

# Phase 3 — Approval System & Typed Persistence

## Goals
- Implement the **full PendingChangeSet approval system** (required before any stage implementation)
- Eliminate free-text mutation
- Provide API + UI approval flow

## Actions

### 3.1 Database migration

New Alembic migration adding:
- `pending_change_sets` table (schema from Section 2.2)
- `artifact_drafts` table with FK to `pending_change_sets`
- Indexes on `(project_id, status)` for pending queries

### 3.2 Implement core Pydantic models
- `PendingChangeSet`, `ChangeSetStatus`, `ArtifactDraft`, `ArtifactDraftType`
- `WorkflowStageResult`
- `ApprovalCommand`
- Strict validation on all fields

### 3.3 Implement approval API endpoints

```
POST /api/projects/{project_id}/changes/{id}/approve  → merge into canonical state
POST /api/projects/{project_id}/changes/{id}/reject   → mark rejected, no state change
POST /api/projects/{project_id}/changes/{id}/revise   → mark superseded, agent revises
GET  /api/projects/{project_id}/changes?status=pending → list pending bundles
GET  /api/projects/{project_id}/changes/{id}           → view bundle details
```

### 3.4 Implement merge services

- `MergeService.apply_change_set(project_id, change_set_id)` → deterministic merge into canonical state
- Merge rules per artifact type:
  - Requirements: merge by ID + lineage
  - Architectures: append versions (don't overwrite)
  - Diagrams: versioned (keep history)
  - WAF: append evidence to checklist items
  - ADRs: append, support supersession chain
  - Cost estimates: replace (latest wins)
  - IaC: replace (latest wins)

### 3.5 Conflict detection
- When canonical state was modified by human between bundle creation and approval
- Surface conflicts in human-readable format
- Require explicit resolution (no silent overwrite)

### 3.6 Replace tool persistence model

**Old (to remove)**:
- AAA tools return `AAA_STATE_UPDATE` text blocks
- `postprocess.py` regex extraction
- `state_update_parser.py` heuristic merge

**New**:
- AAA tools write to `pending_change_sets` + `artifact_drafts` tables directly
- Tools return structured JSON confirmation: `{"change_set_id": "...", "artifacts_created": 3}`
- No regex, no text parsing, no heuristic inference

### 3.7 Remove `tool_wrappers.py`
- Each AAA tool gets proper Pydantic `BaseModel` input schema
- LangChain `bind_tools()` natively handles Pydantic schemas
- Delete `backend/app/agents_system/tools/tool_wrappers.py`

---

# Phase 4 — Stage: `extract_requirements`

> **Spec**: US1 — Ingest & Extract Requirements (Priority P1)

## Goals
- Exhaustive, source-grounded requirement extraction from documents
- Structured output: business/functional/NFR categories with ambiguity markers
- Initial C4 context diagram + WAF baseline

## Pipeline

### 4.1 Reuse existing ingestion pipeline
- Extend `backend/app/features/ingestion/` (not replace)
- Document chunking and normalization already exists
- Add structured extraction layer on top

### 4.2 Requirements extractor worker (LLM)
- Prompt: `requirements_extraction.yaml`
- Tools: `project_document_search`, `aaa_manage_artifacts`
- Input: document chunks
- Output per chunk:
  - Requirements (business/functional/NFR) with IDs
  - Ambiguity markers
  - Assumptions (explicit and inferred)
  - Citations (source document + location)

### 4.3 Deterministic merge worker (code)
- Deduplicate requirements across chunks (by semantic similarity + ID)
- Cluster related requirements
- Preserve provenance (which document, which chunk)

### 4.4 Diagram + WAF initialization workers
- Diagram generator (LLM): C4 Level 1 context diagram from requirements
- WAF baseline (deterministic): initialize all 5 pillar checklists as not-covered
- Mindmap coverage (deterministic): initial coverage assessment

### 4.5 Bundle → PendingChangeSet
- All artifacts bundled into one `PendingChangeSet`
- User reviews extracted requirements before they become canonical
- Bundle includes: requirements, assumptions, ambiguities, initial diagram, WAF baseline

### 4.6 First interaction flow
- **When project has uploaded documents**: router → `extract_requirements` stage → present findings + ask 3-5 targeted gap questions
- **When no documents**: router → `clarify` stage → structured onboarding questions (workload type, scale, compliance, budget)

---

# Phase 5 — Stage: `clarify`

> **Spec**: US1 — Gap-filling (Priority P1)

## Goals
- High-value, structured clarification questions
- Questions driven by detected ambiguities, WAF gaps, and mindmap gaps
- Interactive: user answers → state updates via new bundle

## Components

### 5.1 Clarification planner worker (LLM)

Inputs:
- Extracted requirements (from canonical state)
- Ambiguity markers
- WAF gaps (deterministic: which pillars are not-covered)
- Mindmap gaps (deterministic: which topics are not-addressed)
- Prior clarification history (don't re-ask)

Outputs:
- Grouped questions (by theme: performance, security, cost, operations)
- Prioritized by impact on architecture decisions
- Max 3-5 questions per response
- Each question explains **why** it matters for architecture

### 5.2 Clarification resolution worker (LLM)
- When user answers questions → extract structured updates
- Updates packaged as PendingChangeSet:
  - Updated requirements (filled gaps)
  - Resolved ambiguities (marked as answered)
  - New assumptions (from user answers)

---

# Phase 6 — Stage: `propose_candidate`

> **Spec**: US2 — Candidate Architectures (Priority P1)

## Goals
- Produce structured, specific architecture proposals (not boilerplate)
- Default **1 candidate**, optionally **2+** when explicitly requested
- Always evidence-backed with MCP research

## Pipeline

### 6.1 Mandatory research worker (LLM)
- Queries MCP / Microsoft Learn for:
  - Service-specific guidance
  - Architecture patterns
  - Best practices
- Evidence mapped to requirements

### 6.2 Architecture synthesizer worker (LLM)
- Prompt: `architecture_planner_prompt.yaml` (updated with C4 examples)
- Generates per candidate:
  - Azure services with rationale
  - Assumptions linked to requirements
  - Trade-offs (explicitly stated)
  - C4 diagrams (System Context + Container level, Mermaid)
  - Citations (MCP results, WAF references)
  - WAF delta (which checklist items affected)
  - Mindmap delta (which topics addressed)

### 6.3 Bundle → PendingChangeSet
- All candidate artifacts in one bundle
- User reviews architecture proposal before it becomes canonical

---

# Phase 7 — Stage: `manage_adr`

> **Spec**: US3 — Decisions & ADRs (Priority P2)

## Goals
- Structured ADR lifecycle: draft → accepted → superseded
- Traceability: requirement → ADR → diagram → WAF → finding

## Components

### 7.1 ADR drafter worker (LLM)
- Prompt: `adr_writer.yaml` (new, with example)
- Generates: context, decision, consequences, alternatives considered
- Links to originating requirements + mindmap topics

### 7.2 ADR lifecycle
- Create: draft status
- Accept: approved via PendingChangeSet approval
- Supersede: creates new ADR, links to superseded one

### 7.3 Bundle → PendingChangeSet

---

# Phase 8 — Stage: `validate`

> **Spec**: US4 — Validation & Findings (Priority P2)

## Goals
- Validate architecture against all 5 WAF pillars + security baselines
- Produce findings with severity and remediation suggestions
- Never auto-reject — findings are advisory

## Components

### 8.1 WAF evaluator (deterministic)
- Match architecture components against WAF checklist rules
- Update checklist items: covered / partial / not-covered
- No LLM needed for status computation

### 8.2 Findings generator worker (LLM)
- Prompt: `waf_validator.yaml` (new)
- Input: WAF evaluator results + architecture state
- Output: findings with severity (critical/high/medium/low), impacted components, remediation suggestions
- Each finding cites WAF pillar/checklist item + source URL

### 8.3 Bundle → PendingChangeSet
- Findings + WAF checklist updates bundled
- User reviews findings before they become canonical

---

# Phase 9 — Stage: `estimate_cost`

> **Spec**: US5b — Cost Estimation (Priority P3)

## Goals
- Accurate Azure cost estimation using Retail Prices API
- Monthly/annual/3-year TCO breakdown
- Optimization recommendations

## Components

### 9.1 Cost estimator worker (LLM)
- Prompt: `cost_estimator_prompt.yaml` (**preserve as-is** — best prompt in the system, scored 9-10/10)
- Tools: `mcp_*` (Azure Pricing API), `aaa_record_cost_estimate`
- Output: cost breakdown by service, optimization opportunities, RI recommendations

### 9.2 Bundle → PendingChangeSet

---

# Phase 10 — Stage: `generate_iac`

> **Spec**: US5a — IaC Generation (Priority P3)

## Goals
- Production-ready Bicep and/or Terraform
- Parameterized, modular, validated

## Components

### 10.1 IaC generator worker (LLM)
- Prompt: `iac_generator_prompt.yaml` (**updated with Bicep/Terraform code examples**)
- Tools: `mcp_*`, `aaa_record_iac_artifacts`
- Output: validated IaC files with parameterization, deployment instructions

### 10.2 Bundle → PendingChangeSet

---

# Phase 11 — Export + Context & Memory Optimization

> **Spec**: Export (final deliverable) + operational improvements

## Goals
- Complete project export with traceability
- Fix context/memory issues for long conversations

## Actions

### 11.1 Export stage
- `export` stage worker
- Full project export: requirements → ADRs → diagrams → WAF → IaC → costs
- Traceability chains: stable IDs, no broken references
- Mindmap coverage scorecard (13 topics with evidence)

### 11.2 Context & memory

| Action | Current State | Fix |
|---|---|---|
| Context compaction | `aaa_context_compaction_enabled=False` | Enable + test |
| Token budget | Unbounded context in system prompt | Enforce max in `compose_prompt()` |
| Thread memory | `aaa_thread_memory_enabled=False` | Enable LangGraph checkpointer |
| Inline prompts | 3 f-string templates in `llm_service.py` | Move to YAML (done in Phase 1) |
| Duplicate compaction prompt | `compaction_service.py` duplicates YAML | Use PromptLoader (done in Phase 1) |

---

# Phase 12 — Cutover & Cleanup

## Goals
- Single clean runtime path
- No dead code

## Actions

### 12.1 Remove all legacy code
- Legacy orchestrator flows
- Unused prompt sections
- Dead graph nodes (stubs from multi-agent Phase 6)
- `enable_stage_routing` / `enable_multi_agent` flags (no longer needed)

### 12.2 Verify single runtime path
- All requests flow through: Router → Stage Worker → Workers → PendingChangeSet → Approval → Merge
- No bypass paths

### 12.3 Final eval run
- Run all 15+ golden scenarios
- Score must exceed baseline on all dimensions
- Generate final comparison report

---

# 4. Testing & Acceptance

## Per-Phase Testing

Every phase ships with:
- Golden test scenarios for the implemented stage
- Eval harness scoring against Phase 0 baseline
- Regression check on previously working stages

## Core Acceptance Scenarios

| # | Scenario | Expected Result | Spec Reference |
|---|---|---|---|
| 1 | Upload RFP → extraction | Structured requirements + ambiguity flags + C4 L1 diagram | US1 |
| 2 | Approve extraction bundle | Requirements appear in canonical state | US1 + approval |
| 3 | Clarification round | 3-5 targeted questions grouped by theme | US1 |
| 4 | Request architecture | Specific Azure architecture with C4 diagrams + NFR analysis | US2 |
| 5 | Request 2 variants | Two distinct candidates with trade-offs | US2 |
| 6 | Create ADR | ADR with context/decision/consequences + traceability links | US3 |
| 7 | Supersede ADR | New ADR links to old, supersession chain intact | US3 |
| 8 | Run WAF validation | Findings with severity + WAF checklist updates | US4 |
| 9 | Estimate cost | TCO breakdown with per-service costs + optimization tips | US5b |
| 10 | Generate Bicep | Validated Bicep with parameters + deployment instructions | US5a |
| 11 | Reject bundle | No state mutation occurs | Approval |
| 12 | Revise bundle | New bundle supersedes old | Approval |
| 13 | Agent challenges bad choice | Pushes back on single-region for HA with WAF citations | US7 |
| 14 | Export project | Full traceability chain, all 13 mindmap topics accounted | US6 |
| 15 | Conflicting sources | Agent presents 2-3 options, asks for architect choice | Edge case (FR-018) |

## Guardrails (automated checks)

- No hallucinated requirements (all traced to source document)
- No silent state overwrites (all mutations via PendingChangeSet)
- Conflicting sources → multiple options presented (never auto-select)
- Failed MCP research → explicit fallback message (never hallucinate)
- No generic boilerplate (specificity score ≥ 3/5)

---

# 5. Risks & Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| Over-engineering internal workers | Delays, complexity | Workers must pass eval improvement test before shipping |
| PendingChangeSet migration complexity | Blocks all stages | Phase 3 is self-contained; existing persistence works as fallback |
| Incorrect merge semantics | Data corruption | Deterministic merge with conflict detection; never auto-overwrite |
| Token/context explosion | Bad LLM output | Token budget enforcement in `compose_prompt()`; context compaction |
| Phase dependency chain too long | Slow delivery | Each phase is independently measurable; can ship partial improvements |
| Breaking SSE streaming | UX regression | Streaming support is mandatory per-phase acceptance criterion |
| Regression on working stages | Quality loss | Eval harness runs full suite after every phase |

## Rollback Strategy

- **Feature flags per phase**: each stage can be disabled independently
- **Incremental cutover**: old and new paths can coexist during transition
- **Git-based rollback**: one branch per phase, easy revert
- **Eval regression gate**: phase doesn't ship if it regresses previous scores

---

# 6. Decisions Log

Decisions made during plan review session (2026-04-07):

| # | Decision | Rationale |
|---|---|---|
| D1 | 10 canonical stages (not 5) | All 7 user stories must be implementable; IaC and Cost are separate stages |
| D2 | One phase per stage (13 phases total) | Clear scope boundaries, independent measurement |
| D3 | `extract_requirements` and `clarify` are separate stages | Extract is automatic (document processing); clarify is interactive (gap-filling) |
| D4 | Workers are mixed: some LLM, some deterministic | WAF evaluator + mindmap coverage = deterministic code; extractors/planners/synthesizers = LLM |
| D5 | Approval via API endpoints + UI buttons (primary), chat fallback | Chat-parsed "approve latest" is fragile as sole mechanism |
| D6 | New DB tables for PendingChangeSet | Clean separation, proper FK constraints, queryable |
| D7 | Phase 3 builds full approval system before stages 4-6 | Approval-first is a core principle; cannot defer |
| D8 | Reuse and extend existing ingestion pipeline | `backend/app/features/ingestion/` already handles document processing |
| D9 | Default 1 candidate architecture, optionally 2+ | 2 candidates doubles LLM cost; make configurable |
| D10 | SSE streaming must be preserved throughout rebuild | Non-negotiable UX requirement |
| D11 | Preserve `cost_estimator_prompt.yaml` as-is | Reference quality (scored 9-10/10 in analysis) |
| D12 | Preserve `saas_advisor_prompt.yaml` as-is | Excellent activation filters, thorough tenant models |
| D13 | Hybrid router: state rules → keywords → lightweight LLM fallback | Cheap for common cases, accurate for ambiguous ones |
| D14 | 5-10 tool call iterations per LLM worker | Thorough research, not rushing |
| D15 | Prompt hot-reload preserved | Critical for rapid iteration during rebuild |
| D16 | Reasoning: summary visible to user, full chain for debug | Balances UX with debuggability |
| D17 | Tool calls visible in UI stream events | Transparency for architect |
| D18 | Remove all dead code in Phase 1 | ReAct template, AAA_STATE_UPDATE regex, stub specialists, tool_wrappers.py, inline prompts |
