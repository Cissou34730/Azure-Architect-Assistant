# Tasks: Architecture Diagram Generator

**Input**: Design documents from `/specs/001-architecture-diagram-generator/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Not explicitly requested in specification, so test tasks are omitted per YAGNI principle. Add tests if needed later.

## Format: `- [ ] [ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3...)
- All paths are absolute to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and environment setup

- [X] T001 Add environment variables to backend/config.py (DIAGRAMS_DATABASE, PLANTUML_JAR_PATH, OpenAI config)
- [X] T002 Add dependencies to backend/requirements.txt (openai>=1.0.0, plantuml>=0.3.0, pyproject-mermaid>=0.1.0)
- [X] T003 Download PlantUML JAR to backend/lib/plantuml.jar and verify with `java -jar backend/lib/plantuml.jar -version`
- [X] T004 Update backend/Dockerfile to install Java JRE and download plantuml.jar during build
- [X] T005 Configure Alembic for separate diagrams.db database in backend/alembic.ini

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Database Models and Migrations

- [X] T006 [P] Create diagram models Base class in backend/app/models/diagram/base.py
- [X] T007 [P] Create DiagramSet model in backend/app/models/diagram/diagram_set.py (id, adr_id, input_description, created_at, updated_at)
- [X] T008 [P] Create Diagram model in backend/app/models/diagram/diagram.py (id, diagram_set_id FK, diagram_type enum, source_code, rendered_svg, rendered_png, version, created_at)
- [X] T009 [P] Create AmbiguityReport model in backend/app/models/diagram/ambiguity_report.py (id, diagram_set_id FK, ambiguous_text, suggested_clarification, resolved, created_at)
- [X] T010 [P] Create Lock model in backend/app/models/diagram/lock.py (id, diagram_set_id FK UNIQUE, lock_held_by, lock_acquired_at, lock_expires_at)
- [X] T011 Create diagram models __init__.py exporting all entities in backend/app/models/diagram/__init__.py
- [X] T012 Create Alembic migration 001_create_diagram_sets.py in backend/migrations/versions/
- [X] T013 Create Alembic migration 002_create_diagrams.py in backend/migrations/versions/
- [X] T014 Create Alembic migration 003_create_ambiguity_reports.py in backend/migrations/versions/
- [X] T015 Create Alembic migration 004_create_locks.py in backend/migrations/versions/
- [X] T016 Run migrations and verify diagrams.db created with all tables: `alembic upgrade head`

### Core Services Foundation

- [X] T017 Create diagram database session factory in backend/app/services/diagram/database.py (init_diagram_database, get_diagram_session, close_diagram_database functions)
- [X] T018 Create diagram-specific LLM client in backend/app/services/diagram/llm_client.py (DiagramLLMClient class with retry logic, rate limiting, diagram-specific configuration)
- [X] T019 Create PromptBuilder class in backend/app/services/diagram/prompt_builder.py (methods: build_generation_prompt, build_ambiguity_prompt, build_retry_prompt with shared patterns)
- [X] T020 Update backend/app/main.py to initialize diagram database in startup event and close in shutdown event
- [X] T021 Create router __init__.py in backend/app/routers/diagram_generation/__init__.py (aggregates all diagram sub-routers)

**Checkpoint**: Foundation ready - database schema exists, core services scaffolded, backend can start

---

## Phase 3: User Story 1 - Generate Functional Requirements Diagram (Priority: P1) 🎯 MVP

**Goal**: Accept text description, detect ambiguities, generate Mermaid functional diagram

**Independent Test**: POST /api/v1/diagram-sets with functional requirements description → receives Mermaid diagram + ambiguity list

### Ambiguity Detection (US1 Required)

- [X] T022 [P] [US1] Implement ambiguity detector service in backend/app/services/diagram/ambiguity_detector.py (analyze_description method using LLM to identify unclear elements)
- [X] T023 [US1] Create POST /api/v1/diagram-sets/{id}/ambiguities endpoint in backend/app/routers/diagram_generation/ambiguities.py (list ambiguities for diagram set)
- [X] T024 [US1] Create PATCH /api/v1/ambiguities/{id} endpoint to mark ambiguity as resolved

### Mermaid Functional Diagram Generation (US1 Core)

- [X] T025 [P] [US1] Implement syntax validator in backend/app/services/diagram/syntax_validator.py (validate_mermaid_syntax using pyproject-mermaid)
- [X] T026 [P] [US1] Implement semantic validator in backend/app/services/diagram/semantic_validator.py (validate_diagram_semantics using LLM to verify diagram matches description)
- [X] T027 [P] [US1] Implement visual quality checker in backend/app/services/diagram/visual_quality_checker.py (check_mermaid_visual_quality: node count ≤20, edge count ≤30, orphan detection)
- [X] T028 [US1] Implement validation pipeline orchestrator in backend/app/services/diagram/validation_pipeline.py (validate_diagram method coordinating all 5 layers)
- [X] T029 [US1] Implement diagram generator service in backend/app/services/diagram/diagram_generator.py (generate_mermaid_functional method: LLM generation → validation pipeline → retry up to 3 times)
- [X] T030 [US1] Create POST /api/v1/diagram-sets endpoint in backend/app/routers/diagram_generation/diagram_sets.py (accepts input_description, optional adr_id → generates functional Mermaid diagram + detects ambiguities)
- [X] T031 [US1] Create GET /api/v1/diagram-sets/{id} endpoint to retrieve diagram set with all diagrams and ambiguities
- [X] T032 [US1] Register diagram_generation router in backend/app/main.py with prefix="/api/v1"

### Frontend Mermaid Rendering (US1 Required)

- [X] T033 [P] [US1] Create MermaidRenderer component in frontend/src/components/diagrams/MermaidRenderer.tsx (props: diagramSetId, diagramType; uses mermaid.js for client-side rendering with Tailwind CSS v4 syntax)
- [X] T034 [US1] Install mermaid.js dependency in frontend: `npm install mermaid`
- [X] T035 [US1] Implement error handling in MermaidRenderer for invalid syntax (show error message, don't crash)

**Checkpoint US1**: Can submit functional requirements description → receive Mermaid diagram + ambiguity list → view rendered diagram in frontend

---

## Phase 4: User Story 2 - Generate C4 Context and Container Diagrams (Priority: P1) 🎯 MVP

**Goal**: Generate C4 Level 1 (Context) and C4 Level 2 (Container) Mermaid diagrams from architecture description

**Independent Test**: POST /api/v1/diagram-sets with architecture description → receives 3 diagrams (functional + C4 Context + C4 Container)

### C4 Compliance Validation (US2 Required)

- [X] T036 [P] [US2] Implement C4 compliance validator in backend/app/services/diagram/c4_compliance_validator.py (validate_c4_compliance: check Context diagrams have Person+System only, Container diagrams have Container elements, no abstraction level violations)

### C4 Diagram Generation (US2 Core)

- [X] T037 [P] [US2] Add generate_c4_context method to diagram_generator.py (uses Mermaid C4Context syntax with Person, System, Boundary elements)
- [X] T038 [P] [US2] Add generate_c4_container method to diagram_generator.py (uses Mermaid C4Container syntax with Container, ContainerDb, Boundary elements)
- [X] T039 [US2] Update POST /api/v1/diagram-sets endpoint to generate 3 Mermaid diagram types in parallel (functional, C4 Context, C4 Container) using diagram_generator methods
- [X] T040 [US2] Update validation_pipeline.py to apply C4 compliance validation (Layer 4) for C4 diagram types only
- [X] T041 [US2] Update PromptBuilder to include C4-specific prompt templates (system context vs container abstraction levels)

### Frontend C4 Rendering (US2 Required)

- [X] T042 [US2] Update MermaidRenderer.tsx to handle C4Context and C4Container diagram types (initialize mermaid with C4 support)
- [X] T043 [US2] Create DiagramSetViewer component in frontend/src/components/diagrams/DiagramSetViewer.tsx (displays multiple diagrams side-by-side: functional, C4 Context, C4 Container)

**Checkpoint US2**: Can submit architecture description → receive 3 Mermaid diagrams (functional + C4 Context + C4 Container) → view all rendered in frontend side-by-side

---

## Phase 5: User Story 3 - Generate Azure-Specific PlantUML Diagrams (Priority: P2)

**Goal**: Generate PlantUML diagrams with Azure service icons, rendered server-side to SVG/PNG

**Independent Test**: POST /api/v1/diagram-sets with Azure architecture description → receives PlantUML diagram with correct Azure sprites rendered as SVG/PNG

### Azure Icon Validation (US3 Required)

- [ ] T044 [P] [US3] Implement Azure icon validator in backend/app/services/diagram/azure_icon_validator.py (validate_azure_icons: map Azure services from description to sprite names, log warnings for mismatches)
- [ ] T045 [P] [US3] Create AZURE_SERVICE_SPRITES mapping dict in azure_icon_validator.py (azure function → AzureFunctions, cosmos db → AzureCosmosDb, blob storage → AzureBlobStorage, etc.)

### PlantUML Rendering (US3 Core)

- [ ] T046 [P] [US3] Implement PlantUML renderer in backend/app/services/diagram/plantuml_renderer.py (render_plantuml method: invoke Java JAR with PlantUML source → return SVG and PNG bytes)
- [ ] T047 [P] [US3] Add validate_plantuml_syntax method to syntax_validator.py (invoke PlantUML JAR with -testdot flag)
- [ ] T048 [US3] Add generate_plantuml_azure method to diagram_generator.py (uses C4-PlantUML syntax with Azure-PlantUML sprites: !include <C4/C4_Container>, !include AzurePuml/Compute/AzureFunctions.puml)
- [ ] T049 [US3] Update POST /api/v1/diagram-sets to generate 4 diagram types: mermaid_functional, c4_context, c4_container, plantuml_azure
- [ ] T050 [US3] Update validation_pipeline.py to apply Azure icon validation (Layer 5) for PlantUML diagram type only
- [ ] T051 [US3] Create GET /api/v1/diagrams/{id}/rendered endpoint to retrieve SVG or PNG rendering (returns image bytes with appropriate Content-Type header)

### Frontend PlantUML Display (US3 Required)

- [ ] T052 [US3] Update DiagramSetViewer.tsx to display PlantUML diagrams as <img> elements using rendered SVG/PNG from backend (fetch from /api/v1/diagrams/{id}/rendered?format=svg)

**Checkpoint US3**: Can submit Azure architecture description → receive 4 diagrams including PlantUML with Azure icons → view all rendered in frontend

---

## Phase 6: User Story 4 - Version and Link Diagrams to ADRs (Priority: P2)

**Goal**: Semantic versioning for diagrams, ADR reference tracking, version history

**Independent Test**: Create diagram → regenerate with changes → version increments → retrieve version history → filter by ADR ID

### Versioning Infrastructure (US4 Core)

- [ ] T053 [P] [US4] Implement version_manager module in backend/app/services/diagram/version_manager.py (determine_next_version method: analyze changes to determine MAJOR.MINOR.PATCH increment)
- [ ] T054 [US4] Update diagram_generator.py to assign semantic version on creation (v1.0.0) and regeneration (increment based on change type)
- [ ] T055 [US4] Update Diagram model to store previous_version_id FK (optional, for version chain tracking)

### ADR Integration (US4 Core)

- [ ] T056 [US4] Update POST /api/v1/diagram-sets to accept and validate adr_id parameter (alphanumeric + hyphens only)
- [ ] T057 [US4] Update PATCH /api/v1/diagram-sets/{id} endpoint to allow updating adr_id
- [ ] T058 [US4] Extend GET /api/v1/diagram-sets with query filters for FR-020: `?adr_id={exact_match}` (case-sensitive), `?version={semver}` (exact match e.g., v1.2.0), `?created_after={ISO8601}`, `?created_before={ISO8601}`. Multiple filters combine with AND logic. Return paginated results.

### Version History API (US4 Required)

- [ ] T059 [US4] Create GET /api/v1/diagram-sets/{id}/versions endpoint to list all versions of a diagram set with timestamps
- [ ] T060 [US4] Create GET /api/v1/diagrams/{id}/history endpoint to list version history for a specific diagram type within a set
- [ ] T061 [US4] Update POST /api/v1/diagram-sets/{id}/regenerate endpoint to preserve old version before creating new version (increment version number)

**Checkpoint US4**: Can create diagram → link to ADR → regenerate → see version history → filter diagrams by ADR ID

---

## Phase 7: User Story 5 - Manage and Update Diagrams Through Frontend (Priority: P3)

**Goal**: Full CRUD operations via frontend UI, regeneration workflow, change highlighting

**Independent Test**: Use frontend to create/view/update/delete diagram sets, regenerate diagrams, view version history

### Diagram Update API (US5 Core)

- [ ] T062 [US5] Implement locking service in backend/app/services/diagram/locking_service.py (acquire_lock, release_lock, check_lock methods with 10-minute timeout)
- [ ] T063 [US5] Create POST /api/v1/diagram-sets/{id}/lock endpoint in backend/app/routers/diagram_generation/locks.py (acquire lock with user_id parameter)
- [ ] T064 [US5] Create DELETE /api/v1/diagram-sets/{id}/lock endpoint to release lock
- [ ] T065 [US5] Create PATCH /api/v1/diagram-sets/{id} endpoint to update input_description (requires lock, regenerates diagrams)
- [ ] T066 [US5] Create DELETE /api/v1/diagram-sets/{id} endpoint to delete diagram set (soft delete preferred)

### Frontend Management UI (US5 Required)

- [ ] T067 [US5] Create DiagramSetList component in frontend/src/components/diagrams/DiagramSetList.tsx (lists all diagram sets with ADR ID, creation date, diagram count)
- [ ] T068 [US5] Create DiagramSetEditor component in frontend/src/components/diagrams/DiagramSetEditor.tsx (edit input_description, acquire/release lock, regenerate button)
- [ ] T069 [US5] Create VersionSelector component in frontend/src/components/diagrams/VersionSelector.tsx (dropdown to switch between diagram versions)
- [ ] T070 [US5] Implement version diff highlighting in DiagramSetViewer.tsx (compare source_code of two versions, highlight changes)

**Checkpoint US5**: Can use frontend to fully manage diagram lifecycle: create, view, edit, regenerate, delete, view versions

---

## Phase 8: User Story 6 - Integrate Diagrams into Project Documents (Priority: P3)

**Goal**: Export diagrams in multiple formats, embed codes for dynamic inclusion in documents

**Independent Test**: Generate diagram → export as PNG/SVG/Markdown → successfully embed in document

### Export API (US6 Core)

- [ ] T071 [P] [US6] Create GET /api/v1/diagrams/{id}/export endpoint with format parameter (mermaid_source, plantuml_source, svg, png, markdown_embed)
- [ ] T072 [P] [US6] Implement markdown embed code generation in export endpoint (returns `![Diagram](api-url)` syntax with version reference)
- [ ] T073 [US6] Create GET /api/v1/diagram-sets/{id}/export endpoint to export entire diagram set as ZIP file (all diagrams in all formats)

### Frontend Export UI (US6 Required)

- [ ] T074 [US6] Add Export button to DiagramSetViewer.tsx with format selection dropdown (PNG, SVG, Mermaid Source, PlantUML Source, Markdown Embed, Full ZIP)
- [ ] T075 [US6] Implement file download handler in frontend for each export format

**Checkpoint US6**: Can export diagrams in multiple formats and embed in documents

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Performance optimization, error handling, logging, monitoring

### Performance Optimization

- [ ] T076 [P] Add request timeout middleware to prevent >30s generation time (SC-001 compliance)
- [ ] T077 [P] Add database connection pooling configuration for diagrams.db session factory
- [ ] T078 [P] Add LLM response caching for repeated identical descriptions (cache key: hash of input_description)

### Error Handling & Logging

- [ ] T079 [P] Add structured logging to all diagram services (log diagram_set_id, diagram_type, generation_time, validation_results)
- [ ] T080 [P] Implement error response schemas in OpenAPI spec (400 validation errors, 409 lock conflicts, 500 generation failures)
- [ ] T081 [P] Add circuit breaker pattern to LLM client for API failure resilience

### Monitoring & Observability

- [ ] T082 [P] Add Prometheus metrics for diagram generation (count, duration, failure rate, validation pass/fail rates)
- [ ] T083 [P] Add health check endpoint GET /api/v1/health/diagrams (checks diagrams.db connectivity, PlantUML JAR availability, OpenAI API connectivity)

### Documentation

- [ ] T084 Create API usage guide in specs/001-architecture-diagram-generator/API_GUIDE.md (examples for each endpoint, authentication, rate limits)
- [ ] T085 Update quickstart.md with frontend setup instructions (npm install, environment variables, component usage)
- [ ] T086 Create TROUBLESHOOTING.md with common issues (PlantUML JAR errors, OpenAI API failures, lock timeout issues)

---

## Implementation Strategy

### MVP Scope (P1 Stories)
**Minimum Viable Product**: User Story 1 + User Story 2
- Functional Mermaid diagram generation
- C4 Context and Container diagrams
- Ambiguity detection
- Frontend rendering (client-side Mermaid)
- **Estimated Tasks**: T001-T043 (43 tasks)
- **Estimated Effort**: ~2-3 weeks for 1 developer

### Phase 2 Delivery (P2 Stories)
Add User Story 3 + User Story 4
- PlantUML with Azure icons
- Versioning and ADR linking
- **Additional Tasks**: T044-T061 (18 tasks)
- **Estimated Effort**: +1-2 weeks

### Phase 3 Delivery (P3 Stories)
Add User Story 5 + User Story 6
- Full frontend management UI
- Export and document integration
- **Additional Tasks**: T062-T075 (14 tasks)
- **Estimated Effort**: +1-2 weeks

### Polish
Phase 9 tasks for production readiness
- **Additional Tasks**: T076-T086 (11 tasks)
- **Estimated Effort**: +1 week

**Total Tasks**: 86
**Total Estimated Effort**: 5-8 weeks for 1 developer (adjust based on team size)

---

## Dependencies & Parallel Execution

### Dependency Graph (User Story Completion Order)

```
Phase 1 (Setup) → Phase 2 (Foundation) → Must complete before user stories
                                          ↓
                      ┌───────────────────┴────────────────────┐
                      ↓                                        ↓
            Phase 3 (US1) ────→ Phase 4 (US2)                 |
                      ↓               ↓                        |
                      └───────┬───────┘                        |
                              ↓                                |
                        Phase 5 (US3) ←──────────────────────┘
                              ↓
                        Phase 6 (US4)
                              ↓
                        Phase 7 (US5)
                              ↓
                        Phase 8 (US6)
                              ↓
                        Phase 9 (Polish)
```

### Parallel Execution Opportunities

**Within Phase 2 (Foundation)**:
- T006-T010 (all diagram models) - parallel
- T012-T015 (all migrations) - sequential (must follow model creation)
- T017-T019 (core services) - parallel after T011

**Within Phase 3 (US1)**:
- T022-T024 (ambiguity detection) - parallel
- T025-T027 (validators) - parallel
- T033-T035 (frontend) - parallel with backend tasks

**Within Phase 4 (US2)**:
- T036-T038 (C4 generation) - parallel with T041
- T042-T043 (frontend) - parallel with backend

**Within Phase 5 (US3)**:
- T044-T047 (validation & rendering) - parallel
- T052 (frontend) - parallel with backend

**Within Phase 6 (US4)**:
- T053-T055 (versioning) - parallel with T056-T058 (ADR)

**Within Phase 9 (Polish)**:
- T076-T083 (all polish tasks) - mostly parallel

---

## Validation Checklist

Before considering implementation complete:

- [ ] All P1 user stories (US1, US2) deliver independent value
- [ ] Each user story can be tested independently
- [ ] Success criteria SC-001 verified: diagram generation <30 seconds
- [ ] Success criteria SC-006 verified: frontend page load <3 seconds
- [ ] All 5 validation layers tested and working (syntax, semantic, visual, C4, Azure icons)
- [ ] Constitution principles verified: SRP, Auto-Deploy, Explicit Naming, Zero Duplication, YAGNI
- [ ] OpenAPI contract matches implementation
- [ ] Database migrations have rollback functions
- [ ] Error handling covers all edge cases from spec.md
- [ ] Pessimistic locking prevents concurrent edit conflicts
- [ ] Version history maintains complete audit trail
- [ ] Frontend uses correct Tailwind CSS v4 syntax (no deprecated utilities)

---

**Generated**: 2025-12-17
**Source**: /speckit.tasks command
**Input Documents**: spec.md (6 user stories), plan.md (5-layer validation), data-model.md (4 entities), contracts/openapi.yaml (10 endpoints)
