# Documentation Home

This repository uses a domain-first documentation structure with a strict audience split.

## Audience Lanes

- **Agent lane (default for AI agents)**: `/docs/agents`
- **Human lane (comprehensive)**: domain folders under `/docs`

Agents should use `/docs/agents` as primary context and should not rely on human-comprehensive docs by default.

## Governance

- Documentation policy and update rules: [`/docs/operations/DOCUMENTATION_GOVERNANCE.md`](./operations/DOCUMENTATION_GOVERNANCE.md)
- Migration tracker and move/archive status: [`/docs/operations/DOC_MIGRATION_INDEX.md`](./operations/DOC_MIGRATION_INDEX.md)

## Domain Index (Human Lane)

### Architecture

- [`architecture/README.md`](./architecture/README.md)
- [`architecture/project-overview.md`](./architecture/project-overview.md)
- [`architecture/system-architecture.md`](./architecture/system-architecture.md)
- [`architecture/multi-agent-architecture.md`](./architecture/multi-agent-architecture.md)
- [`architecture/arch_mindmap.json`](./architecture/arch_mindmap.json)

### Backend

- [`backend/README.md`](./backend/README.md)
- [`backend/BACKEND_REFERENCE.md`](./backend/BACKEND_REFERENCE.md)
- [`backend/TESTING_DEPENDENCY_INJECTION.md`](./backend/TESTING_DEPENDENCY_INJECTION.md)

### Frontend

- [`frontend/README.md`](./frontend/README.md)
- [`frontend/FRONTEND_REFERENCE.md`](./frontend/FRONTEND_REFERENCE.md)
- [`frontend/UX_IDE_WORKFLOW.md`](./frontend/UX_IDE_WORKFLOW.md)
- [`frontend/UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md`](./frontend/UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md)

### Operations

- [`operations/README.md`](./operations/README.md)
- [`operations/history/README.md`](./operations/history/README.md)
- [`operations/DEVELOPMENT_GUIDE.md`](./operations/DEVELOPMENT_GUIDE.md)
- [`waf_normalization_implementation/README.md`](./waf_normalization_implementation/README.md)

## Agent Lane Index

- [`agents/README.md`](./agents/README.md)
- [`agents/AGENT_DOC_TEMPLATE.md`](./agents/AGENT_DOC_TEMPLATE.md)
- [`agents/project-overview.agent.md`](./agents/project-overview.agent.md)
- [`agents/system-architecture.agent.md`](./agents/system-architecture.agent.md)
- [`agents/multi-agent-architecture.agent.md`](./agents/multi-agent-architecture.agent.md)

## Historical / In-Progress Material

These files are currently in migration and may be archived or split:

- Implementation completion summaries
- Legacy migration plans
- Review and analysis dumps
- Historical phase/spec artifacts (moved to operations history)

See the live status table in [`operations/DOC_MIGRATION_INDEX.md`](./operations/DOC_MIGRATION_INDEX.md).

Primary history buckets:

- [`operations/history/implementation-history/`](./operations/history/implementation-history/)
- [`operations/history/plans-and-phases/`](./operations/history/plans-and-phases/)
- [`operations/history/reviews/`](./operations/history/reviews/)
- [`operations/history/analysis/`](./operations/history/analysis/)

## Compatibility Pointers (Legacy Paths)

Temporary root-level pointer files are kept for backward compatibility during migration.

Canonical references should use domain and history paths listed above.

Current legacy pointers are tracked in [`operations/DOC_MIGRATION_INDEX.md`](./operations/DOC_MIGRATION_INDEX.md).

## Allowed Documentation Exceptions (outside `/docs`)

These technical READMEs are intentionally local to code and must stay discoverable from this index:

- [`/backend/app/agents_system/langgraph/README.md`](../backend/app/agents_system/langgraph/README.md)
- [`/backend/app/kb/README.md`](../backend/app/kb/README.md)

Add new exceptions only when code-near maintainability clearly benefits.

---

**Status**: Active  
**Last Updated**: 2026-02-15  
**Owner**: Engineering
