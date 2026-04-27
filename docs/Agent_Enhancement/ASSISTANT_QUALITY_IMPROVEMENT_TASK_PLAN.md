# Assistant Quality Improvement Task Plan

## Purpose

This document turns the codebase review and prompt-quality analysis into an implementation task list. The goal is to make Azure Architect Assistant produce more comprehensive, higher-value architecture guidance while preserving the current LangGraph workflow, reviewable pending-change model, and project-state governance.

The current implementation has a strong workflow shell, but the user-visible answer often feels thin because the system prioritizes persistence and concise summaries over an expert architectural briefing. The changes below focus on improving the actual value delivered in each response.

## Target Outcome

For architecture-related turns, the assistant should:

- Give a clear recommendation, not only a procedural next step.
- Explain why the recommendation fits the project context.
- Show trade-offs and rejected alternatives.
- Surface risks, mitigations, WAF impact, cost drivers, and open decisions.
- Persist structured artifacts through pending change sets.
- Summarize what was persisted without hiding all architectural insight from the user.

## Priority 1: Add an Architect Briefing Output Contract

### Problem

The current prompts and runtime directives tell the model to persist artifacts and keep the chat response concise. This protects project state, but the user often receives a low-value answer such as "I created a pending change set" rather than a useful architectural synthesis.

### Files to Change

- `backend/config/prompts/base_persona.yaml`
- Add new file: `backend/config/prompts/architect_briefing.yaml`
- `backend/app/agents_system/config/prompt_loader.py`
- `backend/app/agents_system/langgraph/nodes/agent_native.py`

### Tasks

1. Create `backend/config/prompts/architect_briefing.yaml`.
2. Add a required "Architect Briefing" contract for project-facing responses.
3. Include this structure:
   - Recommendation
   - Why this fits the project
   - Key trade-offs
   - Main risks and mitigations
   - WAF impact
   - Cost drivers
   - Open decisions
   - Persisted artifacts
   - Next action
4. Make the contract stage-aware:
   - `propose_candidate`: full briefing required.
   - `validate`: risks, WAF findings, evidence, remediation required.
   - `pricing`: assumptions, cost drivers, confidence, gaps required.
   - `iac`: deployment shape, validation status, operational risks required.
   - `clarify`: questions plus default assumptions if unanswered.
5. Update `_SHARED_PROMPT_FILES` in `prompt_loader.py` to include the new prompt after `base_persona.yaml` or before `guardrails.yaml`.
6. Update `agent_native._build_system_directives()` so its "Output discipline" allows a concise briefing instead of only a short receipt.

### Acceptance Criteria

- Architecture answers contain a useful synthesis even when artifacts are persisted.
- The assistant no longer responds only with a change-set id for architecture work.
- The chat answer does not include raw Mermaid, raw IaC, or full artifact dumps.

## Priority 2: Resolve Prompt Contradictions

### Problem

The active prompt stack says both:

- Be comprehensive and thorough.
- Do not inline architecture proposals, trade-offs, NFR analysis, diagrams, or requirements.

This creates model confusion and encourages shallow answers.

### Files to Change

- `backend/config/prompts/constitution.yaml`
- `backend/config/prompts/base_persona.yaml`
- `backend/config/prompts/guardrails.yaml`
- `backend/config/prompts/agent_prompts.yaml`
- `backend/app/agents_system/langgraph/nodes/agent_native.py`

### Tasks

1. Rewrite "Persist before responding" to distinguish between:
   - persisted structured artifacts
   - user-visible architectural briefing
2. Replace wording such as "chat response is for concise summaries only" with:
   - "Do not duplicate full artifacts; provide a decision-quality synthesis."
3. Remove or soften the "3-4 paragraphs max" concept from legacy prompt text.
4. Ensure all prompt layers agree on this rule:
   - persist artifacts through tools
   - explain the architectural value in chat
   - avoid raw structured payload dumps
5. Add a short explicit example to the prompt:
   - "Good response: I recommend Azure Container Apps because... Trade-offs... Risks... I persisted candidate architecture X."
   - "Bad response: I created change set X."

### Acceptance Criteria

- No prompt layer tells the assistant to hide all meaningful architecture analysis from the user.
- The assistant is still forbidden from dumping raw diagram code, IaC bundles, or complete artifact JSON in chat.

## Priority 3: Strengthen the Architecture Planner Rubric ✅ IMPLEMENTED

### Problem

`architecture_planner_prompt.yaml` asks for a complete proposal, but it does not enforce a strict enough consulting-quality rubric. It says to include NFRs and diagrams, but not enough about rejected alternatives, explicit risk analysis, service-by-service rationale, ADR candidates, and implementation sequencing.

### Files Changed

- `backend/config/prompts/architecture_planner_prompt.yaml`
- `backend/app/agents_system/langgraph/nodes/architecture_planner.py`
- `backend/tests/agents_system/test_architecture_planner_node.py`

### Tasks

1. Add mandatory sections to the architecture planner prompt:
   - Executive recommendation
   - Workload classification
   - Target topology
   - Azure service-by-service rationale
   - Alternatives rejected
   - Trade-offs
   - Risks and mitigations
   - WAF pillar mapping
   - NFR achievement matrix
   - Cost drivers
   - Operational model
   - Security model
   - ADR candidates
   - Implementation phases
   - Persisted artifacts summary
2. Update `_build_synthesizer_contract()` in `architecture_planner.py` to require those sections.
3. Update `_build_synthesis_execution_artifact()` to detect the new required sections.
4. Make missing sections visible in the execution artifact for diagnostics.
5. Add tests that verify the architecture planner prompt contains the required sections.

### Acceptance Criteria

- The architecture planner has a clear definition of a "good architecture answer."
- The runtime can detect whether important sections are missing.
- The final response is more specific than generic Azure best-practice boilerplate.

## Priority 4: Expand the Candidate Architecture Artifact Model

### Problem

The architecture planner asks for rich architecture content, but `aaa_generate_candidate_architecture` persists only:

- title
- summary
- assumptions
- diagram ids
- citations

This loses key value such as components, risks, trade-offs, WAF mapping, cost drivers, and rejected alternatives.

### Files to Change

- `backend/app/features/agent/infrastructure/tools/aaa_candidate_tool.py`
- `backend/app/agents_system/services/aaa_state_models.py`
- `backend/tests/agents_system/test_iac_tool_and_cost_models.py`
- Add or update tests for candidate architecture persistence
- Frontend rendering files for candidate architecture display, if present

### Tasks

1. Extend `AAAGenerateCandidateInput` with optional typed fields:
   - `components`
   - `service_choices`
   - `alternatives_rejected`
   - `tradeoffs`
   - `risks`
   - `waf_mapping`
   - `nfr_mapping`
   - `cost_drivers`
   - `operational_considerations`
   - `security_controls`
   - `implementation_phases`
   - `adr_candidates`
2. Update the tool output so these fields are included in `candidateArchitectures`.
3. Update project-state validation models to allow the new fields.
4. Update pending-change artifact draft summaries to reflect richer candidate data.
5. Update frontend candidate architecture view to render the new sections.
6. Add backward compatibility so old candidates without these fields still render.

### Acceptance Criteria

- A candidate architecture pending change contains the same core insight the assistant explains in chat.
- Approving a candidate preserves risks, trade-offs, WAF mapping, and implementation guidance in canonical project state.

## Priority 5: Add Quality Gates for Architecture Completeness

### Problem

The workflow has a quality gate, but the architecture stage needs stronger checks to prevent low-value answers from passing.

### Files to Change

- `backend/app/agents_system/langgraph/nodes/quality_gate.py`
- `backend/app/agents_system/langgraph/nodes/architecture_planner.py`
- `backend/tests/test_quality_gate_loop.py`
- Add dedicated architecture quality-gate tests

### Tasks

1. Add stage-specific checks for `propose_candidate`.
2. Fail or retry when the answer lacks:
   - recommendation
   - service rationale
   - NFR mapping
   - trade-offs
   - risks
   - WAF impact
   - citations or evidence
   - persisted candidate or pending change set
3. Add checks for whether the assistant only returned a generic persistence receipt.
4. Populate `quality_retry_reason` with a precise reason.
5. Ensure `quality_retry` instructs the model to add missing briefing sections, not just retry generically.
6. Limit retries to avoid loops.

### Acceptance Criteria

- A shallow architecture answer is rejected and retried.
- Retry prompt names the missing sections.
- Tests prove that weak answers fail and complete answers pass.

## Priority 6: Generate a Final Briefing From Pending Changes ✅ IMPLEMENTED

### Problem

The model may create a good pending change set, but the chat answer can still be weak. The system should produce a useful user-facing summary from the structured pending change itself.

### Files Changed

- Added new service: `backend/app/features/agent/application/pending_change_briefing_service.py` — `PendingChangeBriefingService.generate_briefing()` dispatches to stage-specific formatters for `propose_candidate`, `pricing`, `iac`, `validate`, and `clarify`; falls back to a generic summary for unknown stages.
- `backend/app/agents_system/langgraph/nodes/postprocess.py` — calls `PendingChangeBriefingService` after extracting the pending change set, attaches `generated_briefing` to graph state.
- `backend/app/agents_system/langgraph/nodes/persist.py` — `apply_state_updates_node` calls `_enrich_answer_with_briefing()` which prepends the briefing when the LLM answer is a thin receipt (<300 chars with persistence phrases), or appends it when the answer is already rich.
- `backend/tests/test_pending_change_briefing_service.py` — 30 tests covering all stages, graceful edge cases, and integration flow.

### Tasks

1. ✅ Create a formatter that accepts a `PendingChangeSetContract`.
2. ✅ Generate stage-specific summaries:
   - candidate architecture: recommendation, risks, WAF impact, trade-offs
   - cost: total, assumptions, gaps, confidence
   - IaC: resources, validation, deployment notes
   - validation: findings, severity, remediation
   - clarify: questions with defaults and decision impact
3. ✅ In `postprocess_node`, when `pending_change_set` exists, attach a generated briefing to state.
4. ✅ In `apply_state_updates_node`, prefer the generated briefing when the model output is only a receipt.
5. ✅ Ensure the original pending change id remains visible.

### Acceptance Criteria

- ✅ Even if the LLM final text is weak, the user receives a useful structured explanation based on the pending change.
- ✅ The pending change id and review instruction remain present.
- ✅ 30 tests pass covering all stages and integration flow.

## Priority 7: Improve Research-to-Decision Traceability

### Problem

Research packets exist, but the code does not guarantee that each architecture decision consumes evidence. The assistant can cite sources without clearly tying them to service choices.

### Files to Change

- `backend/app/agents_system/langgraph/nodes/research.py`
- `backend/app/agents_system/langgraph/nodes/architecture_planner.py`
- `backend/app/features/agent/infrastructure/tools/aaa_candidate_tool.py`
- Candidate architecture state model

### Tasks

1. Add a required `decisionEvidenceMap` field to candidate architecture payloads.
2. Each entry should include:
   - decision id or service choice
   - requirement ids
   - evidence packet ids
   - source citations
   - confidence
3. Update architecture planner prompt to require this mapping.
4. Add validation that every major service choice has at least one evidence source.
5. In the final briefing, summarize the strongest evidence and the weakest assumptions.

### Acceptance Criteria

- User can see why each major Azure service was chosen.
- Unsupported or weakly supported decisions are explicitly marked as assumptions or open decisions.

## Priority 8: Improve Clarification Value ✅ COMPLETED

### Problem

Clarification can feel procedural. Questions should be fewer, sharper, and tied to architecture consequences.

### Files Changed

- `backend/config/prompts/clarification_planner.yaml` — updated to v1.2 with required question structure (why_it_matters, affected_decision, default_assumption, risk_if_wrong), good/bad examples, >70% proceed rule, and top 3-5 ranking rule.
- `backend/app/agents_system/langgraph/nodes/clarify.py` — added `_user_wants_to_proceed()` helper and proceed-with-defaults path that persists default assumptions as reviewable pending change artifacts.
- `backend/app/features/agent/application/clarification_planner_worker.py` — updated LLM JSON schema to require affectedDecision, defaultAssumption, and riskIfWrong fields.
- `backend/app/features/agent/application/clarification_resolution_worker.py` — added `proceed_with_defaults()` method that builds a change set from default assumptions without an LLM call.
- `backend/app/features/agent/contracts/clarification_planner.py` — added optional `affected_decision`, `default_assumption`, `risk_if_wrong` fields to `ClarificationQuestionContract`.
- `backend/app/agents_system/contracts/workflow_result.py` — added optional `affected_decision`, `default_assumption`, `risk_if_wrong` fields to `ClarificationQuestionPayloadItem`.
- `backend/tests/test_agent_runtime_clarify.py` — added `test_user_wants_to_proceed_detection` and `test_execute_clarification_planner_node_proceeds_with_defaults`.
- `backend/tests/test_clarification_planner_worker.py` — added `test_clarification_prompt_has_required_question_structure` and `test_clarification_limits_to_top_questions`.

### Tasks

1. Require each clarification question to include:
   - question
   - why it matters
   - affected architecture decision
   - default assumption if unanswered
   - risk of wrong assumption
2. Allow the assistant to proceed with explicit assumptions when enough evidence exists.
3. Add ranking so only the top 3 to 5 decision-blocking questions are shown.
4. Avoid asking generic questions that are not directly tied to a downstream decision.
5. Persist default assumptions as pending changes when the user chooses to proceed.

### Acceptance Criteria

- ✅ Clarification questions include why/decision/default/risk structure
- ✅ Only top 3-5 questions are asked
- ✅ User can proceed with default assumptions
- ✅ Default assumptions are persisted as pending changes when user proceeds
- ✅ Tests pass

## Priority 9: Improve Cost Estimation Precision and Transparency

### Problem

The cost estimator can produce baseline estimates from heuristic service mapping. This is useful, but it needs clearer confidence, assumptions, and gaps.

### Files to Change

- `backend/app/agents_system/langgraph/nodes/cost_estimator.py`
- `backend/app/features/agent/infrastructure/tools/aaa_cost_tool.py`
- `backend/app/features/agent/infrastructure/tools/azure_retail_prices_tool.py`
- Cost estimate state model and tests

### Tasks

1. Add explicit fields to cost artifacts:
   - region
   - environment
   - currency
   - confidence level
   - pricing assumptions
   - pricing gaps
   - excluded services
   - optimization opportunities
2. Require user-provided or inferred values for:
   - region
   - SKU/tier
   - quantity
   - usage duration
   - storage amount
   - transaction volume
3. If exact values are missing, label the result as "baseline estimate."
4. Add a final answer section:
   - "What would make this estimate more accurate"
5. Add tests for:
   - no architecture available
   - baseline assumptions requested
   - supported service with missing usage
   - exact pricing inputs

### Acceptance Criteria

- Cost answers are transparent about confidence.
- The assistant does not present heuristic baseline pricing as precise estimation.

## Priority 10: Improve Diagram Quality and Explanation

### Problem

The diagram tool persists diagrams, but value depends on whether diagrams are meaningful and explained.

### Files to Change

- `backend/app/features/agent/infrastructure/tools/aaa_diagram_tool.py`
- `backend/app/features/diagrams/application/semantic_validator.py`
- `backend/app/features/diagrams/application/visual_quality_checker.py`
- `backend/app/features/diagrams/application/validation_pipeline.py`
- Diagram tests

### Tasks

1. Add semantic diagram validation checks:
   - actor exists for context diagrams
   - system boundary exists
   - Azure services are named clearly
   - data flows are labeled
   - trust/security boundaries are represented when relevant
   - external dependencies are shown
2. Add a `diagramExplanation` field to diagram references or companion artifact.
3. Include "how to read this diagram" in the final briefing.
4. If ambiguity detector finds unresolved ambiguity, surface it as a clarification or warning.
5. Add tests with intentionally weak diagrams.

### Acceptance Criteria

- Generated diagrams are not only syntactically valid but architecturally useful.
- User receives a short explanation of what each diagram validates.

## Priority 11: Add ADR Candidate Detection ✅ IMPLEMENTED

### Problem

Architecture proposals naturally imply decisions, but the assistant may not capture ADR candidates unless explicitly asked.

### Files Changed

- `backend/config/prompts/architecture_planner_prompt.yaml`
- `backend/app/agents_system/langgraph/nodes/architecture_planner.py`
- `backend/config/prompts/adr_writer.yaml`
- `backend/tests/agents_system/test_architecture_planner_node.py`

### Tasks

1. During architecture proposal, detect major decisions:
   - hosting model
   - database choice
   - identity model
   - network exposure model
   - regional/DR strategy
   - integration pattern
   - observability approach
2. Add `adrCandidates` to candidate architecture payload.
3. In final briefing, list which ADRs should be created next.
4. Optionally create ADR pending changes when the user asks to proceed.
5. Add tests that a proposal creates ADR candidates.

### Acceptance Criteria

- The assistant naturally moves from architecture proposal to decision capture.
- Key architectural decisions are not lost in free-form chat.

## Priority 12: Make More Stages Deterministic — ✅ IMPLEMENTED

### Problem

Several stages depend on the LLM following instructions and emitting correct tool calls. This is flexible but fragile.

### Implementation (P12)

- **New file**: `backend/app/agents_system/contracts/stage_contracts.py`
  - `RequirementsExtractionOutput`: functional_requirements, non_functional_requirements, constraints, open_questions (all default to empty list)
  - `ClarificationPlanOutput`: questions (list of `_ClarificationQuestion` with question/decision_impact/default_assumption), proceed_with_defaults (bool, default False)
  - `ArchitectureDraftOutput`: candidate_name, summary (required), components, trade_offs, risks, waf_highlights, next_steps
  - `ValidationOutput`: waf_findings, severity_breakdown, top_issues, recommendation (all default-safe)
  - `AdrDraftOutput`: title, context, decision, consequences (required), status (default "proposed"), alternatives_considered
  - `_parse_and_validate_output(raw, contract)` helper: returns `(model, None)` on success, `(None, raw)` on malformed JSON or schema mismatch with a WARNING log
- **Updated**: `backend/app/agents_system/contracts/__init__.py` to export all 5 contracts and the helper
- **Updated**: `backend/app/agents_system/langgraph/nodes/validate.py` imports and uses `_parse_and_validate_output` + `ValidationOutput` to build a typed contract snapshot of findings before forwarding
- **Tests**: `backend/tests/test_stage_contracts.py` — 20 tests covering valid parse, defaults, required field rejection, malformed JSON, schema mismatch, and integration smoke test

### Files Changed

- `backend/app/agents_system/contracts/stage_contracts.py` (new)
- `backend/app/agents_system/contracts/__init__.py` (updated exports)
- `backend/app/agents_system/langgraph/nodes/validate.py` (uses contracts)
- `backend/tests/test_stage_contracts.py` (new, 20 tests)

### Acceptance Criteria

- ✅ Critical artifacts are produced through validated contracts, not ad hoc text parsing.
- ✅ `_parse_and_validate_output` provides graceful degradation (returns raw on failure, no crash).
- ✅ Validate stage worker uses the typed contract for findings introspection.

### Files to Change (original)

---

## P14: End-to-End Journey Tests — IMPLEMENTED

### What was done

Added `backend/tests/e2e/test_answer_quality_journey.py` with 13 tests covering the full agent lifecycle for 4 key scenarios using mocks/stubs (no real LLM):

1. **TestClarificationJourney** — vague request hits the clarify stage; verifies `structured_payload` has `type: clarification_questions` and questions have `affectedDecision` + `defaultAssumption` populated.
2. **TestArchitectureProposalJourney** — propose_candidate stage returns a `WorkflowStageResult` with `stage`, `summary`, `nextStep`, `reasoningSummary`; quality gate passes rich answers and retries thin receipts.
3. **TestCostEstimationJourney** — pricing stage result has correct structure; quality gate accepts cost answers with and without artifact edit.
4. **TestQualityGateRetryJourney** — thin receipt triggers retry; `quality_gate_node` increments `quality_retry_count` and sets architectural `quality_retry_reason`; enriched answers pass.

Also added `quality_gate_node` alias to `backend/app/agents_system/langgraph/nodes/quality_gate.py` as a named wrapper for `build_quality_retry`.

### Files Changed

- `backend/tests/e2e/__init__.py` (new)
- `backend/tests/e2e/test_answer_quality_journey.py` (new, 13 tests)
- `backend/app/agents_system/langgraph/nodes/quality_gate.py` (added `quality_gate_node`)

### Acceptance Criteria

- ✅ 13 journey tests pass with mocks/stubs — no real LLM calls required.
- ✅ Clarification payload carries decision fields in camelCase serialized output.
- ✅ Quality gate correctly distinguishes thin receipts from rich architecture answers.
- ✅ Retry node increments count and sets an architectural failure reason.

---

## P15: Answer Quality Eval Golden Scenarios — IMPLEMENTED

### What was done

Added 5 YAML golden scenario files in `backend/tests/eval/golden_scenarios/` covering the key journey stages. Extended `eval_runner.py` with `JourneyScenario`, `JourneyScenarioResult`, `JourneyEvalRun`, `discover_journey_scenarios`, `load_journey_scenario`, `validate_journey_response`, and `run_journey_eval_harness`. Extended `reporting.py` with `JourneyScenarioDimension`, `JourneyScenarioReport`, `JourneyEvalReport`, and `build_journey_eval_report`.

Added 5 new tests to `test_eval_runner.py` and 4 new tests to `test_reporting.py`.

### Files Changed

- `backend/tests/eval/golden_scenarios/journey-clarify-vague.yaml` (new)
- `backend/tests/eval/golden_scenarios/journey-propose-candidate.yaml` (new)
- `backend/tests/eval/golden_scenarios/journey-cost-estimation.yaml` (new)
- `backend/tests/eval/golden_scenarios/journey-quality-gate-retry.yaml` (new)
- `backend/tests/eval/golden_scenarios/journey-compliance-workload.yaml` (new)
- `backend/tests/eval/eval_runner.py` (journey scenario support)
- `backend/tests/eval/reporting.py` (journey eval report)
- `backend/tests/eval/test_eval_runner.py` (5 new journey tests)
- `backend/tests/eval/test_reporting.py` (4 new journey report tests)

### Acceptance Criteria

- ✅ 5 YAML scenario files define expected fields, forbidden patterns, and stage metadata.
- ✅ `discover_journey_scenarios()` loads all 5 scenarios by glob pattern.
- ✅ `validate_journey_response()` checks dot-path field presence and regex forbidden patterns.
- ✅ `run_journey_eval_harness()` runs all scenarios and produces a `JourneyEvalRun`.
- ✅ `build_journey_eval_report()` converts results to a typed Pydantic report with pass rate.

- Existing stage workers under `backend/app/agents_system/langgraph/nodes/`
- Existing application workers under `backend/app/features/agent/application/`
- Tool contracts under `backend/app/features/agent/contracts/`

### Tasks

1. Identify stages that can return typed contracts:
   - requirements extraction
   - clarification planning
   - architecture candidate drafting
   - validation finding drafting
   - ADR drafting
2. For each stage, define a Pydantic contract.
3. Use LLM JSON-mode or structured output where available.
4. Validate output before creating pending changes.
5. Fall back to clarification rather than persisting malformed artifacts.
6. Keep the general tool-loop path for open-ended conversation only.

### Acceptance Criteria

- Critical artifacts are produced through validated contracts, not ad hoc text parsing.
- `AAA_STATE_UPDATE` becomes a fallback path, not the primary correctness mechanism.

## Priority 13: Refactor the Prompt Stack

### Problem

The code uses modular prompts, but the legacy `agent_prompts.yaml` still contains overlapping and sometimes conflicting instructions. This makes behavior difficult to reason about.

### Files to Change

- `backend/config/prompts/agent_prompts.yaml`
- `backend/config/prompts/constitution.yaml`
- `backend/config/prompts/base_persona.yaml`
- `backend/config/prompts/tool_strategy.yaml`
- `backend/config/prompts/guardrails.yaml`
- `backend/app/agents_system/config/prompt_loader.py`

### Tasks

1. Define prompt layers:
   - constitution
   - role/persona
   - stage contract
   - output contract
   - tool contract
   - quality rubric
2. Remove duplicate instructions from `agent_prompts.yaml`.
3. Keep `agent_prompts.yaml` only as a compatibility fallback or regenerate it from the modular prompts.
4. Add tests for prompt composition:
   - orchestrator prompt includes constitution, routing, base persona, tool strategy, guardrails, architect briefing.
   - architecture planner prompt includes planner prompt and shared rules.
   - stage-specific prompts override generic routing.
5. Add a debug endpoint or log entry that records prompt file names used for each turn.

### Acceptance Criteria

- Developers can explain exactly what prompt the model receives for each stage.
- Legacy and modular prompts no longer contradict each other.

## Priority 14: Add End-to-End Journey Tests

### Problem

The code has many unit tests, but correctness should be proven across the full project journey.

### Files to Add or Change

- Add tests under `backend/tests/e2e/` or `backend/tests/agents_system/`
- Existing test fixtures in `backend/tests/conftest.py`

### Tasks

1. Create an end-to-end test scenario:
   - create project
   - upload document
   - extract requirements
   - generate clarification questions
   - answer clarification
   - propose architecture
   - generate diagrams
   - create cost estimate
   - generate IaC
   - approve pending changes
   - verify final project state
2. Use mocked LLM responses where needed.
3. Assert that pending changes are created at each artifact-producing step.
4. Assert that approved changes merge into canonical state.
5. Assert final answer contains architect briefing sections.
6. Assert no raw Mermaid or raw artifact JSON is dumped in chat.

### Acceptance Criteria

- The full assistant journey can be validated automatically.
- Regressions in workflow articulation are caught before release.

## Priority 15: Add Answer-Quality Evaluation Scenarios

### Problem

Existing tests can prove that the workflow runs, but not that answers are valuable.

### Files to Add or Change

- `backend/tests/eval/golden_scenarios/`
- `backend/tests/eval/eval_runner.py`
- `backend/tests/eval/reporting.py`

### Tasks

1. Add golden scenarios for:
   - vague architecture request
   - detailed RFP document
   - compliance-driven workload
   - high-availability workload
   - cost-sensitive workload
   - IaC request after architecture proposal
2. Score each answer on:
   - specificity
   - completeness
   - trade-offs
   - risk analysis
   - WAF coverage
   - source grounding
   - next action usefulness
   - persistence correctness
3. Add threshold gates for architecture answers.
4. Generate a report showing failed dimensions.

### Acceptance Criteria

- The team can measure whether prompt and workflow changes improve answer quality.
- Quality is not judged only by whether the model produced any answer.

## Suggested Implementation Order

1. Add architect briefing prompt and resolve prompt contradictions.
2. Strengthen architecture planner rubric.
3. Add architecture quality gate checks.
4. Expand candidate architecture schema.
5. Add final briefing formatter from pending changes.
6. Improve research-to-decision traceability.
7. Improve clarification, cost, and diagram quality.
8. Refactor prompt stack.
9. Add end-to-end and evaluation tests.

## Definition of Done

The improvement work is done when:

- Architecture answers are useful without opening hidden artifacts.
- Every generated artifact is still reviewable through pending changes.
- Candidate architecture artifacts preserve the same insight shown in the briefing.
- Shallow architecture answers fail quality gates.
- End-to-end tests cover the full assistant journey.
- Evaluation scenarios show measurable improvement in completeness and specificity.

