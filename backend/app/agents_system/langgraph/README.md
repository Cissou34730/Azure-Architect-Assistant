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
- `nodes/agent.py` - Execute stage-aware agent node
- `nodes/postprocess.py` - Extract updates, derive MCP logs
- `nodes/persist.py` - Save messages and apply state updates

**Flow:** load_state → build_summary → run_agent → persist_messages → postprocess → apply_updates

### Graph-Native Tool Loop
**ToolNode-based execution**

- `nodes/agent_native.py` - LangGraph-native agent execution
- Uses `ChatOpenAI.bind_tools()` + `ToolNode` for tool loop
- Message-based trace (AIMessage, ToolMessage)
- Respects iteration limits and timeouts

### Stage Routing + Retry
**Explicit stage transitions and error handling**

- `nodes/stage_routing.py` - Stage classification and retry logic
- ProjectStage enum: clarify, propose_candidate, manage_adr, validate, pricing, iac, export
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
Entry → Load State → Build Summary → Run Agent → Persist Messages → Postprocess → Apply Updates → End
```

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
├── graph_factory.py            # Basic graph
├── graph_factory_advanced.py   # Advanced graph
└── nodes/
    ├── context.py              # Load state, build summary
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
