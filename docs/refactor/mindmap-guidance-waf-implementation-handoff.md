# Mindmap Guidance + WAF-Safe Orchestration — Implementation Handoff

## Goal
Implement non-blocking mindmap-guided architecture coaching (from `docs/architecture/arch_mindmap.json`) while preserving WAF checklist follow-up reliability.

## Scope
- Included: advisory mindmap guidance, top-level coverage tracking, deterministic directive merge, WAF non-regression safeguards, tests.
- Excluded: subtopic/node-id tracking, major routing redesign, frontend UX changes.

## Stage Policy
- Discovery-heavy mindmap: `clarify`, `propose_candidate`.
- Validation protection: `validate` keeps WAF checklist persistence and evidence handling dominant.
- All stages: mindmap guidance remains advisory and non-blocking.

## Task-by-Task Execution

| ID | Task | Depends On | Files | Subagent Applicable | Estimate | Risk | Rollback | Acceptance |
|---|---|---|---|---|---:|---|---|---|
| T1.1 | Define directive precedence contract | - | `backend/app/agents_system/langgraph/nodes/research.py`, `backend/app/agents_system/langgraph/nodes/agent_native.py` | Yes | 0.5d | Medium | Revert to prior concatenation | Explicit stage-aware precedence map exists |
| T1.2 | Define `mindmap_guidance` payload schema | T1.1 | `backend/app/agents_system/langgraph/nodes/research.py`, `backend/app/agents_system/langgraph/state.py` | Yes | 0.5d | Low | Fallback to text-only gaps | Typed payload available in graph state |
| T2.1 | Add dedicated mindmap guidance step in advanced graph | T1.2 | `backend/app/agents_system/langgraph/graph_factory_advanced.py` | Yes | 1d | Medium | Remove node/edge and revert routing | `mindmap_guidance` is explicitly carried before agent execution |
| T2.2 | Implement precedence-based directive assembly | T2.1 | `backend/app/agents_system/langgraph/nodes/agent_native.py` | Yes | 1d | High | Feature-flag/fallback to previous assembly | Discovery favors mindmap; validation favors WAF operations |
| T3.1 | Refine top-level coverage confidence | T2.2 | `backend/app/agents_system/services/mindmap_loader.py`, `backend/app/agents_system/services/iteration_logging.py` | Yes | 1d | Medium | Restore previous thresholds | Reduced false uncovered-topic prompts |
| T3.2 | Add prompt smoothness controls (budget/dedup) | T2.2 | `backend/app/agents_system/services/iteration_logging.py`, `backend/app/agents_system/langgraph/nodes/persist.py` | Yes | 0.5d | Low | Disable budget/dedup branch | Prompt cap and dedup enforced |
| T4.1 | Add WAF non-regression safeguards in merge/persist path | T2.2 | `backend/app/agents_system/langgraph/nodes/agent.py`, `backend/app/agents_system/langgraph/nodes/postprocess.py`, `backend/app/agents_system/langgraph/nodes/persist.py`, `backend/app/agents_system/checklists/engine.py`, `backend/app/agents_system/services/project_context.py` | Partial (mapping/research yes; final merge logic by primary implementer) | 1d | High | Revert to pre-change WAF path | Checklist updates/follow-up still persist under mindmap-heavy turns |
| T5.1 | Add stage-precedence unit tests | T2.2 | `backend/tests/agents_system/` | Yes | 0.5d | Low | N/A | Tests fail on precedence regressions |
| T5.2 | Add WAF persistence regression tests | T4.1 | `backend/tests/agents_system/` | Yes | 0.5d | Low | N/A | Tests fail when WAF follow-up weakens |
| T5.3 | Execute backend validation pipeline | T5.1, T5.2 | VS Code tasks | No | 0.25d | Medium | Revert offending commits | Backend unit + full backend tests pass |

## Parallelization
- Lane A: T2.1 + T3.1.
- Lane B: T5.1 can start once T2.2 stabilizes.
- Sequential blockers: T1.1 → T1.2 → T2.1/T2.2 → T4.1 → T5.2 → T5.3.

## Test IDs
- `MM-WAF-PRECEDENCE-001`: discovery/research prioritizes mindmap prompts.
- `MM-WAF-PRECEDENCE-002`: validation/checklist preserves WAF-first behavior.
- `MM-NONBLOCK-003`: mindmap guidance remains advisory.
- `WAF-NOREG-004`: checklist updates persist during mindmap-guided turns.
- `WAF-NOREG-005`: failed lookup clarification path preserved.
- `PROMPT-SMOOTH-006`: prompt budget/dedup enforced.

## Current Implementation Status
- Implemented in this iteration: T1.1, T1.2, T2.1, T2.2, T3.1, T3.2, T4.1, T5.1, T5.2.
- Remaining: T5.3 is blocked by an existing unrelated test import failure in `backend/tests/test_orchestrator_unit.py` (`StepName` import).
