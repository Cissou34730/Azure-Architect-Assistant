# Multi-Agent Architecture (Agent)

## Purpose

Low-token summary of routing and specialist behavior in the AAA agent system.

## Current State

- Agent orchestration is implemented in the LangGraph flow under `backend/app/agents_system/langgraph`.
- Routing selects specialized behavior before defaulting to the general/main agent.
- Specialized paths cover architecture planning, IaC generation, SaaS advisory, and cost estimation.
- Routing behavior is stage- and keyword-aware and designed to preserve project-state continuity.

## Do / Don't

### Do

- Treat routing rules and specialist boundaries as primary behavior contract.
- Update this file when routing priority or specialist responsibilities change.
- Keep this file compact and operational.

### Don't

- Include long design rationale or migration history.
- Duplicate full prompt specifications.

## Decision Summary

- Use specialist-first routing for high-value tasks, fallback to main agent for general guidance.
- Keep routing deterministic and explicit to reduce ambiguity.

## Update Triggers

Update this file when:

- routing priority/order changes
- new specialist agent is added/removed
- handoff contract or required preconditions change

## Metadata

- Status: Active
- Last Updated: 2026-02-15
- Owner: Engineering
