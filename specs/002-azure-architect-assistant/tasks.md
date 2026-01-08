---

description: "Task list for Azure Architect Assistant (AAA)"
---

# Tasks: Azure Architect Assistant (AAA)

**Input**: Design documents from `/specs/002-azure-architect-assistant/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Automated tests are included for critical paths (pytest). Independent acceptance scenarios from the spec still apply.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US7)
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the integration-first approach and baseline wiring before implementation.

- [x] T001 Confirm plan/spec/contracts alignment in specs/002-azure-architect-assistant/plan.md
- [x] T002 [P] Validate mind map source is present and readable at docs/arch_mindmap.json
- [x] T003 [P] Confirm agent endpoints exist and are mounted under /api/agent in backend/app/agents_system/agents/router.py
- [x] T004 [P] Confirm project endpoints exist for upload/analyze/proposal in backend/app/routers/project_management/project_router.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T005 Implement mind map loader + validator (13 top-level topics) in backend/app/agents_system/services/mindmap_loader.py
- [x] T006 Wire mind map initialization into app startup (load once, fail fast on missing/invalid) in backend/app/lifecycle.py
- [x] T007 Define Pydantic models for AAA artifacts stored inside ProjectState.state in backend/app/agents_system/services/aaa_state_models.py
- [x] T008 Extend project state read/write helpers to validate and normalize AAA state in backend/app/agents_system/services/project_context.py
- [x] T009 Implement source logging helpers (reference docs + MCP queries + citations) in backend/app/agents_system/services/source_logging.py
- [x] T010 Implement merge-based state updates + conflict detection primitives (no overwrite) in backend/app/agents_system/services/state_update_parser.py
- [x] T054 Implement append-only diagram versioning (SC-003) when diagrams are created/updated in backend/app/services/diagram/
- [x] T011 [P] Add frontend API wrapper for project-aware agent chat/history in frontend/src/services/aaa/agentApi.ts
- [x] T012 [P] Add frontend API wrapper for project doc analyze/state in frontend/src/services/aaa/projectApi.ts

**Checkpoint**: Foundation ready — user story work can begin.

---

## Phase 3: User Story 1 — Ingest & Extract Requirements (Priority: P1) 🎯 MVP

**Goal**: Ingest documents/text, normalize into a single corpus, extract requirements + ambiguities, generate initial C4 L1, and persist into ProjectState.

**Independent Test**: Upload mixed-format sources, run analyze-docs, and verify ProjectState contains normalized text, categorized requirements, ambiguities, clarification questions, and a C4 L1 diagram reference.

### Implementation for User Story 1

- [x] T013 [US1] Update ingestion pipeline to record parse failures (not silent skips) in backend/app/routers/project_management/services/document_service.py
- [x] T014 [US1] Extend analyze-docs output to include business/functional/NFR requirements + ambiguity markers in backend/app/routers/project_management/services/document_service.py
- [x] T015 [US1] Generate prioritized clarification questions from gaps/ambiguities (FR-006) in backend/app/routers/project_management/services/document_service.py
- [x] T016 [US1] Generate/store initial C4 Level 1 diagram link in ProjectState via existing diagram flow in backend/app/routers/project_management/project_router.py
- [x] T017 [P] [US1] Build minimal AAA UI shell with upload/analyze and requirements review in frontend/src/features/aaa/

- [x] T044 [US1] Implement PDF text extraction and diagnostics (FR-001) in backend/app/routers/project_management/services/document_service.py
- [x] T045 [US1] Implement XLS/XLSX text extraction and diagnostics (FR-001) in backend/app/routers/project_management/services/document_service.py
- [x] T046 [US1] Route extraction by content type/extension (pdf/xlsx/md/txt) and always record outcomes in backend/app/routers/project_management/services/document_service.py
- [x] T047 [US1] Persist ingestion stats for SC-004 (attempted/parsed/failed + reasons) into ProjectState in backend/app/routers/project_management/services/document_service.py

**Checkpoint**: US1 independently functional.

---

## Phase 4: User Story 2 — Candidate Architectures (Priority: P1)

**Goal**: Generate at least one candidate architecture with assumptions/rationale, update diagrams, and initialize WAF checklists across all pillars.

**Independent Test**: From an ingested project, request candidate generation via agent chat and verify ProjectState includes candidate(s), assumptions, citations, updated diagrams, and initialized WAF checklist (all pillars).

### Implementation for User Story 2

- [x] T018 [US2] Implement candidate generation tool in backend/app/agents_system/tools/aaa_candidate_tool.py
- [x] T019 [US2] Persist candidate architectures, assumptions, and citations (SC-011) into ProjectState using backend/app/agents_system/services/project_context.py
- [x] T020 [US2] Initialize WAF checklist for all pillars (FR-005/SC-002) in backend/app/agents_system/services/aaa_state_models.py
- [x] T021 [P] [US2] Implement candidate viewer (reads ProjectState, shows citations) in frontend/src/features/aaa/

**Checkpoint**: US2 independently functional.

---

## Phase 5: User Story 7 — Document-Driven Iteration (Priority: P1)

**Goal**: Each iteration consults reference docs + MCP, records sources, prompts for uncovered mind map topics, and never overwrites human edits.

**Independent Test**: Run a project-aware agent session; confirm proposals/challenges include citations (WAF/CAF/Architecture Center + MCP URLs), failed lookups are recorded, uncovered mind map topics are prompted, and conflicts are surfaced (no overwrite).

### Implementation for User Story 7

- [ ] T022 [US7] Enforce per-iteration source logging (reference docs + MCP queries) in backend/app/agents_system/tools/mcp_tool.py
- [ ] T023 [US7] Add uncovered mind map topic prompting in backend/app/agents_system/orchestrator/orchestrator.py
- [ ] T024 [US7] Implement conflict surfacing payloads + handling strategy in backend/app/agents_system/agents/router.py
- [ ] T055 [US7] Persist SC-010 iteration events (propose/challenge + citations + architect response link) into ProjectState.iterationEvents in backend/app/agents_system/orchestrator/orchestrator.py
- [ ] T025 [US7] Record failed/empty MCP lookups and request clarification in backend/app/agents_system/tools/mcp_tool.py
- [ ] T026 [P] [US7] Render iteration timeline (reasoning steps + citations) in frontend/src/features/aaa/

- [ ] T048 [US7] When sources conflict (FR-018), present options + tradeoffs + citations and require explicit architect choice before persisting a final selection in backend/app/agents_system/orchestrator/orchestrator.py

**Checkpoint**: US7 independently functional.

---

## Phase 6: User Story 3 — Decisions & ADRs (Priority: P2)

**Goal**: Create/manage ADR lifecycle with traceability to requirements, mind map topics, and diagrams.

**Independent Test**: Create an ADR (draft → accepted → superseded) through agent chat and verify ProjectState stores ADRs with stable IDs and traceability links.

### Implementation for User Story 3

- [ ] T027 [US3] Implement ADR tool (create/update/supersede) with citations (SC-011) in backend/app/agents_system/tools/aaa_adr_tool.py
- [ ] T028 [US3] Persist ADRs + traceability links in backend/app/agents_system/services/aaa_state_models.py
- [ ] T029 [P] [US3] Implement ADR view/edit UX (agent-chat driven) in frontend/src/features/aaa/

- [ ] T049 [US3] Enforce ADR has ≥1 requirement link; diagram/WAF linkage is best-effort and when missing MUST record explicit reason (SC-005) in backend/app/agents_system/tools/aaa_adr_tool.py

**Checkpoint**: US3 independently functional.

---

## Phase 7: User Story 4 — Validation & Findings (Priority: P2)

**Goal**: Validate architecture against WAF (all pillars) and security baselines; produce findings with severity + remediation; update checklist coverage.

**Independent Test**: Trigger validation via agent chat; verify findings list includes severity, WAF pillar/topic, citations, and checklist items update with evidence.

### Implementation for User Story 4

- [ ] T030 [US4] Implement validation tool producing findings in backend/app/agents_system/tools/aaa_validation_tool.py
- [ ] T030 [US4] Implement validation tool producing findings with citations (SC-011) in backend/app/agents_system/tools/aaa_validation_tool.py
- [ ] T031 [US4] Update WAF checklist coverage with evidence links in backend/app/agents_system/services/aaa_state_models.py
- [ ] T032 [P] [US4] Implement findings panel UI in frontend/src/features/aaa/

**Checkpoint**: US4 independently functional.

---

## Phase 8: User Story 5 — IaC & Costs (Priority: P3)

**Goal**: Generate IaC aligned to the approved architecture, run static validation, and produce cost estimates with assumptions.

**Independent Test**: Generate IaC via agent chat; store IaC artifacts + validation results; generate cost estimate with key drivers and assumptions.

### Implementation for User Story 5

- [ ] T033 [US5] Implement IaC generation tool in backend/app/agents_system/tools/aaa_iac_tool.py
- [ ] T034 [US5] Implement static validation recording (SC-006) in backend/app/agents_system/tools/aaa_iac_tool.py
- [ ] T035 [US5] Implement cost estimate generation + persistence in backend/app/agents_system/services/aaa_state_models.py
- [ ] T036 [P] [US5] Implement IaC + cost UI (view + download) in frontend/src/features/aaa/

- [ ] T050 [US5] Implement Azure Retail Prices API client (pagination, filters, retries) in backend/app/services/pricing/retail_prices_client.py
- [ ] T051 [US5] Implement pricing normalization + meter matching rules (service/SKU → retail price) in backend/app/services/pricing/pricing_normalizer.py
- [ ] T052 [US5] Compute and persist baseline monthly cost from Retail Prices API (SC-007) in backend/app/agents_system/services/aaa_state_models.py
- [ ] T053 [US5] Compute and persist variance% vs baseline; record pricing gaps and exclude from variance (SC-007) in backend/app/agents_system/services/aaa_state_models.py

**Checkpoint**: US5 independently functional.

---

## Phase 9: User Story 6 — Mind Map & Traceability (Priority: P3)

**Goal**: Track mind map coverage and provide end-to-end traceability export across all artifacts.

**Independent Test**: Navigate requirement → ADR → diagram/WAF/finding → IaC/cost; export artifacts and confirm traceability links and all 13 topics have coverage statuses.

### Implementation for User Story 6

- [ ] T037 [US6] Implement coverage tracking updates on state changes in backend/app/agents_system/services/mindmap_loader.py
- [ ] T038 [US6] Implement traceability link generation/verification in backend/app/agents_system/services/aaa_state_models.py
- [ ] T039 [US6] Implement export tool preserving traceability links (FR-012) in backend/app/agents_system/tools/aaa_export_tool.py
- [ ] T040 [P] [US6] Implement coverage dashboard + traceability browser in frontend/src/features/aaa/

**Checkpoint**: US6 independently functional.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Hardening after user stories.

- [ ] T041 [P] Update docs quickstart validation checklist in specs/002-azure-architect-assistant/quickstart.md
- [ ] T042 Add observability around state updates, conflicts, and MCP lookups in backend/app/agents_system/agents/router.py
- [ ] T043 [P] Update docs overview references for AAA feature in docs/PROJECT_OVERVIEW.md
- [ ] T056 Add backend smoke tests for analyze-docs: ingestionStats + requirements extraction in backend/tests/
- [ ] T057 Add backend test for merge updates: no-overwrite + conflicts surfaced in backend/tests/

---

## Dependencies & Execution Order

### User Story Completion Order (Dependency Graph)

Setup (Phase 1) → Foundational (Phase 2) → US1 → US2 → (US7 parallel/iterative) → US3 → US4 → US5 → US6 → Polish

### Within Each User Story

- State models/schema updates before agent workflows
- Agent workflows before frontend rendering
- Never overwrite human edits; always surface conflicts

---

## Parallel Opportunities (Examples)

- **Foundation**: T005, T009, T011, T012 can run in parallel (distinct files)
- **US1**: T013 and T017 can run in parallel once Phase 2 is done
- **US2**: T018 and T021 can run in parallel once T019/T020 shape is stable
- **US7**: T023 and T026 can run in parallel

---

## Parallel Example: User Story 1

```bash
Task: "T013 [US1] Update ingestion pipeline in backend/app/routers/project_management/services/document_service.py"
Task: "T017 [P] [US1] Build minimal AAA UI shell in frontend/src/features/aaa/"
```

---

## Implementation Strategy

### MVP First (P1 only)

1. Complete Phase 1–2
2. Complete US1 → US2 → US7
3. Stop and validate independent tests for each story

### Incremental Delivery

1. Add US3 + US4 (governance + validation)
2. Add US5 + US6 (IaC/costs + traceability/export)
