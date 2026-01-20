# Consistency Check: Spec ↔ Plan ↔ Tasks

**Feature**: [specs/002-azure-architect-assistant/spec.md](specs/002-azure-architect-assistant/spec.md)
**Date**: 2026-01-08

## Summary

- Plan now matches the repo reality: initial ingestion extends Project Management; all discussion + artifact generation reuses Agent System.
- Tasks have been corrected to remove references to a parallel `services/aaa` orchestration layer.

## Functional Requirements Coverage (FR)

Legend: ✅ covered in tasks/docs, ⚠️ partially covered (needs detail during implementation)

- FR-001 ingest PDF/MD/Excel/text → ✅ Tasks: US1 (T010–T011b)
- FR-002 extract business/functional/NFR + ambiguities → ✅ Tasks: US1 (T011)
- FR-003 generate/update C4 L1 after ingestion → ✅ Tasks: US1 (T012)
- FR-004 propose candidate architectures + assumptions → ✅ Tasks: US2 (T015)
- FR-005 WAF checklists all pillars + status → ⚠️ Tasks: US2 (T017a) + US4 (T026–T027)
- FR-006 prioritized clarification questions → ✅ Tasks: US1 (T011a)
- FR-007 ADR lifecycle + traceability → ✅ Tasks: US3 (T023–T024)
- FR-008 validate vs WAF + security; findings severity/remediation → ✅ Tasks: US4 (T026–T027)
- FR-009 end-to-end traceability links → ⚠️ Tasks: US6 (T035) + data-model.md (TraceabilityLink)
- FR-010 IaC generation + static validation → ⚠️ Tasks: US5 (T029–T030)
- FR-011 cost estimate + assumptions → ⚠️ Tasks: US5 (T031)
- FR-012 export artifacts preserving links → ✅ Tasks: US6 (T035a)
- FR-013 human edits authoritative; merge + conflict surfacing → ⚠️ Tasks: US7 (T021) (implementation must define conflict rules)
- FR-014 iterative sessions propose/challenge + capture responses → ✅ Tasks: US7 (T019)
- FR-015 consult reference docs for proposals/validation/IaC → ⚠️ Tasks: US7 (T019) (implementation must enforce)
- FR-016 MCP queries with explicit search terms → ✅ Tasks: Phase 2 (T007) + US2 (T016)
- FR-017 record which docs/MCP used per ADR/finding/IaC → ✅ Tasks: Phase 2 (T007) + US2/US4/US5
- FR-018 do not auto-select when sources conflict → ⚠️ Tasks: US7 (T019) (implementation must enforce option presentation)
- FR-019 load mind map at init and validate 13 topics → ✅ Tasks: Phase 2 (T005)
- FR-020 track coverage and link artifacts to nodes → ✅ Tasks: US1 (T013) + US7 (T020) + data-model.md
- FR-021 prompt on uncovered topics → ✅ Tasks: US7 (T020)

## Success Criteria Coverage (SC)

- SC-001 mind map topic coverage exists → ✅ Phase 2 (T005) + US6 (T033/T034)
- SC-002 WAF checklists all pillars tracked → ⚠️ US2 (T017a) + US4 (T026–T027)
- SC-003 C4 L1 produced early and versioned → ⚠️ US1 (T012) (versioning details to implement)
- SC-004 95% docs parsed; failures logged/surfaced → ✅ US1 (T011b)
- SC-005 decisions have ADRs linked to req + diagram/WAF → ⚠️ US3 (T023–T024) + US6 (T035)
- SC-006 IaC passes static validation → ⚠️ US5 (T030)
- SC-007 costs ±15% vs calculator baseline → ⚠️ US5 (T031) (baseline method TBD)
- SC-008 traceability export no broken references → ⚠️ US6 (T035/T035a)
- SC-009 no human content overwritten → ⚠️ US7 (T021)
- SC-010 each iteration logs propose/challenge + response + links → ✅ US7 (T019) + agent history endpoint
- SC-011 candidates/ADRs/findings cite at least one source → ✅ Phase 2 (T007) + US2/US3/US4
- SC-012 MCP queries recorded with terms + URLs → ✅ Phase 2 (T007) + US7 (T021a)
- SC-013 mind map loaded and validated → ✅ Phase 2 (T005)
- SC-014 coverage per topic linked to artifacts + flagged gaps → ✅ US7 (T020) + US6 (T033)

## Contract Alignment

- API contract now reflects actual integration point: agent-driven discussion/artifact generation via `/api/agent/projects/{projectId}/chat`.
- Existing project ingestion endpoints remain under `/api/projects/{projectId}/*`.

## Remaining “Needs Detail” Items (Implementation-Time)

- WAF checklist schema and evidence linking rules (FR-005, SC-002)
- Human-edit conflict resolution strategy for `ProjectState` (FR-013, SC-009)
- IaC static validation tooling choice per environment (SC-006)
- Cost baseline method for SC-007
