# AAA Project Memory & Context Remediation - Implementation Plan

**Date:** 2026-03-29  
**Last Updated:** 2026-03-29  
**Status:** Complete — all 4 phases implemented  
**Objective:** Move the project agent from "fresh turn + static summary" to a thread-aware, compaction-backed, token-budgeted, stage-specific runtime.  
**Primary Outcome:** Conversation continuity across turns, efficient context usage, and stage-adaptive prompt assembly.

---

## 0. Plan Review & Challenges Applied

The original plan (8 workstreams, 5 parallel agents, memory cards, custom retrieval pipeline) was reviewed against state-of-the-art patterns. Seven challenges were applied to reduce scope, eliminate over-engineering, and align with existing infrastructure:

| # | Challenge | SOTA Justification | Resolution |
|---|-----------|-------------------|------------|
| 1 | Custom thread repository vs LangGraph checkpointer | LangGraph docs "How to add thread-level persistence" — native `MemorySaver`/`SqliteSaver`/`PostgresSaver` provide thread-scoped state | Use built-in LangGraph checkpointer; add thin `thread_id` column to `ConversationMessage` only |
| 2 | Memory cards premature | MemGPT paper advocates iterative refinement; `ProjectState` already serves as semantic memory | Defer memory cards; use `ProjectState` + conversation compaction |
| 3 | Full retrieval pipeline rebuild | Anthropic "Contextual Retrieval" (2024): biggest wins = query-driven retrieval + chunk context on existing stack | Enhance existing `ProjectDocumentSearchTool`; remove unconditional excerpts |
| 4 | 8 workstreams / 5 agents | YAGNI + Lean: batch size must match team capacity | Collapse to 4 sequential phases |
| 5 | Missing LangGraph `RemoveMessage` pattern | LangGraph docs "How to add summary conversation memory" | Use native `RemoveMessage` + summarization for compaction |
| 6 | Missing token counting | `tiktoken` already in deps; character estimation unreliable | Add `tiktoken`-based token counting as foundation service |
| 7 | Frontend changes premature | Backend-first: don't build UI for unstable APIs | Defer frontend to separate PR after backend stabilizes |

---

## 1. Scope And Delivery Rules

- Preserve current user-facing chat behavior; all new features behind feature flags.
- Keep rollback simple: every addition has a disable flag.
- Do not bloat the main system prompt to solve context problems.
- Reuse existing LlamaIndex/OpenAI embedding stack for retrieval.
- `ProjectState` remains the semantic project memory layer.
- LangGraph checkpointer handles thread-scoped conversation state.
- Frontend changes deferred to a separate PR after backend API stabilizes.

---

## 2. Target Runtime

### 2.1 Memory Tiers

| Tier | Content | Storage |
|------|---------|---------|
| **Hot** | Last N turns, current stage directives, active tool results | LangGraph checkpointer (in-memory/SQLite) |
| **Warm** | Conversation summary (compacted from older turns) | LangGraph state + DB snapshot |
| **Semantic** | Requirements, constraints, decisions, open questions, architecture artifacts | `ProjectState` JSON (existing) |
| **Cold** | Full transcript, MCP queries, tool traces | `ConversationMessage` table (existing) + trace events (new) |

### 2.2 Context Injection Policy (Stage-Specific)

| Stage | High-Priority Sections | Lower-Priority (drop first) |
|-------|----------------------|---------------------------|
| `clarify` | goals, ambiguities, recent clarifications, missing decisions | doc excerpts, tool traces |
| `propose_candidate` | requirements, NFRs, constraints, prior decisions, Azure evidence | full doc text, iteration logs |
| `manage_adr` | decision record, trade-offs, prior options, citations | requirements list, pricing |
| `validate` | WAF deltas, missing evidence, risks, checklist state | full architecture recap |
| `pricing` | chosen services, usage assumptions, budget constraints | NFR details, IaC |
| `iac` | finalized design, resources, compliance, naming rules | pricing details, clarifications |

### 2.3 Remediation Themes

1. Add thread-scoped short-term memory via LangGraph checkpointer.
2. Add compaction via LangGraph `RemoveMessage` + summarization before context pressure.
3. Build token-budgeted, stage-specific context packs.
4. Replace unconditional document excerpts with query-driven retrieval.
5. Add context usage telemetry.

---

## 3. Files This Plan Touches

### 3.1 Backend Files

- `backend/app/models/project.py` — add `thread_id` to `ConversationMessage`, add `ProjectTraceEvent` model
- `backend/app/agents_system/langgraph/state.py` — extend `GraphState` with thread/memory fields
- `backend/app/agents_system/langgraph/graph_factory.py` — add checkpointer, compaction node, context pack node
- `backend/app/agents_system/langgraph/adapter.py` — pass thread config, handle thread lifecycle
- `backend/app/agents_system/langgraph/nodes/context.py` — replace monolithic summary with context pack
- `backend/app/agents_system/langgraph/nodes/persist.py` — persist thread metadata, trace events
- `backend/app/agents_system/langgraph/nodes/agent_native.py` — consume context packs, emit telemetry
- `backend/app/agents_system/services/project_context.py` — split into reusable extractors
- `backend/app/core/settings/agents.py` — add feature flags
- `backend/app/core/settings/llm_tuning.py` — add compaction/budget thresholds
- `backend/app/core/app_settings.py` — surface new settings
- `backend/app/routers/agents/models.py` — add `threadId` to request/response
- `backend/app/routers/agents/router.py` — pass thread id through
- `backend/app/services/project/chat_service.py` — thread-scoped message retrieval

### 3.2 New Backend Files

- `backend/app/agents_system/memory/__init__.py`
- `backend/app/agents_system/memory/token_counter.py` — tiktoken-based counting
- `backend/app/agents_system/memory/compaction_service.py` — conversation summarization
- `backend/app/agents_system/memory/context_budget.py` — token budget per section
- `backend/app/agents_system/memory/context_pack_service.py` — stage-specific packs
- `backend/app/agents_system/memory/context_packs/` — per-stage pack builders
- `backend/app/agents_system/memory/telemetry.py` — context usage metrics
- `backend/config/prompts/memory_compaction_prompt.yaml`
- `backend/config/prompts/context_pack_sections.yaml`
- `backend/migrations/versions/<timestamp>_add_thread_and_trace_tables.py`

### 3.3 Test Files

- `backend/tests/agents_system/test_token_counter.py`
- `backend/tests/agents_system/test_compaction_service.py`
- `backend/tests/agents_system/test_context_budget.py`
- `backend/tests/agents_system/test_context_pack_service.py`
- `backend/tests/agents_system/test_memory_telemetry.py`

---

## 4. Dependencies

### 4.1 Existing (Reuse)

- `langgraph`, `langchain-core`, `langchain-openai` — graph + checkpointer
- `SQLAlchemy` — DB models
- `tiktoken` — token counting
- `llama-index-*` — existing retrieval
- existing React/Vitest/Playwright stack

### 4.2 New (Add Only If Needed)

| Dependency | When | Decision |
|-----------|------|----------|
| `langgraph-checkpoint-sqlite` | Phase 1 | Yes — persistent dev checkpointing |
| `langgraph-checkpoint-postgres` | Phase 4+ | Deferred — only for production scale |
| `pgvector` | Phase 4+ | Deferred — only if retrieval quality needs it |

---

## 5. Feature Flags

All added to `backend/app/core/settings/agents.py` via `AppSettings`:

| Flag | Default | Purpose |
|------|---------|---------|
| `AAA_THREAD_MEMORY_ENABLED` | `False` | Enable LangGraph checkpointer for thread continuity |
| `AAA_CONTEXT_COMPACTION_ENABLED` | `False` | Enable conversation summarization/compaction |
| `AAA_CONTEXT_PACKS_ENABLED` | `False` | Enable stage-specific context packs |
| `AAA_CONTEXT_DEBUG_ENABLED` | `False` | Expose context debug info in API responses |
| `AAA_CONTEXT_MAX_HISTORY_TURNS` | `10` | Max recent turns in hot memory |
| `AAA_CONTEXT_COMPACT_THRESHOLD_TOKENS` | `4000` | Trigger compaction when history exceeds this |
| `AAA_CONTEXT_MAX_BUDGET_TOKENS` | `12000` | Total token budget for context pack |
---

`AAA_CONTEXT_COMPACT_THRESHOLD_TOKENS` remains the history-pressure trigger for compaction. Stage-specific context packs and composed system directives should instead use `AAA_CONTEXT_MAX_BUDGET_TOKENS` as the active assembly budget.

## 6. Implementation Phases

### Phase 1: Foundation — Feature Flags, Token Counter, Thread Schema, LangGraph Checkpointer

**Goal:** Establish the infrastructure for thread-aware conversation memory.  
**Depends on:** Nothing  
**Blocks:** All subsequent phases

#### Tasks

- [x] Add feature flags to `agents.py` settings (all flags from Section 5).
- [x] Surface new settings through `AppSettings`.
- [x] Create `backend/app/agents_system/memory/` package.
- [x] Add `token_counter.py` — tiktoken-based counting with model-aware encoding.
- [x] Add `thread_id` nullable column to `ConversationMessage` model.
- [x] Add `ProjectThread` model (id, project_id, stage, title, is_active, created_at, updated_at).
- [x] Add `ProjectTraceEvent` model (id, project_id, thread_id, event_type, payload, created_at).
- [x] Create Alembic migration for new tables/columns.
- [x] Add LangGraph `MemorySaver` checkpointer to graph compilation (behind flag).
- [x] Pass `thread_id` config to graph invocation in `adapter.py`.
- [x] Add `thread_id` to router request/response models.
- [x] Write tests for token counter, migration, and thread-aware graph invocation.

#### Acceptance

- [x] Feature flags loadable from environment.
- [x] Token counter produces accurate counts for GPT-4 model family.
- [x] Graph runs with checkpointer when flag enabled; runs without when disabled.
- [x] New tables exist in migration; rollback is safe.

---

### Phase 2: Conversation Compaction + Token Budgeting

**Goal:** Summarize old conversation turns to stay within token budget.  
**Depends on:** Phase 1

#### Tasks

- [x] Add `compaction_service.py` — conversation summarization using LLM call.
- [x] Add `context_budget.py` — token budget allocation per context section.
- [x] Add `memory_compaction_prompt.yaml` — prompt template for summarization.
- [x] Load compaction system/user templates through `PromptLoader` so compaction prompts stay YAML-driven and hot-reloadable.
- [x] Integrate compaction check in graph: if history tokens > threshold, summarize older turns.
- [x] Store compaction summaries in graph state (`thread_summary` field).
- [x] Add tool-result clearing: old raw tool outputs not replayed into future turns.
- [x] Write tests for compaction service and context budget.

#### Acceptance

- [x] Follow-up message can reference prior turns via summary.
- [x] Compaction triggers only when token threshold exceeded.
- [x] Old tool outputs are cleared after compaction.
- [x] Compaction flag can be disabled without breaking chat.
- [x] Compaction prompt content is sourced from YAML, not duplicated inline strings.

---

### Phase 3: Stage-Specific Context Packs

**Goal:** Inject different context depending on workflow stage.  
**Depends on:** Phase 2

#### Tasks

- [x] Define `ContextPack` typed schema (system_prefix, stage_policy, thread_summary, recent_turns, project_facts, open_questions, context_budget_meta).
- [x] Create `context_pack_service.py` — assembles pack based on stage.
- [x] Create per-stage packer functions (clarify, propose_candidate, manage_adr, validate, pricing, iac).
- [x] Add token budget per section with drop policy (drop low-value first, never drop hard constraints).
- [x] Integrate context packs into `nodes/context.py` as alternative to monolithic summary (behind flag).
- [x] Add `context_pack_sections.yaml` for configurable section templates.
- [x] Write tests for context pack service and stage-specific variation.

#### Acceptance

- [x] `clarify` packs are materially different from `validate` and `iac` packs.
- [x] Token budget overflow degrades gracefully (sections dropped by priority).
- [x] Monolithic summary path still works when flag is disabled.

---

### Phase 4: Telemetry + Query-Driven Retrieval Enhancement

**Goal:** Make context usage measurable; stop injecting unconditional document excerpts.  
**Depends on:** Phase 3

#### Tasks

- [x] Add `telemetry.py` — capture token usage, compaction events, context pack composition per turn.
- [x] Persist telemetry to `ProjectTraceEvent` table.
- [x] Modify `get_project_context_summary()` to skip raw document excerpts when context packs are active.
- [x] `ProjectDocumentSearchTool` already query-driven; unconditional excerpts bypassed by context packs.
- [x] Telemetry emission behind `AAA_CONTEXT_DEBUG_ENABLED` flag.
- [x] Write tests for telemetry persistence.

#### Acceptance

- [x] Developers can inspect token usage per turn.
- [x] Raw 2000-char document excerpts no longer injected when context packs are active.
- [x] Telemetry stored in trace table, not in ProjectState.

---

## 7. Rollout Strategy

1. Merge Phase 1 with all flags defaulting to `False`. Existing behavior unchanged.
2. Enable `AAA_THREAD_MEMORY_ENABLED` in dev. Validate thread continuity.
3. Enable `AAA_CONTEXT_COMPACTION_ENABLED` after continuity tests pass.
4. Enable `AAA_CONTEXT_PACKS_ENABLED` after compaction is stable.
5. Enable `AAA_CONTEXT_DEBUG_ENABLED` for developers only.
6. Keep stateless fallback (flags=False) for at least one release cycle.

---

## 8. Master Implementation Checklist

### Phase 1 — Foundation
- [x] Feature flags added and surfaced.
- [x] Token counter service implemented and tested.
- [x] Thread schema + migration created.
- [x] LangGraph checkpointer integrated (behind flag).
- [x] Thread ID flows through router → adapter → graph → persist.

### Phase 2 — Compaction
- [x] Compaction service implemented and tested.
- [x] Context budget service implemented and tested.
- [x] Compaction prompt template created.
- [x] Graph integrates compaction check node.
- [x] Tool-result clearing policy active.

### Phase 3 — Context Packs
- [x] Context pack schema defined.
- [x] Stage-specific packers implemented.
- [x] Context pack service integrated into graph.
- [x] Drop policy handles budget overflow.
- [x] Tests verify stage variation.

### Phase 4 — Telemetry + Retrieval
- [x] Telemetry service implemented.
- [x] Trace events persisted.
- [x] Unconditional excerpts bypassed when context packs active.
- [x] Document tool already query-driven.
- [x] Telemetry behind flag.

---

## 9. Deferred Items (Future PRs)

These items from the original plan are deferred based on SOTA review:

| Item | Reason | Revisit When |
|------|--------|-------------|
| Memory cards (`project_memory_cards` table) | `ProjectState` already serves as semantic memory; cards add complexity without immediate payoff | After compaction proves insufficient for decision recall |
| Custom retrieval pipeline (chunker + contextualizer + reranker) | Existing LlamaIndex + OpenAI stack handles current doc volume | When document volume exceeds 50+ per project |
| Postgres checkpointer | MemorySaver sufficient for dev; SQLite for single-instance prod | When multi-instance deployment is needed |
| Frontend thread UI (ContextStatusBadge, MemoryDebugPanel) | Backend APIs must stabilize first | After Phase 3 merges successfully |
| Multi-agent context isolation | Specialist nodes are not yet active by default | After multi-agent flag is commonly enabled |
