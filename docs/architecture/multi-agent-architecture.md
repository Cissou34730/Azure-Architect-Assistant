# Multi-Agent Architecture

## Purpose

Comprehensive human-oriented reference for multi-agent routing, specialist responsibilities, and implementation touchpoints.

## Current architecture

The Azure Architect Assistant uses LangGraph orchestration with stage-aware routing to specialized sub-agents.

### Routing priority (highest to lowest)

1. IaC Generator
2. Architecture Planner
3. SaaS Advisor
4. Cost Estimator
5. Main Agent (default fallback)

### Routing principles

- Use explicit intent and stage-aware checks before handoff.
- Keep specialist responsibilities narrow and deterministic.
- Preserve project-state continuity across handoffs.
- Fall back to main agent if specialist preconditions are not met.

## Specialist responsibilities

### Architecture Planner

- Handles complex architecture design requests.
- Produces architecture proposals with NFR considerations and diagram intent.
- Used when request complexity indicates architecture decomposition.

### IaC Generator

- Handles Terraform/Bicep generation requests.
- Requires a sufficiently finalized architecture context.
- Produces production-oriented IaC artifacts with parameterization patterns.

### SaaS Advisor

- Handles multi-tenant/SaaS-specific architecture questions.
- Focuses on tenant model and isolation strategy guidance.

### Cost Estimator

- Handles pricing and cost-estimation requests.
- Uses finalized architecture context for more grounded estimates.

### Main Agent

- Handles generic guidance and orchestration.
- Coordinates context and fallback behavior for the full flow.

## Implementation touchpoints

- `backend/app/agents_system/langgraph/graph_factory.py`
- `backend/app/agents_system/langgraph/state.py`
- `backend/app/agents_system/langgraph/nodes/stage_routing.py`
- Specialist nodes in `backend/app/agents_system/langgraph/nodes/`
- Prompts in `backend/config/prompts/`

## Validation

Relevant scenario tests and integration scripts are located in `scripts/` (for example Phase 3 scenario suites).

## Historical design notes

The earlier Phase 2 design narrative remains available in legacy documents and should be treated as historical context, not the primary contract.

---

**Status**: Active  
**Last Updated**: 2026-02-15  
**Owner**: Engineering
