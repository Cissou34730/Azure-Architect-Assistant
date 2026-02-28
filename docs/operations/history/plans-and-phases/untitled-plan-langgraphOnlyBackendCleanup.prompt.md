## Plan: Backend LangGraph-Only Cleanup

Remove all backend legacy LangChain runtime paths and the direct langchain package dependency, while keeping LangGraph-compatible stack (langgraph + langchain-core + langchain-openai). The migration is done in ordered phases so API behavior stays stable and regressions are caught early.

**Steps**
1. Phase 1 — Freeze baseline and guardrails  
   - Run targeted baseline tests for agent routes and LangGraph nodes before edits, then capture failures to distinguish pre-existing vs introduced issues.  
   - Validate current entrypoints and singleton lifecycle around runner startup/shutdown in [backend/app/lifecycle.py](backend/app/lifecycle.py), [backend/app/agents_system/runner.py](backend/app/agents_system/runner.py), and [backend/app/agents_system/agents/router.py](backend/app/agents_system/agents/router.py).

2. Phase 2 — Remove legacy execution switching (blocks later deletions)  
   - Make LangGraph the only backend execution path in router by removing legacy branch/fallback code and langchain engine checks in [backend/app/agents_system/agents/router.py](backend/app/agents_system/agents/router.py) and simplifying settings in [backend/app/core/app_settings.py](backend/app/core/app_settings.py).  
   - Remove langchain-oriented config semantics (AAA_AGENT_ENGINE values, compatibility coercion) while preserving current env defaults for LangGraph-related flags.

3. Phase 3 — Remove legacy ReAct stack and references (depends on 2)  
   - Delete legacy runtime modules: [backend/app/agents_system/agents/mcp_react_agent.py](backend/app/agents_system/agents/mcp_react_agent.py), [backend/app/agents_system/orchestrator/orchestrator.py](backend/app/agents_system/orchestrator/orchestrator.py), and langchain package helpers in [backend/app/agents_system/langchain/agent_facade.py](backend/app/agents_system/langchain/agent_facade.py), [backend/app/agents_system/langchain/prompt_builder.py](backend/app/agents_system/langchain/prompt_builder.py), [backend/app/agents_system/langchain/facade_utils.py](backend/app/agents_system/langchain/facade_utils.py), [backend/app/agents_system/langchain/tool_registry.py](backend/app/agents_system/langchain/tool_registry.py).  
   - Move/replace any still-needed generic helper behavior (input normalization wrappers) into a neutral helper module under langgraph or tools (no langchain package namespace).

4. Phase 4 — Migrate tool typing away from langchain package (parallel with 3 after helper move)  
   - Replace imports using langchain.tools with langchain_core.tools where applicable in [backend/app/agents_system/tools/mcp_tool.py](backend/app/agents_system/tools/mcp_tool.py), [backend/app/agents_system/tools/kb_tool.py](backend/app/agents_system/tools/kb_tool.py), [backend/app/agents_system/tools/aaa_candidate_tool.py](backend/app/agents_system/tools/aaa_candidate_tool.py), [backend/app/agents_system/tools/aaa_adr_tool.py](backend/app/agents_system/tools/aaa_adr_tool.py), [backend/app/agents_system/tools/aaa_cost_tool.py](backend/app/agents_system/tools/aaa_cost_tool.py), [backend/app/agents_system/tools/aaa_diagram_tool.py](backend/app/agents_system/tools/aaa_diagram_tool.py), [backend/app/agents_system/tools/aaa_export_tool.py](backend/app/agents_system/tools/aaa_export_tool.py), [backend/app/agents_system/tools/aaa_iac_tool.py](backend/app/agents_system/tools/aaa_iac_tool.py), [backend/app/agents_system/tools/aaa_validation_tool.py](backend/app/agents_system/tools/aaa_validation_tool.py), and [backend/app/agents_system/langgraph/nodes/agent_native.py](backend/app/agents_system/langgraph/nodes/agent_native.py).  
   - Keep ChatOpenAI from langchain-openai in place for LangGraph nodes unless a separate provider refactor is requested.

5. Phase 5 — Simplify runner to LangGraph-only responsibilities (depends on 3)  
   - Refactor [backend/app/agents_system/runner.py](backend/app/agents_system/runner.py) so it no longer initializes/owns legacy orchestrator or execute_query ReAct behavior; keep only shared OpenAI settings + MCP client access needed by LangGraph adapter/nodes.  
   - Update dependent injection and health contracts in [backend/app/dependencies.py](backend/app/dependencies.py) and [backend/app/agents_system/langgraph/adapter.py](backend/app/agents_system/langgraph/adapter.py).

6. Phase 6 — Dependencies, tests, and docs alignment (depends on 2–5)  
   - Remove direct langchain dependency from [pyproject.toml](pyproject.toml) and regenerate [uv.lock](uv.lock) via uv lock/sync workflow.  
   - Update/remove legacy tests: [backend/tests/agents/test_agent_facade.py](backend/tests/agents/test_agent_facade.py), [backend/tests/agents/test_prompt_builder.py](backend/tests/agents/test_prompt_builder.py), [backend/tests/agents/test_mcp_react_agent_llm_wiring.py](backend/tests/agents/test_mcp_react_agent_llm_wiring.py), [backend/tests/agents_system/test_prompt_loader.py](backend/tests/agents_system/test_prompt_loader.py), plus any fixtures in [backend/tests/conftest.py](backend/tests/conftest.py) that assume legacy internals.  
   - Refresh backend docs to reflect LangGraph-only runtime in [docs/BACKEND_REFERENCE.md](docs/BACKEND_REFERENCE.md), [docs/LANGGRAPH_MIGRATION_COMPLETE.md](docs/LANGGRAPH_MIGRATION_COMPLETE.md), and [docs/README.md](docs/README.md).

**Verification**
- Targeted: run updated agent-system unit tests first (LangGraph nodes, router, runner).  
- Workspace task: Run backend unit tests.  
- Workspace task: Run full backend tests.  
- Static check: grep backend for disallowed runtime references (langchain.agents, AgentExecutor, initialize_agent, app.agents_system.langchain).  
- Dependency check: confirm pyproject/uv.lock no longer contain direct langchain package entry.

**Decisions**
- Included: remove direct langchain package entirely; backend runtime uses only LangGraph path.  
- Included: tests and docs updated in same change.  
- Excluded: frontend and non-backend architectural refactors not required for LangGraph-only enforcement.
