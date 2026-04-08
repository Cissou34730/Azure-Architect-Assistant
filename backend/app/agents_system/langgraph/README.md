# LangGraph Runtime - Backend Guide

This document describes the current LangGraph state-based orchestration runtime used by backend agent chat endpoints.

## Overview

The backend agent runtime is LangGraph-only and provides:
- Explicit, testable workflow control
- Clear branching rules for architect choices and retries
- Foundation for multi-agent orchestration
- Better stage transition handling

## Architecture

### Foundation
**Core LangGraph integration**

- Package structure: `backend/app/agents_system/langgraph/`
- GraphState TypedDict for workflow state
- Node-based orchestration for project chat workflows

**Nodes:**
- `nodes/context.py` - Load project state and build context
- `nodes/clarify.py` - Execute the dedicated clarify-stage planning/resolution workers
- `nodes/extract_requirements.py` - Execute the dedicated requirements-extraction stage worker
- `nodes/manage_adr.py` - Execute the dedicated manage-ADR pending-change worker
- `nodes/research.py` - Build research plans and materialize Phase 6 research evidence packets
- `nodes/validate.py` - Execute the dedicated validate-stage worker (deterministic WAF evaluation + findings payload synthesis)
- `nodes/cost_estimator.py` - Execute the dedicated pricing-stage worker/runtime path and reuse the existing cost estimator + AAA cost tool flow
- `nodes/iac_generator.py` - Execute the dedicated IaC-stage worker/runtime path and reuse the specialized IaC handoff + generator node without falling back to the generic graph agent loop
- `nodes/export.py` - Execute the dedicated export-stage worker (deterministic AAA export payload generation)
- `nodes/architecture_planner.py` - Execute the dedicated architecture synthesizer for `propose_candidate` and emit a reviewable synthesis-execution artifact alongside the pending-change/postprocess flow
- `nodes/agent.py` - Execute stage-aware agent node
- `nodes/postprocess.py` - Extract updates, derive MCP logs
- `nodes/persist.py` - Save messages and apply state updates

**Flow:** load_state → classify_stage → build_summary → [extract_requirements | clarify_stage_worker | export_stage_worker | build_research → (research_worker for `propose_candidate`) → build_mindmap_guidance → {prepare_architecture_handoff → architecture_planner | manage_adr_stage_worker | validate_stage_worker | cost_stage_worker | iac_stage_worker | run_agent}] → persist_messages → [end | postprocess → apply_updates]

- The architecture synthesizer reuses `nodes/architecture_planner.py` instead of introducing a second proposal path. It now records `architecture_synthesis_execution_artifact` metadata so tests and later evaluators can verify that evidence packets, WAF/mindmap deltas, and review-mode output sections were requested without bypassing the approval-first pending-change flow.

### Graph-Native Tool Loop
**ToolNode-based execution**

- `nodes/agent_native.py` - LangGraph-native agent execution
- Uses `AIService.create_chat_llm().bind_tools()` + `ToolNode` for provider-selected tool execution
- Message-based trace (AIMessage, ToolMessage)
- Respects iteration limits and timeouts
- `config/prompt_loader.py` keeps orchestrator directives YAML-driven and enforces the supplied prompt budget before the final system prompt is injected.
- `nodes/context.py` builds stage-specific context packs with `AAA_CONTEXT_MAX_BUDGET_TOKENS`, while `graph_factory.py` adds a `MemorySaver` checkpointer with `AAA_THREAD_MEMORY_ENABLED` now defaulting on for thread-scoped LangGraph memory.
- `memory/compaction_service.py` reads `memory_compaction_prompt.yaml` through `PromptLoader`, so compaction prompt edits hot-reload with the rest of the prompt surface.

### Stage Routing + Retry
**Explicit stage transitions and error handling**

- `nodes/stage_routing.py` - Stage classification and retry logic (`how much`, `TCO`, and similar spend-first prompts now classify as `pricing`)
- ProjectStage enum: extract_requirements, clarify, propose_candidate, manage_adr, validate, pricing, iac, export
- Retry loop for ERROR: prefixed outputs
- Always propose next steps if no artifacts persisted
- Feature flag: `AAA_ENABLE_STAGE_ROUTING`

### Multi-Agent Specialists
**Supervisor routes to specialized agents**

- `nodes/multi_agent.py` - Supervisor and specialist nodes
- SpecialistType enum: adr, validation, pricing, iac, general
- Each specialist has narrowed toolset and focused prompts
- Supervisor routes based on task classification
- Feature flag: `AAA_ENABLE_MULTI_AGENT`

**Specialists:**
- **ADR Specialist** - Architecture decision records (aaa_manage_adr + research)
- **Validation Specialist** - WAF and security validation (aaa_record_validation_results)
- **Pricing Specialist** - Cost estimation (pricing tools only)
- **IaC Specialist** - Infrastructure as Code generation (IaC tools only)

## Configuration

### Environment Variables

```bash
# Enable Stage Routing
AAA_ENABLE_STAGE_ROUTING=false  # Set to true for explicit stage transitions

# Enable Multi-Agent
AAA_ENABLE_MULTI_AGENT=false  # Set to true for specialist routing
```

### Feature Flag Combinations

| AAA_ENABLE_STAGE_ROUTING | AAA_ENABLE_MULTI_AGENT | Behavior |
|--------------------------|------------------------|----------|
| false | false | Core LangGraph workflow |
| true | false | LangGraph with stage routing |
| false | true | LangGraph with specialists |
| true | true | LangGraph with stage routing + specialists |

## Usage

### Basic Usage
```python
# Make API request to /api/agent/projects/{project_id}/chat
# Router uses LangGraph adapter by default
```

### With Stage Routing
```python
AAA_ENABLE_STAGE_ROUTING=true

# System will:
# - Classify stage (clarify, propose, adr, validate, pricing, iac, export)
# - Retry on ERROR: outputs
# - Propose next steps if no artifacts persisted
```

### With Multi-Agent
```python
AAA_ENABLE_MULTI_AGENT=true

# System will:
# - Route through supervisor
# - Select appropriate specialist (ADR, Validation, Pricing, IaC)
# - Use narrowed toolset for focused tasks
```

## Graph Workflows

### Standard Workflow
```
Entry → Load State → Classify Stage → Build Summary → [Extract Requirements | Clarify Stage Worker | Export Stage Worker | Build Research → Research Worker (`propose_candidate`) → Build Mind Map Guidance → Architecture Planner / Validate Stage Worker / Cost Stage Worker / IaC Stage Worker / Run Agent] → Persist Messages → [End | Postprocess → Apply Updates] → End
```

### Validate-Stage Worker
```
... → Build Research → Build Mind Map Guidance → Validate Stage Worker
                                                     ├─ deterministic WAF evaluator
                                                     ├─ WAF findings worker
                                                     └─ aaa_record_validation_results payload
                                                         → Persist Messages → Postprocess → Apply Updates
```

- The validate worker bypasses the generic stage-aware agent for `validate` turns.
- It returns either:
  - a validation-tool `AAA_STATE_UPDATE` payload for findings/checklist deltas, or
  - a deterministic no-op response when checklist/evidence input is insufficient or no actionable gaps remain.

### Cost-Stage Worker
```
... → Build Research → Build Mind Map Guidance → Cost Stage Worker
                                                     ├─ prepare_cost_estimator_handoff
                                                     ├─ cost_estimator_node
                                                     └─ aaa_record_cost_estimate / deterministic pricing path
                                                         → Persist Messages → Postprocess → Apply Updates
```

- Pricing turns now bypass the generic agent path and always reuse the dedicated cost estimator runtime when the stage or routing heuristics indicate a cost request.
- The worker preserves the existing `aaa_record_cost_estimate` update flow, so deterministic `costEstimates` still land through the standard postprocess/apply pipeline instead of duplicating persistence logic.

### IaC-Stage Worker
```
... → Build Research → Build Mind Map Guidance → IaC Stage Worker
                                                     ├─ prepare_iac_generator_handoff
                                                     ├─ iac_generator_node
                                                     └─ aaa_record_iac_artifacts
                                                         → Persist Messages → Postprocess → Apply Updates
```

- IaC turns now bypass the generic graph agent path and reuse the dedicated IaC handoff + generator runtime.
- The worker preserves the existing `aaa_record_iac_artifacts` update flow, so `iacArtifacts` still land through the standard postprocess/apply pipeline instead of introducing new persistence semantics.

### Architecture Synthesizer
```
... → Build Research → Research Worker → Build Mind Map Guidance → Prepare Architecture Handoff
                                                             → Architecture Planner
                                                                 ├─ synthesizer output contract (1 candidate by default)
                                                                 ├─ evidence packet / WAF / mindmap delta prompts
                                                                 └─ architecture_synthesis_execution_artifact
                                                                     → Persist Messages → Postprocess → Apply Updates
```

- The synthesizer seam remains review-first: it still relies on the existing postprocess + pending-change-set path to persist candidate architectures and diagrams.

### Clarify-Stage Worker
```
... → Build Summary → Clarify Stage Worker
                       ├─ open clarification questions present?
                       │   ├─ yes → clarification resolution worker
                       │   │          ├─ structured requirement/question/assumption updates
                       │   │          └─ pending change set for approval
                       │   └─ no  → clarification planner worker
                       │              ├─ canonical requirements / ambiguities
                       │              ├─ WAF gaps + mindmap gaps
                       │              └─ grouped clarification questions
                       └─ Persist Messages → End
```

- Clarify turns stay approval-first: planning remains read-only, while answer-resolution turns now record a pending change set instead of mutating canonical state directly.

### Manage-ADR Worker
```
... → Build Research → Build Mind Map Guidance → Manage ADR Stage Worker
                                                     ├─ ADR drafter worker (structured JSON contract)
                                                     ├─ ADR management worker
                                                     └─ pending change set with _adrLifecycle command
                                                         → Persist Messages → End
```

- ADR turns remain approval-first: the stage worker records a reviewable change set, and approval-time merge logic applies create/supersede lifecycle commands through the deterministic ADR lifecycle service.

### Export-Stage Worker
```
... → Build Summary → Export Stage Worker
                       ├─ aaa_export_state tool
                       └─ packaged AAA_EXPORT payload with traceability + mindmap coverage scorecard evidence
                           → Persist Messages → End
```

- Export turns now bypass the generic agent path and use the existing AAA export tool directly.
- The export payload now includes a `mindmapCoverageScorecard` with all 13 top-level topics plus packaged artifact evidence.

### With Stage Routing
```
... → Postprocess → Classify Stage → [Check Retry]
                                     ├─ retry → Retry Prompt → End (user clarifies)
                                     └─ continue → Apply Updates → Propose Next Step → End
```

### With Multi-Agent
```
... → Build Summary → Supervisor → [Route to Specialist]
                                  ├─ ADR → ADR Specialist ─┐
                                  ├─ Validation → Validation Specialist ─┤
                                  ├─ Pricing → Pricing Specialist ─┤
                                  ├─ IaC → IaC Specialist ─┤
                                  └─ General → Run Agent ─┘
                                                            └─ Persist Messages → ...
```

## Code Structure

```
backend/app/agents_system/langgraph/
├── __init__.py
├── state.py                    # GraphState TypedDict
├── adapter.py                  # execute_project_chat() interface
├── graph_factory.py            # Project chat graph
    └── nodes/
        ├── context.py              # Load state, build summary
        ├── extract_requirements.py # Dedicated requirements extraction stage worker
        ├── export.py               # Dedicated export stage worker
        ├── iac_generator.py        # Dedicated IaC stage worker + generator node
        ├── validate.py             # Dedicated validate-stage worker
        ├── agent.py                # Agent execution node
    ├── agent_native.py         # Graph-native agent loop
    ├── postprocess.py          # Extract updates, derive logs
    ├── persist.py              # Save messages, apply updates
    ├── stage_routing.py        # Stage classification, retry
    └── multi_agent.py          # Supervisor, specialists
```

## Testing

### Unit Tests
```bash
# Test graph compilation
uv run python -m pytest backend/tests/agents_system/test_langgraph_skeleton.py

# Test stage routing
uv run python -m pytest backend/tests/agents_system/test_stage_routing.py

# Test specialist routing
uv run python -m pytest backend/tests/agents_system/test_multi_agent.py
```

### Integration Tests
```bash
# Test with actual project
curl -X POST http://localhost:8000/api/agent/projects/{project_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "We need 99.9% availability"}'
```

## Rollout

Recommended enablement order:
1. Start with core LangGraph workflow (both flags `false`)
2. Enable `AAA_ENABLE_STAGE_ROUTING=true` when stage transitions need stricter control
3. Enable `AAA_ENABLE_MULTI_AGENT=true` when specialist routing is required

## Performance Considerations

- **Latency**: LangGraph adds minimal overhead (<100ms) for state management
- **Memory**: Graph state is kept in memory during execution
- **Checkpointing**: Optional for conversation persistence (not yet implemented)
- **Parallelization**: Specialists can potentially run in parallel (future optimization)

## Troubleshooting

### Graph execution fails
- Check logs for specific node failures
- Verify all dependencies installed (`langgraph>=0.2.0`)
- Ensure OpenAI API key configured

### Stage routing not working
- Verify `AAA_ENABLE_STAGE_ROUTING=true`
- Check keyword classification in logs
- Review stage classification logic

### Specialists not routing correctly
- Verify `AAA_ENABLE_MULTI_AGENT=true`
- Check supervisor routing logic in logs
- Ensure specialist tools available

## Future Enhancements

- [ ] Checkpointing for conversation persistence
- [ ] Parallel specialist execution
- [ ] Custom stage routing rules
- [ ] Specialist prompt customization
- [ ] Performance monitoring and metrics
- [ ] A/B testing framework

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Migration Plan](../../../../docs/LANGGRAPH_MIGRATION_PLAN.md)
- [System Architecture](../../../../docs/SYSTEM_ARCHITECTURE.md)
