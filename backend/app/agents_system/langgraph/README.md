# LangGraph Migration - Implementation Guide

This document describes the LangGraph migration from LangChain ReAct to LangGraph state-based orchestration.

## Overview

The LangGraph migration replaces the legacy LangChain `AgentExecutor` with LangGraph's state-based workflow system, providing:
- Explicit, testable workflow control
- Clear branching rules for architect choices and retries
- Foundation for multi-agent orchestration
- Better stage transition handling

## Architecture

### Phase 1-3: Foundation (Completed)
**Basic LangGraph integration with feature flag**

- Package structure: `backend/app/agents_system/langgraph/`
- GraphState TypedDict for workflow state
- Node-based orchestration wrapping existing agent
- Feature flag for safe rollout: `AAA_USE_LANGGRAPH`

**Nodes:**
- `nodes/context.py` - Load project state and build context
- `nodes/agent.py` - Execute agent (wraps legacy runner)
- `nodes/postprocess.py` - Extract updates, derive MCP logs
- `nodes/persist.py` - Save messages and apply state updates

**Flow:** load_state → build_summary → run_agent → persist_messages → postprocess → apply_updates

### Phase 4: Graph-Native Tool Loop (Completed)
**Replace LangChain AgentExecutor with LangGraph ToolNode**

- `nodes/agent_native.py` - LangGraph-native agent execution
- Uses `ChatOpenAI.bind_tools()` + `ToolNode` for tool loop
- Message-based trace (AIMessage, ToolMessage)
- Respects iteration limits and timeouts

### Phase 5: Stage Routing + Retry (Completed)
**Explicit stage transitions and error handling**

- `nodes/stage_routing.py` - Stage classification and retry logic
- ProjectStage enum: clarify, propose_candidate, manage_adr, validate, pricing, iac, export
- Retry loop for ERROR: prefixed outputs
- Always propose next steps if no artifacts persisted
- Feature flag: `AAA_ENABLE_STAGE_ROUTING`

### Phase 6: Multi-Agent Specialists (Completed)
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
# Enable LangGraph (Phase 3+)
AAA_USE_LANGGRAPH=false  # Set to true to use LangGraph instead of legacy

# Enable Stage Routing (Phase 5)
AAA_ENABLE_STAGE_ROUTING=false  # Set to true for explicit stage transitions

# Enable Multi-Agent (Phase 6)
AAA_ENABLE_MULTI_AGENT=false  # Set to true for specialist routing
```

### Feature Flag Combinations

| AAA_USE_LANGGRAPH | AAA_ENABLE_STAGE_ROUTING | AAA_ENABLE_MULTI_AGENT | Behavior |
|-------------------|--------------------------|------------------------|----------|
| false | * | * | Legacy LangChain path |
| true | false | false | Phase 2/3: Basic LangGraph |
| true | true | false | Phase 5: With stage routing |
| true | false | true | Phase 6: With specialists |
| true | true | true | Full: Stage routing + specialists |

## Usage

### Basic Usage (Phase 3)
```python
# Enable LangGraph in .env
AAA_USE_LANGGRAPH=true

# Make API request to /api/agent/projects/{project_id}/chat
# Router automatically uses LangGraph adapter
```

### With Stage Routing (Phase 5)
```python
# Enable LangGraph + Stage Routing
AAA_USE_LANGGRAPH=true
AAA_ENABLE_STAGE_ROUTING=true

# System will:
# - Classify stage (clarify, propose, adr, validate, pricing, iac, export)
# - Retry on ERROR: outputs
# - Propose next steps if no artifacts persisted
```

### With Multi-Agent (Phase 6)
```python
# Enable LangGraph + Multi-Agent
AAA_USE_LANGGRAPH=true
AAA_ENABLE_MULTI_AGENT=true

# System will:
# - Route through supervisor
# - Select appropriate specialist (ADR, Validation, Pricing, IaC)
# - Use narrowed toolset for focused tasks
```

## Graph Workflows

### Standard Workflow (Phase 2/3)
```
Entry → Load State → Build Summary → Run Agent → Persist Messages → Postprocess → Apply Updates → End
```

### With Stage Routing (Phase 5)
```
... → Postprocess → Classify Stage → [Check Retry]
                                     ├─ retry → Retry Prompt → End (user clarifies)
                                     └─ continue → Apply Updates → Propose Next Step → End
```

### With Multi-Agent (Phase 6)
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
├── graph_factory.py            # Basic graph (Phase 2/3)
├── graph_factory_advanced.py   # Advanced graph (Phase 4-6)
└── nodes/
    ├── context.py              # Load state, build summary
    ├── agent.py                # Legacy agent wrapper (Phase 2/3)
    ├── agent_native.py         # Graph-native agent (Phase 4)
    ├── postprocess.py          # Extract updates, derive logs
    ├── persist.py              # Save messages, apply updates
    ├── stage_routing.py        # Stage classification, retry (Phase 5)
    └── multi_agent.py          # Supervisor, specialists (Phase 6)
```

## Testing

### Unit Tests
```bash
# Test graph compilation
pytest backend/tests/agents_system/test_langgraph_skeleton.py

# Test stage routing
pytest backend/tests/agents_system/test_stage_routing.py

# Test specialist routing
pytest backend/tests/agents_system/test_multi_agent.py
```

### Integration Tests
```bash
# Test with actual project
curl -X POST http://localhost:8000/api/agent/projects/{project_id}/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "We need 99.9% availability"}'
```

## Migration Path

### Recommended Rollout
1. **Phase 3**: Enable `AAA_USE_LANGGRAPH=true` for single project
2. **Validate**: Compare responses with legacy path
3. **Phase 5**: Add `AAA_ENABLE_STAGE_ROUTING=true` for better stage transitions
4. **Phase 6**: Add `AAA_ENABLE_MULTI_AGENT=true` for specialist routing
5. **Production**: Roll out to all projects
6. **Deprecate**: Remove legacy LangChain path

### Rollback
If issues arise, simply set `AAA_USE_LANGGRAPH=false` to revert to legacy behavior.

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
- [Migration Plan](../../docs/LANGGRAPH_MIGRATION_PLAN.md)
- [System Architecture](../../docs/SYSTEM_ARCHITECTURE.md)
