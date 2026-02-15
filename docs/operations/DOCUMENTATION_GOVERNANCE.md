# Documentation Governance

## Purpose

This document defines how documentation is organized and maintained in this repository.

## Scope and Exceptions

- Canonical project documentation lives under `/docs`.
- Technical, code-near `README.md` files are allowed outside `/docs` as **exceptions** when they improve local maintainability (for example inside backend modules).
- Exception docs must be discoverable from `/docs/README.md`.

## Audience Split (Mandatory)

The repository maintains two documentation lanes:

- **Agent lane**: concise, low-token documentation in `/docs/agents`.
- **Human lane**: comprehensive documentation in domain folders (for example `/docs/backend`, `/docs/architecture`, `/docs/operations`).

### Hard Boundary

- AI agents must use `/docs/agents` as first-class documentation.
- Human-comprehensive documents must not be used as default context for agents.
- When a topic needs both views, maintain both files and keep them aligned.

## Required Updates on Change

A significant code change (behavior, API, architecture, IaC, operational workflow) is complete only when documentation is updated in both lanes:

1. Update or create the concise agent document in `/docs/agents`.
2. Update the detailed human document in the relevant domain folder.
3. Update `/docs/README.md` navigation and links.
4. If content is moved or deprecated, update `/docs/operations/DOC_MIGRATION_INDEX.md`.

## Domain-First Structure

Top-level documentation organization is domain-first.

- `/docs/architecture`
- `/docs/backend`
- `/docs/frontend`
- `/docs/operations`
- `/docs/agents`

During migration, legacy root files can remain temporarily but must be tracked in migration index.

## Lifecycle and Archiving

- Active docs remain in domain folders.
- Historical implementation reports, old plans, and review dumps should be moved to archive locations.
- Keep index pointers in active docs to preserve traceability.

## Quality Gates

Before merging changes with documentation impact:

- Links added/modified in docs resolve correctly.
- Agent and human documents do not conflict.
- Stale or superseded documents are marked or migrated.
- `/docs/README.md` remains accurate.

## Metadata Guidelines

For documents maintained over time, include:

- `Status`: Draft | Active | Historical
- `Last Updated`: `YYYY-MM-DD`
- `Owner`: team or role

---

**Status**: Active  
**Last Updated**: 2026-02-15  
**Owner**: Engineering
