# Documentation Migration Index

## Purpose

Track migration of legacy or root-level docs into the target domain-first structure and the agent/human split.

## Status Categories

- `keep`: stays where it is (already aligned)
- `move`: must be moved to a target folder
- `split`: one file should become agent + human variants
- `archive`: move to archive and leave pointer
- `review`: owner decision required

## Tracking Table

| Source | Action | Target | Owner | Status |
|---|---|---|---|---|
| `/docs/PROJECT_OVERVIEW.md` | split | `/docs/agents/project-overview.agent.md` + `/docs/architecture/project-overview.md` | Engineering | completed |
| `/docs/SYSTEM_ARCHITECTURE.md` | split | `/docs/agents/system-architecture.agent.md` + `/docs/architecture/system-architecture.md` | Engineering | completed |
| `/docs/MULTI_AGENT_ARCHITECTURE.md` | split | `/docs/agents/multi-agent-architecture.agent.md` + `/docs/architecture/multi-agent-architecture.md` | Engineering | completed |
| `/docs/P0_IMPLEMENTATION_COMPLETE.md` | archive | `/docs/operations/history/implementation-history/` + pointer in `/docs/operations/history/README.md` | Engineering | completed |
| `/docs/P1_IMPLEMENTATION_COMPLETE.md` | archive | `/docs/operations/history/implementation-history/` + pointer in `/docs/operations/history/README.md` | Engineering | completed |
| `/docs/PHASE5_COMPLETION_SUMMARY.md` | archive | `/docs/operations/history/implementation-history/` + pointer in `/docs/operations/history/README.md` | Engineering | completed |
| `/docs/reviews/*` | archive | `/docs/operations/history/reviews/` + pointer index | Engineering | completed |
| `/docs/FRONTEND_REDESIGN_COMPLETE.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/FRONTEND_REDESIGN_PLAN.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/HEADER_PROJECT_SELECTOR_PLAN.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/IDE_WORKSPACE_TABS_SPEC.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/LANGGRAPH_MIGRATION_COMPLETE.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/LANGGRAPH_MIGRATION_PLAN.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/PERFORMANCE_REMEDIATION_PLAN.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/PHASE1_COMPLETION_SUMMARY.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/PHASE1_PROMPT_ANALYSIS.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/PHASE3_OPTIONAL_AGENTS.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/plan-normalizeWafChecklistToDb.prompt.prompt.md` | archive | `/docs/operations/history/plans-and-phases/` + pointer | Engineering | completed |
| `/docs/BACKEND_REFERENCE.md` | move | `/docs/backend/BACKEND_REFERENCE.md` + pointer | Engineering | completed |
| `/docs/FRONTEND_REFERENCE.md` | move | `/docs/frontend/FRONTEND_REFERENCE.md` + pointer | Engineering | completed |
| `/docs/UX_IDE_WORKFLOW.md` | move | `/docs/frontend/UX_IDE_WORKFLOW.md` + pointer | Engineering | completed |
| `/docs/UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md` | move | `/docs/frontend/UNIFIED_UX_IMPLEMENTATION_CHECKLIST.md` + pointer | Engineering | completed |
| `/docs/DEVELOPMENT_GUIDE.md` | move | `/docs/operations/DEVELOPMENT_GUIDE.md` + pointer | Engineering | completed |
| `/docs/INDEXER_PERFORMANCE_ANALYSIS.json` | archive | `/docs/operations/history/analysis/INDEXER_PERFORMANCE_ANALYSIS.json` + pointer | Engineering | completed |
| `/docs/arch_mindmap.json` | move | `/docs/architecture/arch_mindmap.json` + pointer | Engineering | completed |
| `/backend/app/agents_system/langgraph/README.md` | keep | local exception + link from `/docs/README.md` | Engineering | planned |
| `/backend/app/kb/README.md` | keep | local exception + link from `/docs/README.md` | Engineering | planned |

## Notes

- This index is the single migration tracker for documentation moves.
- Update this table in the same pull request as any move/split/archive operation.

---

**Status**: Active  
**Last Updated**: 2026-02-15  
**Owner**: Engineering
