
# LangGraph Migration Plan (AAA Backend)

Date: 2026-01-12

## 1) Goal

Migrate the backend agent orchestration from the current LangChain ReAct `AgentExecutor` loop to LangGraph, while preserving:

- Existing API contracts and response schemas.
- Existing ProjectState update parsing + merge semantics.
- Existing tool surface area (MCP tools, KB tool, AAA tools).

Primary outcomes:

- Explicit, testable workflow control (less stalling at stage boundaries).
- Clear branching rules (“Architect choice required”, retries, timeouts).
- A foundation for multi-agent orchestration (supervisor → specialists) after the single-graph baseline is stable.

## 2) Hard constraints (must hold throughout)

### 2.1 Code size constraints

- No new module/file larger than ~200 lines. If it grows, split by responsibility (node/state/helpers).
- No function/method larger than ~20–50 lines. If it grows, extract helpers.
- One module = one primary responsibility.

### 2.2 UX constraints

- No new pages/routes/UX flows.
- Preserve a single chat flow from the portal.
- Keep the existing HTTP endpoints stable.

### 2.3 Compatibility constraints

- Preserve the `ProjectAgentChatResponse` shape returned by `POST /api/agent/projects/{project_id}/chat`.
- Preserve how `AAA_STATE_UPDATE` blocks are extracted and merged (no-overwrite merge).
- Preserve “Architect choice required” behavior (FR-018): block state updates until explicit selection.
- Preserve how MCP query logs are derived from tool calls.

## 3) Current baseline (what we are migrating from)

### 3.1 Primary entrypoints

- Project-aware agent endpoint: `POST /api/agent/projects/{project_id}/chat`
- Router implementation: `backend/app/agents_system/agents/router.py`

### 3.2 Current flow responsibilities (project-aware)

The router currently does orchestration-like work:

1) Loads ProjectState from DB
2) Builds context summary
3) Executes agent via runner/orchestrator
4) Parses `AAA_STATE_UPDATE` in assistant output
5) Derives MCP query logs from intermediate steps
6) Blocks state updates if “Architect choice required” is present
7) Persists conversation messages + applies state updates
8) Post-processes answer with uncovered topics, failed MCP guidance, merge conflict surfacing

This is already a workflow; LangGraph is a better fit for readability, retries, checkpointing, and testability.

### 3.3 Existing components we will reuse

- Agent runner/orchestrator:
  - `backend/app/agents_system/runner.py`
  - `backend/app/agents_system/orchestrator/orchestrator.py`
  - `backend/app/agents_system/agents/mcp_react_agent.py`
- ProjectState update pipeline:
  - `backend/app/agents_system/services/state_update_parser.py`
  - `backend/app/agents_system/services/project_context.py`
- MCP logging derivation:
  - `backend/app/agents_system/services/iteration_logging.py`
- Tools:
  - MCP tools: `backend/app/agents_system/tools/mcp_tool.py`
  - KB tool: `backend/app/agents_system/tools/kb_tool.py`
  - AAA tools: `backend/app/agents_system/tools/aaa_candidate_tool.py` (+ the tools it imports)

## 4) Target architecture (LangGraph)

### 4.1 Design principle

Move orchestration into a LangGraph graph while keeping:

- tool implementations unchanged
- DB models unchanged
- request/response models unchanged

### 4.2 Graph boundaries

We start with a single “project-aware chat graph” that handles one user turn end-to-end.

Later, we can split into subgraphs (doc research subgraph, ADR subgraph, validation subgraph, pricing subgraph, IaC subgraph), but we do not do that until parity is proven.

### 4.3 Graph state (per-turn)

Define a typed graph state that carries everything needed for a single turn:

- `project_id: str`
- `user_message: str`
- `context_summary: str | None`
- `current_project_state: dict`
- `agent_output: str`
- `intermediate_steps: list` (must preserve enough shape to derive MCP logs)
- `architect_choice_required_section: str | None`
- `derived_updates: dict` (MCP logs + iteration events)
- `state_updates: dict | None` (from `AAA_STATE_UPDATE` extraction)
- `combined_updates: dict`
- `updated_project_state: dict | None`
- `final_answer: str`
- `success: bool`
- `error: str | None`

Keep this state minimal and stable; add fields only when needed.

## 5) File/module plan (enforcing size limits)

Add a new package:

`backend/app/agents_system/langgraph/`

Each module must stay ≤200 lines.

### 5.1 New modules

1) `backend/app/agents_system/langgraph/state.py`
	- Graph state type (TypedDict/dataclass) and small constants
	- No orchestration logic

2) `backend/app/agents_system/langgraph/nodes/context.py`
	- `load_project_state_node(...)`
	- `build_context_summary_node(...)`
	- Only wraps existing services

3) `backend/app/agents_system/langgraph/nodes/agent.py`
	- `run_agent_node(...)`
	- Phase 1: calls existing runner/orchestrator to preserve behavior

4) `backend/app/agents_system/langgraph/nodes/postprocess.py`
	- Pure helpers + nodes:
	  - detect “Architect choice required” section
	  - `extract_state_updates(...)`
	  - `derive_mcp_query_updates_from_steps(...)`
	  - combine updates

5) `backend/app/agents_system/langgraph/nodes/persist.py`
	- `persist_messages_node(...)`
	- `apply_state_updates_node(...)`
	- Wraps `update_project_state(...)`

6) `backend/app/agents_system/langgraph/graph_factory.py`
	- `build_project_chat_graph(...)` returning a compiled graph
	- Only wires nodes and edges

7) `backend/app/agents_system/langgraph/adapter.py`
	- A small adapter exposing an `execute_project_chat(...)` method
	- Returns the same dict shape currently expected by the router

### 5.2 Keep existing modules unchanged (initially)

- Tool implementations remain as-is.
- Prompt loading remains as-is.
- Router models remain as-is.

## 6) Migration strategy (phased, low risk)

### Phase 0 — Inventory + invariants (no behavior change)

Tasks:

1) Write down invariants for the project chat endpoint:
	- Response schema and keys
	- What gets persisted on each request (messages, mcpQueries, iterationEvents, openQuestions)
	- When state updates are blocked (architect choice)

2) Capture a small set of “golden interactions” as fixtures:
	- at least 5 project chat requests and expected structural assertions
	- include one “Architect choice required” scenario

Deliverables:

- This document acts as the acceptance criteria.

### Phase 1 — Add LangGraph dependency + skeleton (no routing change)

Tasks:

3) Add `langgraph` dependency (pinned).
4) Create `backend/app/agents_system/langgraph/` package + empty modules.
5) Add a minimal `GraphState` model and a no-op graph that can be compiled.

Acceptance:

- Existing unit tests pass.
- Importing the new modules does not change runtime behavior.

### Phase 2 — Build a minimal project chat graph that wraps existing agent execution

Goal: LangGraph controls the orchestration, but the actual tool loop remains the current `MCPReActAgent` for now.

Tasks:

6) Implement `load_project_state_node`.
7) Implement `build_context_summary_node`.
8) Implement `run_agent_node` by calling the existing runner/orchestrator.
9) Implement postprocess nodes:
	- architect choice extraction
	- `extract_state_updates` call
	- MCP log derivation from intermediate steps
	- combined updates merge
10) Implement persistence nodes:
	- persist conversation messages
	- apply state updates when allowed
11) Implement response-building node.
12) Wire nodes into `build_project_chat_graph`.
13) Add a “graph smoke test” that uses stubbed dependencies (LLM/tool execution mocked) and asserts:
	- combined updates logic matches current behavior
	- architect choice blocks state update

Acceptance:

- Graph can be executed in isolation.
- Graph output is compatible with the router’s response model.

### Phase 3 — Swap the project-aware route to use the graph adapter (feature-flagged)

Tasks:

14) Add an env/config flag: `AAA_USE_LANGGRAPH=true|false`.
15) In `POST /api/agent/projects/{project_id}/chat`:
	- if flag is on, call graph adapter
	- else, run existing code path
16) Add an API-level test that exercises the endpoint through FastAPI and asserts stable schema.

Acceptance:

- With the flag on: behavior matches legacy path on the golden fixtures.
- With the flag off: unchanged.

### Phase 4 — Make the tool loop graph-native

Goal: Replace `AgentExecutor` loop with LangGraph-native agent/tool loop.

Tasks:

17) Replace `run_agent_node` to use LangGraph tool loop (ToolNode + LLM node) while preserving:
	- tool list
	- prompt template
	- max iterations/timeouts
18) Ensure tool trace is captured in a consistent structure.
19) Update MCP log derivation to support the new trace shape (keep it in a small adapter function).
20) Add tests for trace conversion.

Acceptance:

- Intermediate steps still drive MCP log derivation and UI reasoning.
- No regression in state update persistence.

### Phase 5 — Add explicit stage routing + retry semantics (agent behavior)

Goal: eliminate “stops at each stage” behavior by enforcing stage transitions in the graph.

Tasks:

21) Add a `classify_next_stage_node` that outputs a bounded enum:
	- clarify
	- propose_candidate
	- manage_adr
	- validate
	- pricing
	- iac
	- export
22) Add branching edges per stage.
23) Add a retry loop edge:
	- if tool output begins with `ERROR:` → ask missing fields → retry once
24) Add a “always propose next step” postprocessing node:
	- if the turn did not persist an artifact, it must produce 1–5 high-impact questions

Acceptance:

- The system always returns either:
  - a persisted update, or
  - minimal clarifying questions to proceed.

### Phase 6 — Multi-agent (later; not required for LangGraph cutover)

After Phase 5 is stable:

25) Introduce a supervisor node that selects a specialist subgraph.
26) Specialists use narrowed toolsets and prompts:
	- ADR specialist: `aaa_manage_adr` + research tools
	- Validation specialist: `aaa_record_validation_results` + research tools
	- Pricing specialist: pricing-only usage of `aaa_record_iac_and_cost`
	- IaC specialist: iac-only usage of `aaa_record_iac_and_cost`

## 7) Testing plan (what to add/update)

### 7.1 Existing tests to keep

- State update parser tests
- Merge/no-overwrite behavior tests
- Tool contract tests for AAA tools

### 7.2 New tests to add

1) Graph smoke test (no DB):
	- stubs agent output + intermediate steps
	- asserts derived updates and combined updates are correct

2) Trace conversion test (Phase 4):
	- asserts MCP derivation works for the new trace shape

3) API-level test (Phase 3):
	- calls `/api/agent/projects/{project_id}/chat`
	- asserts schema stability and basic persistence

4) End-to-end stage test (Phase 5):
	- clarify → ADR → validate → pricing → IaC → persist updates
	- verifies the system does not stall

## 8) Key risks and mitigations

1) Tool trace shape drift
	- Mitigation: isolate trace conversion and test it.

2) Behavior drift from prompt changes
	- Mitigation: Phase 2 wraps existing agent execution; prompts/toolsets remain unchanged until later.

3) Checkpointing/storage choice
	- Mitigation: treat ProjectState DB as the canonical store; graph checkpointing is optional and can be added later.

## 9) Definition of Done

Migration complete when:

- Project-aware agent endpoint runs through LangGraph by default.
- Golden fixtures pass.
- Tests cover: architect choice blocking, state update persistence, MCP log derivation, and a stage flow.
- The codebase respects size constraints for the new LangGraph modules.

