# Question Generation Split Plan

> Status: In progress — Q1.1 and Q1.2 complete  
> Date: 2026-05-06  
> Scope: Clarify-stage question quality, internal architect question feature, WAF and mindmap coverage

## Goal

Improve generated questions by separating two different jobs that are currently mixed together:

1. Customer clarification questions: questions addressed to the customer to clarify requirements, expose discrepancies, and resolve inconsistencies in the inputs.
2. Architect solution questions: internal questions for the architecture team to answer while building the solution, explicitly covering WAF checklist gaps and architecture mindmap gaps.

The customer-facing set must stop drifting into solution design too early. The internal set must preserve the useful design pressure of the current questions, but move it into a dedicated feature with traceability to WAF and mindmap coverage.

## Codebase Analysis

The clarify stage is already implemented as a dedicated backend stage worker, not only as a generic agent prompt:

- `backend/app/agents_system/langgraph/nodes/clarify.py` short-circuits `next_stage == "clarify"` into `ClarificationPlannerWorker.plan_questions(...)`, formats the answer, and emits `structured_payload` of type `clarification_questions`.
- `backend/app/features/agent/application/clarification_planner_worker.py` builds planner input from canonical requirements, ambiguity markers, WAF gaps, mindmap gaps, and prior clarification history.
- `backend/config/prompts/clarification_planner.yaml` currently instructs the LLM to produce the top 3 to 5 "decision-blocking" architecture questions. This explains why generated questions are useful for solution design but too technical for customer requirement clarification.
- `backend/app/features/agent/contracts/clarification_planner.py` has one output shape: `questionGroups`. There is no first-class distinction between customer clarification and internal architect questions.
- `backend/app/agents_system/contracts/workflow_result.py` exposes only one structured payload type for this path: `ClarificationQuestionsPayload` with `type: "clarification_questions"`.
- `frontend/src/features/knowledge/types/api-kb.ts` only models the basic clarification fields and currently does not include the backend's optional `affectedDecision`, `defaultAssumption`, and `riskIfWrong` fields.
- `frontend/src/features/projects/components/unified/ChatReviewPanelSections.tsx` renders a single clarification form and sends all answers back as customer clarification answers.
- Existing backend tests in `backend/tests/test_clarification_planner_worker.py` and `backend/tests/test_agent_runtime_clarify.py` validate the single-set behavior, top-5 filtering, history deduplication, and formatting.
- Existing eval/reporting paths already have stage-specific clarify checks, including required `questionGroups` detection in `backend/tests/eval`.
- WAF data is available through `wafChecklist.items`; unresolved checklist items are already extracted by `_build_waf_gaps(...)`.
- Mindmap coverage is available from graph state `mindmap_coverage` or project state `mindMapCoverage`; uncovered or partial topics are already extracted by `_build_mindmap_gaps(...)`.
- ProjectState artifact families are already decomposed through `backend/app/features/projects/infrastructure/project_state_components_repository.py`, so internal architect questions should be introduced as a durable artifact family from the first implementation slice rather than as transient chat-only payloads.
- The quality gate already summarizes WAF and mindmap coverage through `backend/app/features/projects/application/quality_gate_service.py` and the frontend `QualityGateTab`, making it a natural place to surface open internal architect questions and answer status.

## Product Behavior

### Customer Clarification Questions

These are addressed to the customer. They should ask for missing, contradictory, or ambiguous requirement information. They should not ask the customer to choose an implementation unless the input explicitly makes the requirement dependent on that choice.

Required qualities:

- Point to the requirement, document excerpt, assumption, conflict, or missing input that caused the question.
- Clarify business intent, constraints, operating model, compliance needs, user populations, data sensitivity, success criteria, timeline, budget guardrails, and ownership.
- Highlight discrepancies and inconsistencies, for example conflicting availability targets, vague compliance language, mismatched geography and latency constraints, or unsupported scale claims.
- Explain why the answer matters without prescribing a solution.
- Include an optional default assumption only when the assistant can proceed safely if the customer does not answer.
- Stay concise: top 3 to 5 questions, ranked by requirement risk and downstream architectural impact.

Examples:

- Good customer clarification: "The documents mention EU data residency but also a US-only support team. Can support staff access production customer data from outside the EU, or must all support access remain EU-bound?"
- Poor customer clarification: "Should we use Azure Front Door with private endpoints?" This is a solution question unless the customer explicitly asked to compare those services.

### Architect Solution Questions

These are for the internal architecture team. They should capture the key design questions we must answer while building the solution. This preserves the useful part of the current behavior, but moves it out of the customer clarification lane.

Required qualities:

- Tie each question to one or more WAF checklist items, WAF pillars, architecture mindmap topics, or both.
- Name the design decision being forced, such as identity topology, recovery strategy, network exposure model, data partitioning, observability model, or cost guardrail enforcement.
- Show the gap source: `waf`, `mindmap`, `requirement`, `conflict`, or `mixed`.
- Capture risk if unanswered and recommended evidence to collect.
- Be visible in the workflow as internal guidance, not as a required customer response.
- Persist as project artifacts from the first version.
- Track the answer lifecycle from the first version: `open`, `answered`, `deferred`, `not_applicable`, including answer text, answer source, answered timestamp, and related evidence or artifact references where available.

Examples:

- Good internal solution question: "How will the design prove tenant isolation across identity, data storage, and observability boundaries? Covers WAF Security identity/access controls and mindmap topics identity, data, and operations."
- Good internal solution question: "What recovery pattern closes the open Reliability checklist item while staying inside the stated RTO/RPO and cost guardrails?"

## Proposed Architecture

Use one planning worker at first, but split its output contract into two explicit sections. This keeps prompt context and dedup logic centralized while making audience and persistence behavior explicit.

Internal architect questions are durable artifacts from the first implementation. They should be written through the approval-first pending-change flow before becoming canonical project state, and their answers must be tracked as updates to those artifacts. The first version should therefore include create, answer/update, and status-change paths for architect questions rather than treating them as transient workflow hints.

Suggested backend result shape:

```json
{
  "customerClarificationGroups": [
    {
      "theme": "Requirements",
      "questions": [
        {
          "question": "Focused customer-facing question",
          "whyItMatters": "Requirement consequence without prescribing a solution",
          "clarificationTarget": "conflict | missing_input | ambiguity | inconsistency",
          "sourceRefs": ["req-auth"],
          "defaultAssumption": "Optional concrete assumption"
        }
      ]
    }
  ],
  "architectQuestionGroups": [
    {
      "theme": "Security",
      "questions": [
        {
          "question": "Internal solution-design question",
          "designDecision": "identity topology",
          "coverageSources": [
            { "kind": "waf", "id": "waf-sec-1", "pillar": "Security" },
            { "kind": "mindmap", "id": "identity" }
          ],
          "riskIfUnanswered": "Architecture may not prove tenant isolation.",
          "recommendedEvidence": ["identity flow", "RBAC matrix"],
          "status": "open",
          "answer": null,
          "answeredAt": null,
          "answerSource": null
        }
      ]
    }
  ]
}
```

Compatibility option: keep emitting `structured_payload.type == "clarification_questions"` for customer questions during the transition, and add a second structured payload field or a new typed payload variant for architect questions. Avoid overloading the existing customer answer form with internal questions. Architect questions must also be persisted as artifacts, so the payload is a presentation surface, not the source of truth.

## Implementation Tasks

### Phase 0 - Baseline and Failing Tests

| ID | Task | Files | Acceptance |
|---|---|---|---|
| Q0.1 | Add regression tests showing customer questions must target ambiguity, discrepancy, inconsistency, or missing requirement input rather than solution implementation choices. | `backend/tests/test_clarification_planner_worker.py` | Test fails against current prompt/schema because only one technical question set exists. |
| Q0.2 | Add tests for two output sets: customer clarification groups and architect question groups. | `backend/tests/test_clarification_planner_worker.py`, `backend/tests/test_agent_runtime_clarify.py` | Tests assert both sets are parsed, filtered, and surfaced separately. |
| Q0.3 | Add WAF/mindmap coverage tests for architect questions. | `backend/tests/test_clarification_planner_worker.py` | Tests assert unresolved WAF gaps and partial/not-addressed mindmap topics are represented in architect questions or explicitly marked not applicable. |
| Q0.4 | Add persistence tests for architect question artifacts and answer/status updates. | `backend/tests/features/projects/`, `backend/tests/test_agent_runtime_clarify.py` | Tests fail until architect questions are created as pending artifacts and answers can be recorded with status metadata. |
| Q0.5 | Add frontend type/rendering tests for the new payload fields. | `frontend/src/features/projects/components/unified/ChatReviewPanel.test.tsx`, `frontend/src/features/projects/api/chatService.test.ts` | Tests fail until frontend distinguishes customer questions from internal architect questions and shows answer status. |

### Phase 1 - Backend Contract Split

| ID | Task | Files | Acceptance |
|---|---|---|---|
| Q1.1 | Replace or extend `ClarificationPlanningResultContract` with explicit `customerClarificationGroups` and `architectQuestionGroups`. | `backend/app/features/agent/contracts/clarification_planner.py` | ✅ Done — Pydantic validates both sections; old `questionGroups` JSON key is explicitly rejected while `question_groups` Python kwarg is transparently forwarded; backward-compat `question_groups` property shim keeps existing callers stable. |
| Q1.2 | Add dedicated question contracts for customer and architect questions. | `backend/app/features/agent/contracts/clarification_planner.py` | ✅ Done — `CustomerClarificationQuestionContract` has `clarificationTarget`/`sourceRefs`; `ArchitectQuestionContract` has `coverageSources`/`designDecision`/`riskIfUnanswered`/answer lifecycle; `ArchitectQuestionCoverageSource`, `UncoveredWafGap`, group contracts and `__init__` exports added. |
| Q1.3 | Update LLM JSON schema in `_plan_with_llm`. | `backend/app/features/agent/application/clarification_planner_worker.py` | Schema asks for both output sets and forbids mixing solution-choice questions into customer clarification groups. |
| Q1.4 | Split filtering and prioritization by audience. | `backend/app/features/agent/application/clarification_planner_worker.py` | Customer questions remain capped at 3 to 5; architect questions have their own cap, for example 5 to 8, and dedup against prior customer clarifications plus prior internal questions. |
| Q1.5 | Update prompt instructions and examples. | `backend/config/prompts/clarification_planner.yaml` | Prompt explicitly defines customer versus internal audience, includes good/bad examples, and keeps customer questions requirement-focused. |

### Phase 2 - WAF and Mindmap Coverage Feature

| ID | Task | Files | Acceptance |
|---|---|---|---|
| Q2.1 | Enrich planner input for WAF gaps with title, pillar, severity/status, item id, and any existing evaluation notes. | `backend/app/features/agent/application/clarification_planner_worker.py` | Architect questions can cite specific checklist items, not only generic pillars. |
| Q2.2 | Enrich planner input for mindmap gaps with topic key, status, confidence if available, and evidence summary if available. | `backend/app/features/agent/application/clarification_planner_worker.py`, mindmap coverage services if needed | Architect questions can cite specific mindmap topics and distinguish partial from not-addressed topics. |
| Q2.3 | Add deterministic coverage validation after LLM output. | `backend/app/features/agent/application/clarification_planner_worker.py` | If WAF/mindmap gaps exist, internal architect questions either reference them or include a reason they are not applicable. |
| Q2.4 | Add a durable `architectQuestions` artifact family. | `backend/app/agents_system/services/aaa_state_models.py`, `backend/app/features/projects/infrastructure/project_state_components_repository.py`, workspace/project-state contracts | Internal architect questions are stored in canonical project state after approval and returned through workspace/project-state reads. |
| Q2.5 | Add approval-first merge support for internal architect question creation. | `backend/app/features/projects/application/pending_changes_merge_service.py`, `backend/app/agents_system/tools/tool_registry.py`, pending-change contracts if needed | New internal questions are first proposed as pending artifacts and only become canonical after approval. |
| Q2.6 | Add answer and status tracking for internal architect questions. | `backend/app/features/projects/application/pending_changes_merge_service.py`, project-state contracts, API/service layer selected for artifact updates | Architect question answers capture `answer`, `status`, `answerSource`, `answeredAt`, and related evidence/artifact references without replacing the original question text. |
| Q2.7 | Add dedup/reopen behavior for persisted architect questions. | `backend/app/features/agent/application/clarification_planner_worker.py`, persistence merge service | Planner does not recreate equivalent open/answered architect questions; unresolved coverage can reopen or supersede questions through a reviewable update. |

### Phase 3 - Runtime Formatting and API Payloads

| ID | Task | Files | Acceptance |
|---|---|---|---|
| Q3.1 | Update clarify-node formatting so the assistant response clearly separates customer questions from internal architect questions. | `backend/app/agents_system/langgraph/nodes/clarify.py` | Customer-facing section remains answerable; internal section is labeled as architect work and is not phrased as customer homework. |
| Q3.2 | Add a structured payload variant for internal architect questions. | `backend/app/agents_system/contracts/workflow_result.py` | `WorkflowStructuredPayload` can represent customer clarification questions and internal architect questions without text parsing. |
| Q3.3 | Keep customer clarification resolution scoped to customer answers only. | `backend/app/features/agent/application/clarification_resolution_worker.py`, `backend/app/agents_system/langgraph/nodes/clarify.py` | Customer answer parsing ignores internal architect questions. |
| Q3.4 | Add an internal architect-question answer path. | Backend route/service selected for artifact updates, pending-change contracts, merge service | An architect can answer, defer, or mark a question not applicable; the update is persisted and visible in project state. |
| Q3.5 | Update stage/eval reporting to recognize the new payload shape and persisted artifacts. | `backend/tests/eval`, `scripts/e2e/aaa_e2e_runner.py` | Eval can fail separately for missing customer clarifications, missing internal WAF/mindmap questions, and missing architect-question answer tracking. |

### Phase 4 - Frontend UX

| ID | Task | Files | Acceptance |
|---|---|---|---|
| Q4.1 | Update TypeScript API types for all backend question fields. | `frontend/src/features/knowledge/types/api-kb.ts` | Types include existing backend optional fields plus the new internal architect question payload. |
| Q4.2 | Keep the answer form for customer clarifications only. | `frontend/src/features/projects/components/unified/ChatReviewPanelSections.tsx` | Customer questions remain answerable and submit through the existing clarification answer message. |
| Q4.3 | Render internal architect questions in a separate artifact-backed section. | `frontend/src/features/projects/components/unified/ChatReviewPanelSections.tsx` or a new local component | Internal questions show WAF/mindmap coverage references, design decision, risk, status, and existing answer state, but do not block customer answer submission. |
| Q4.4 | Add UI affordance for answering or updating internal architect questions. | Frontend artifact/workspace component selected for architect questions | Architect can submit answer text, mark deferred, or mark not applicable; UI reflects persisted status after refresh. |
| Q4.5 | Surface internal architect questions in the Quality Gate tab. | `frontend/src/features/projects/components/unified/QualityGateTab.tsx`, `backend/app/features/projects/application/quality_gate_service.py` | Quality gate shows open/answered/deferred architect questions alongside WAF/mindmap coverage. |

### Phase 5 - Documentation and Evaluation

| ID | Task | Files | Acceptance |
|---|---|---|---|
| Q5.1 | Update backend reference docs. | `docs/backend/BACKEND_REFERENCE.md` | Clarify-stage documentation describes the two question sets and their contracts. |
| Q5.2 | Update agent architecture docs. | `docs/agents/system-architecture.agent.md` | Agent-facing runtime summary reflects the split behavior. |
| Q5.3 | Update prompt README if prompt composition or file responsibilities change. | `backend/config/prompts/README.md` | Prompt documentation accurately describes the clarification planner prompt. |
| Q5.4 | Add or update golden scenarios for question quality and answer tracking. | `backend/tests/eval/golden_scenarios/` | Scenario asserts customer questions clarify requirements while internal questions cover WAF/mindmap and answer/status tracking is present. |
| Q5.5 | Run targeted validations. | Backend and frontend test commands | Use `uv run python -m pytest ...` for backend and `npm.cmd run test:unit`/`npm.cmd run typecheck` from `frontend` when implementation starts. |

## Open Decisions

1. What is the preferred label in the UI: "Architect questions", "Internal design questions", or "Solution questions"?
2. Should customer questions retain default assumptions, or should defaults move only to internal architect questions to avoid implying decisions before the customer responds?
3. Should architect-question answers require approval before becoming canonical, or can answers be recorded directly as artifact updates once the architect submits them?
4. Should answer evidence be a free-text citation list in v1, or should it link only to existing artifact/document identifiers?

## Recommended First Implementation Slice

Start small and test-first:

1. Add failing backend tests for the two-set contract and prompt guardrails.
2. Update `clarification_planner.yaml`, the Pydantic contracts, and `_plan_with_llm` schema.
3. Add the `architectQuestions` artifact family, pending-change creation, approval merge, and workspace/project-state read support.
4. Add answer/status tracking for architect questions from the first slice.
5. Update the clarify-node formatter and frontend types/rendering so customer questions and architect question artifacts are clearly separated.

This gives immediate quality improvement while making the internal question trail durable and auditable from the first implementation.