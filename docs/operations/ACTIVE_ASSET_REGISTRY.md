# Active Asset Registry (Agents, Prompts, Skills)

## Purpose

Provide a single index of active automation assets, ownership, and maintenance status.

## Status Values

- `active`: in regular use and maintained.
- `review-needed`: active but pending quality/ownership review.
- `deprecated-candidate`: likely obsolete; pending maintainer decision.

## Agent Assets

| Asset | Path | Owner | Status | Review Cadence |
|---|---|---|---|---|
| grumpy | `/.github/agents/grumpy.agent.md` | Engineering | review-needed | Quarterly |
| react.perf | `/.github/agents/react.perf.agent.md` | Frontend | review-needed | Quarterly |
| refactor.backend | `/.github/agents/refactor.backend.agent.md` | Backend | active | Quarterly |
| refactor.frontend | `/.github/agents/refactor.frontend.agent.md` | Frontend | active | Quarterly |
| speckit.* agents | `/.github/agents/speckit.*.agent.md` | Engineering | active | Monthly |

## Prompt Assets

| Asset Group | Path Pattern | Owner | Status | Review Cadence |
|---|---|---|---|---|
| speckit prompts | `/.github/prompts/speckit.*.prompt.md` | Engineering | active | Monthly |
| unified state tracking | `/.github/prompts/plan-unifiedStateTracking.prompt.md` | Engineering | review-needed | Quarterly |

## Skill Assets

| Asset Group | Path Pattern | Owner | Status | Review Cadence |
|---|---|---|---|---|
| built-in curated skills | `/.github/skills/*` | Engineering | active | Quarterly |

## Quality Baseline

For active assets, maintain:

1. Clear purpose in first section.
2. Explicit scope and non-goals.
3. Review cadence and owner in this registry.
4. No broken internal file references.

## Deprecation Workflow

1. Mark as `deprecated-candidate` in this registry.
2. Open issue to evaluate migration/removal.
3. Remove only after maintainer approval.

---

**Status**: Active  
**Last Updated**: 2026-02-22  
**Owner**: Engineering