# Agent Orchestration Separation — Task Plan

Goal: Separate orchestration (lifecycle, routing, DI, budgets, telemetry) from agent implementations (LangChain ReAct, RAG wrapper) without changing external APIs.

## Scope & Principles
- Orchestrator owns execution flow, tool/prompt assembly, context injection, budgets/timeouts, optional summarization and telemetry.
- Agents only build/run chains with injected `llm`, `prompt`, and `tools`.
- Tools are LangChain `BaseTool` wrappers over our services (MCP ops, RAG service).
- MCP client and RAG services stay LangChain-free.
- Preserve `runner` and FastAPI lifecycle wiring.

## Phase 0 — Preparation
- [ ] Create safety branch: `chore/agent-orchestration-separation`
- [ ] Confirm current behavior via a quick query run (manual)

## Phase 1 — Orchestrator Skeleton
- [x] Add package `backend/app/agents_system/orchestrator/`
- [x] Implement `orchestrator.py` with `AgentOrchestrator`:
  - `initialize(mcp_client, settings)`
  - `execute(user_query: str, project_context: Optional[str]) -> dict`
  - `shutdown()`
- [x] Implement `registry.py` to construct tools (MCP + KB) and provide factories (Phase 1 placeholder)
- [x] Define execution budgets (iterations/timeouts) and context injection in orchestrator

## Phase 2 — Agent Extraction & Interface
- [x] Create `backend/app/agents_system/agents/mcp_react_agent.py`
  - Accept injected `llm`, `prompt`, `tools`, and limits via constructor
  - Implement `initialize()` and `execute()` using LangChain `AgentExecutor`
- [x] Define minimal `Agent` protocol (initialize/execute) for consistency
- [x] Keep existing `rag_agent.py` unchanged (already a service wrapper)
- [x] Add compatibility shim in `agents/mcp_agent.py` (deprecated re-export) to avoid breaking imports

## Phase 3 — Tools & Prompts Assembly
- [x] Keep tools in place: `tools/mcp_tool.py`, `tools/kb_tool.py`
- [x] Move tool assembly into orchestrator; retain existing factories (`create_mcp_tools()`, `create_kb_tools()`)
- [x] Centralize prompt composition
  - Using `agents_system/config/react_prompts` injected via orchestrator

## Phase 4 — Runner Wiring
- [ ] Refactor `backend/app/agents_system/runner.py` to own `AgentOrchestrator`
  - Replace direct `MCPReActAgent` usage with orchestrator
  - Keep public methods: `initialize()`, `execute_query()`, `shutdown()`
- [ ] Ensure `backend/app/lifecycle.py` remains unchanged in wiring (initializes MCP client, then runner)
  - Note: Phase 1 keeps existing wiring unchanged (verified)

## Phase 5 — Cross-Cutting Concerns
- [ ] Implement summarization hook contract in `conversation/summary_chain.py` and call from orchestrator (no-op if stub)
- [ ] Add telemetry/tracing hooks (start/end, tool usage, errors) in orchestrator
- [ ] Ensure error handling, parsing hints remain intact (from current ReAct agent)

## Phase 6 — Safety & QA
- [ ] Verify imports and avoid circular dependencies (orchestrator → agents/tools/services; tools → services)
- [ ] Add smoke test: instantiate orchestrator with mocked MCP client, run `execute()` on a simple query, assert result shape
- [ ] Run lint/type checks (`ruff`, `mypy`, `pyright`) and fix issues

## Phase 7 — Documentation & Commits
- [ ] Add docs: `docs/AGENT_ARCHITECTURE.md` explaining boundaries, dependencies, runtime flow
- [ ] Commit plan:
  - Pass 1: introduce orchestrator + agent extraction + compatibility shim (no behavior change)
  - Pass 2: switch runner to orchestrator; wire prompt/tool injection there
- [ ] Optional: add migration notes for future agent types (planner, function-calling)

## Acceptance Criteria
- Queries execute successfully via the orchestrator with identical outputs to current behavior
- `runner` API remains unchanged; FastAPI lifecycle continues to work
- MCP client and RAG services have no LangChain imports
- Clear module boundaries: orchestrator, agents, tools, services
- Tests and linters pass; docs updated
