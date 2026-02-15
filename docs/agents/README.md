# Agent Documentation

## Purpose

This folder contains concise, low-token documents intended for AI agents.

## Rules

- Keep documents short, direct, and task-oriented.
- Prefer checklists, constraints, and decision summaries over narrative text.
- Do not duplicate large human documentation sections.
- Link to human docs only for maintainers; agents should not use human docs as default context.

## Required Format

Every agent document should include:

- `Purpose`
- `Current State`
- `Do / Don't`
- `Decision Summary`
- `Update Triggers`

Use template: `/docs/agents/AGENT_DOC_TEMPLATE.md`.

## Canonical Agent Entry Points

- `/docs/agents/project-overview.agent.md`
- `/docs/agents/system-architecture.agent.md`
- `/docs/agents/multi-agent-architecture.agent.md`

---

**Status**: Active  
**Last Updated**: 2026-02-15  
**Owner**: Engineering
