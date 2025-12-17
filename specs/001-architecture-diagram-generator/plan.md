# Implementation Plan: Architecture Diagram Generator

**Branch**: `001-architecture-diagram-generator` | **Date**: 2025-12-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-architecture-diagram-generator/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Integrate diagram generation capabilities into the existing unified FastAPI backend by adding new router at `backend/app/routers/diagram_generation/` and services at `backend/app/services/diagram/`. The feature accepts architecture descriptions via REST API and generates multiple diagram types: Mermaid (functional flow, C4 Context/Container) rendered client-side in React, and PlantUML (Azure service icons) rendered server-side to SVG/PNG. Uses separate OpenAI client for diagram-specific LLM operations (ambiguity detection, 3-retry validation). Stores diagram versions in isolated `diagrams.db` with pessimistic locking for concurrent edit protection. Reuses existing FastAPI infrastructure (lifecycle, middleware, configuration) while maintaining service isolation.

## Technical Context

**Language/Version**: Python 3.10+ (backend), TypeScript 5+ (frontend React component integration)  
**Primary Dependencies**: FastAPI 0.115+ (existing app), OpenAI SDK 1.0+ with GPT-4 Turbo (new diagram-specific client in `services/diagram/llm_client.py`), plantuml 0.3+ with local JAR (PlantUML rendering), pyproject-mermaid 0.1+ (Mermaid validation), SQLAlchemy 2.0+ with aiosqlite (async ORM)  
**Storage**: Separate SQLite database `backend/data/diagrams.db` with independent session factory (`services/diagram/database.py`) isolated from existing `projects.db` for scaling flexibility  
**Testing**: pytest (backend unit/integration tests), frontend tests for React Mermaid component integration  
**Target Platform**: Integrated into existing FastAPI backend at `backend/app/`, frontend React 19+ with client-side Mermaid rendering, Docker containerized deployment
**Project Type**: Web application backend extension (router + services added to existing structure)  
**Performance Goals**: <30 seconds diagram generation (SC-001), <3 seconds frontend page load for all diagrams (SC-006)  
**Constraints**: OpenAI API rate limits (TPM/RPM), PlantUML rendering time (~2-5s per diagram), pessimistic locking for edit conflicts, 3-retry limit on generation failures, SQLite single writer limitation on `diagrams.db`  
**Scale/Scope**: Multiple concurrent users (read-heavy workload), version history per diagram (semantic versioning), ADR-linked diagram sets via external ID reference, support for 4 diagram types (Mermaid functional, C4 Context, C4 Container, PlantUML Azure)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Single Responsibility** - **PASS**
  - Evaluation: Integration maintains clear SRP boundaries:
    - Router layer (`routers/diagram_generation/`) handles HTTP concerns only
    - Service layer (`services/diagram/`) separates: LLM client, generator orchestration, ambiguity detection, rendering (PlantUML/Mermaid), locking
    - Each model has single purpose: DiagramSet (metadata), Diagram (artifacts), AmbiguityReport (quality), Lock (concurrency)
  - Status: **PASS** - Clarification confirmed router integration pattern preserves service isolation

- [x] **II. Automated Deployment** - **PASS**
  - Evaluation: Integration into existing backend leverages established auto-deployment:
    - Reuses existing Docker containerization and lifecycle management
    - Separate `diagrams.db` as volume mount (no provisioning)
    - PlantUML JAR downloaded during container build (existing pattern)
    - Environment variables for configuration (`DIAGRAMS_DATABASE`, `PLANTUML_JAR_PATH`)
    - Alembic migrations run on startup via existing lifecycle hooks
    - New router auto-registered in `main.py` (standard pattern)
  - Status: **PASS** - Follows existing deployment automation patterns

- [x] **III. Explicit Naming** - **PASS**
  - Evaluation: All new code follows explicit naming:
    - Router paths: `POST /api/v1/diagram-sets` (not `/ds`)
    - Service modules: `diagram_generator.py`, `ambiguity_detector.py` (not abbreviated)
    - Model fields: `input_description`, `lock_held_by`, `diagram_set_id` (fully spelled out)
    - Enum values: `mermaid_functional`, `c4_context`, `c4_container`, `plantuml_azure`
    - Database: `diagrams.db` (not `diag.db` or `dg.db`)
  - Status: **PASS** - OpenAPI and data-model demonstrate compliance

- [x] **IV. Zero Duplication** - **PASS**
  - Evaluation: Integration avoids duplication while maintaining isolation:
    - **Separate LLM client justified**: Diagram-specific rate limiting, retry logic, and prompt handling differ from general-purpose `llm_service.py` (clarification decision B)
    - **Separate database justified**: Isolation enables independent backup/scaling strategies without affecting `projects.db` (clarification decision B)
    - **Shared patterns**: PromptBuilder class abstracts common LLM patterns across diagram types (research.md)
    - **Reused infrastructure**: FastAPI app, Docker config, lifecycle management (clarification decision A)
  - Status: **PASS** - Justified duplication for isolation; shared abstractions where appropriate

- [x] **V. YAGNI** - **PASS**
  - Evaluation: Implementation scope limited to P1 features:
    - Mermaid functional, C4 Context/Container diagrams only (P1)
    - PlantUML Azure icons (P1 proof-of-concept)
    - ADR `adr_id` field nullable (minimal P2 prep, no speculative workflow)
    - No approval system, comments, or advanced versioning UI (deferred P3)
    - No premature optimization (e.g., no caching until proven needed)
  - Status: **PASS** - Spec and data-model limit to essential P1 functionality

- [x] **Instruction files compliance verified**
  - Python backend: Follows `.github/copilot-instructions.md` (SRP, explicit naming, DRY)
  - TypeScript frontend: Client-side Mermaid rendering via React component (minimal integration)
  - Agent context: Updated with Python 3.10+, FastAPI, separate LLM client, diagrams.db decisions
  - Status: **PASS** - Clarifications incorporated into agent context

**Violations**: None. Separate LLM client and database are **justified** architectural decisions for isolation and scaling, not violations.

**Mitigation Strategies**:
- Separate LLM client mitigated by: Diagram-specific requirements (retry logic, prompt patterns) differ from general `llm_service.py` usage
- Separate database mitigated by: Independent lifecycle, backup, and scaling needs; prevents `projects.db` lock contention

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── main.py                         # MODIFY: Add diagram_generation router registration
│   ├── config.py                       # MODIFY: Add DIAGRAMS_DATABASE, PLANTUML_JAR_PATH env vars
│   ├── projects_database.py            # EXISTING: Projects.db session factory (not modified)
│   ├── lifecycle.py                    # EXISTING: Startup/shutdown hooks (not modified)
│   │
│   ├── models/
│   │   ├── project.py                  # EXISTING: Project models with separate Base
│   │   └── diagram/                    # NEW: Diagram-specific models
│   │       ├── __init__.py
│   │       ├── base.py                 # Diagram models Base (separate from project Base)
│   │       ├── diagram_set.py          # DiagramSet entity
│   │       ├── diagram.py              # Diagram entity with version field
│   │       ├── ambiguity_report.py     # AmbiguityReport entity
│   │       └── lock.py                 # Lock entity for pessimistic locking
│   │
│   ├── routers/
│   │   ├── ingestion.py                # EXISTING
│   │   ├── kb_management/              # EXISTING
│   │   ├── kb_query/                   # EXISTING
│   │   ├── project_management/         # EXISTING
│   │   └── diagram_generation/         # NEW: Diagram generation routes
│   │       ├── __init__.py
│   │       ├── diagram_sets.py         # CRUD for diagram sets, regeneration
│   │       ├── ambiguities.py          # Ambiguity resolution endpoints
│   │       └── locks.py                # Lock acquisition/release endpoints
│   │
│   ├── services/
│   │   ├── llm_service.py              # EXISTING: General LLM service (not reused)
│   │   ├── rag/                        # EXISTING
│   │   ├── mcp/                        # EXISTING
│   │   ├── kb/                         # EXISTING
│   │   └── diagram/                    # NEW: Diagram-specific services
│   │       ├── __init__.py
│   │       ├── database.py             # Diagram DB session factory (diagrams.db)
│   │       ├── llm_client.py           # Diagram-specific OpenAI client
│   │       ├── prompt_builder.py       # Shared LLM prompt patterns
│   │       ├── diagram_generator.py    # Orchestrates generation (calls llm_client)
│   │       ├── ambiguity_detector.py   # LLM-powered ambiguity detection
│   │       ├── plantuml_renderer.py    # PlantUML JAR invocation + Azure icons
│   │       ├── mermaid_validator.py    # Mermaid syntax validation (Layer 1)
│   │       ├── locking_service.py      # Pessimistic lock management
│   │       ├── syntax_validator.py     # NEW: Layer 1 validation (syntax)
│   │       ├── semantic_validator.py   # NEW: Layer 2 validation (LLM-based semantic check)
│   │       ├── visual_quality_checker.py  # NEW: Layer 3 validation (quality metrics)
│   │       ├── c4_compliance_validator.py  # NEW: Layer 4 validation (C4 model rules)
│   │       ├── azure_icon_validator.py     # NEW: Layer 5 validation (Azure sprite accuracy)
│   │       └── validation_pipeline.py      # NEW: Orchestrates 5-layer validation
│   │
│   └── agents_system/                  # EXISTING (not modified)
│
├── migrations/                         # NEW: Alembic migrations for diagrams.db
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_create_diagram_sets.py
│       ├── 002_create_diagrams.py
│       ├── 003_create_ambiguity_reports.py
│       └── 004_create_locks.py
│
├── lib/
│   └── plantuml.jar                    # PlantUML JAR (downloaded in Dockerfile)
│
├── data/
│   ├── projects.db                     # EXISTING: Project database
│   └── diagrams.db                     # NEW: Diagram-specific database
│
├── tests/
│   ├── test_diagram_generation/        # NEW: Diagram tests
│   │   ├── unit/
│   │   │   ├── test_prompt_builder.py
│   │   │   ├── test_mermaid_validator.py
│   │   │   ├── test_locking_service.py
│   │   │   ├── test_syntax_validator.py        # NEW: Test Layer 1 validation
│   │   │   ├── test_semantic_validator.py      # NEW: Test Layer 2 validation
│   │   │   ├── test_visual_quality_checker.py  # NEW: Test Layer 3 validation
│   │   │   ├── test_c4_compliance_validator.py # NEW: Test Layer 4 validation
│   │   │   └── test_azure_icon_validator.py    # NEW: Test Layer 5 validation
│   │   ├── integration/
│   │   │   ├── test_diagram_generation.py
│   │   │   ├── test_ambiguity_detection.py
│   │   │   ├── test_api_endpoints.py
│   │   │   └── test_validation_pipeline.py     # NEW: Test full validation pipeline
│   │   ├── contract/
│   │   │   └── test_openapi_spec.py
│   │   └── performance/                        # NEW: Performance validation
│   │       ├── test_generation_speed.py        # Verify SC-001 (<30s)
│   │       └── test_validation_overhead.py     # Verify validation <5s overhead
│   └── [other existing tests]          # EXISTING (not modified)
│
├── Dockerfile                          # MODIFY: Add Java JRE, download plantuml.jar
├── requirements.txt                    # MODIFY: Add openai, plantuml, pyproject-mermaid
└── alembic.ini                         # NEW: Alembic config for diagrams.db migrations

frontend/
├── src/
│   └── components/
│       └── diagrams/
│           └── MermaidRenderer.tsx     # NEW: Client-side Mermaid rendering
└── [existing structure]

.github/
├── workflows/
│   └── [existing CI/CD]                # MODIFY: Ensure diagram tests run
└── agents/
    └── copilot-instructions.md         # MODIFIED: Added diagram context
```

**Structure Decision**: Web application extension - integrate diagram generation into existing `backend/app/` FastAPI application. New router at `routers/diagram_generation/` follows existing pattern (kb_query, project_management). Services in isolated `services/diagram/` namespace with separate database session factory. Reuses app lifecycle, Docker config, and deployment infrastructure. Frontend adds minimal Mermaid rendering component only (PlantUML rendered server-side).

## Diagram Quality Validation Strategy

To ensure diagram accuracy and quality (critical for user requirements), implement **5-layer validation pipeline** before storing diagrams:

### Layer 1: Syntax Validation (Blocking)
**Purpose**: Verify diagram code is syntactically correct and can be rendered.

**Implementation**:
- **Mermaid**: Use `pyproject-mermaid>=0.1.0` library to validate syntax
- **PlantUML**: Invoke PlantUML JAR with `-testdot` flag to validate before rendering
- **Retry Logic**: On failure, include error message in LLM retry prompt (max 3 attempts per FR-021)

**Service**: `backend/app/services/diagram/syntax_validator.py`
```python
async def validate_mermaid_syntax(source_code: str) -> ValidationResult:
    """Validate Mermaid diagram syntax."""
    from pyproject_mermaid import validate
    try:
        validate(source_code)
        return ValidationResult(is_valid=True)
    except Exception as e:
        return ValidationResult(is_valid=False, error=str(e))
```

### Layer 2: Semantic Validation (Blocking)
**Purpose**: Verify diagram accurately represents the input description (not just syntactically valid).

**Implementation**:
- Use separate LLM call to compare input description vs generated diagram
- Check for missing elements, incorrect relationships, wrong abstraction level
- On failure, retry generation with semantic feedback included in prompt

**Service**: `backend/app/services/diagram/semantic_validator.py`
```python
async def validate_diagram_semantics(
    input_description: str,
    diagram_source: str,
    diagram_type: DiagramType,
    llm_client: DiagramLLMClient
) -> SemanticValidationResult:
    """Use LLM to verify diagram matches description."""
    
    prompt = f"""Compare input description with generated diagram:
    
    INPUT: {input_description}
    DIAGRAM TYPE: {diagram_type}
    DIAGRAM CODE: {diagram_source}
    
    Verify:
    1. All mentioned components/systems present?
    2. Relationships correctly represented?
    3. Appropriate abstraction level for {diagram_type}?
    
    Return JSON:
    {{
      "is_valid": true/false,
      "missing_elements": [...],
      "incorrect_relationships": [...],
      "suggestions": "..."
    }}
    """
    
    result = await llm_client.validate_semantics(prompt)
    return parse_semantic_validation(result)
```

**Retry Strategy**: If `is_valid=false`, include semantic feedback in next generation attempt.

### Layer 3: Visual Quality Checks (Non-blocking, logs warnings)
**Purpose**: Ensure diagrams are readable and well-structured.

**Implementation**:
- Parse diagram to extract nodes, edges, relationships
- Apply quality metrics (configurable thresholds)

**Metrics**:
- **Mermaid diagrams**:
  - Node count: ≤20 (readability threshold)
  - Edge count: ≤30 (avoid spaghetti)
  - Depth: ≤5 levels (avoid deep nesting)
  - Orphan nodes: 0 (all nodes must connect)
  
- **PlantUML diagrams**:
  - Sprite existence: Verify all Azure sprites exist in library
  - Boundary usage: Systems/containers grouped in boundaries
  - Layout hints: Use `Rel_U/D/L/R` for directional control

**Service**: `backend/app/services/diagram/visual_quality_checker.py`
```python
def check_mermaid_visual_quality(source_code: str) -> QualityReport:
    """Parse Mermaid and check visual quality metrics."""
    nodes = extract_nodes(source_code)
    edges = extract_edges(source_code)
    
    issues = []
    if len(nodes) > 20:
        issues.append("Too many nodes - consider splitting diagram")
    if len(edges) > 30:
        issues.append("Too many relationships - simplify")
    
    orphans = find_orphan_nodes(nodes, edges)
    if orphans:
        issues.append(f"Orphan nodes detected: {orphans}")
    
    return QualityReport(
        is_acceptable=len(issues) == 0,
        issues=issues,
        warnings=[i for i in issues],  # Log as warnings, don't block
        severity="WARNING"
    )
```

**Action**: Log warnings to help improve prompts, but don't block storage (non-critical quality issue).

### Layer 4: C4 Model Compliance (Blocking for C4 diagrams)
**Purpose**: Verify C4 diagrams follow C4 model abstraction rules.

**Implementation**:
- Apply C4 model rules based on diagram type
- On violation, retry with rule-specific feedback

**C4 Context Diagram Rules**:
- Must show `Person` and `System` elements only (no `Container`/`Component`)
- Must have at least one `Person` (actor)
- Must show system boundary (via `Boundary` or `Enterprise_Boundary`)

**C4 Container Diagram Rules**:
- Must show `Container` elements within system boundary
- Can show external systems but not their containers
- No `Component` elements (wrong abstraction level)
- Must use `Boundary` to group containers

**Service**: `backend/app/services/diagram/c4_compliance_validator.py`
```python
def validate_c4_compliance(
    source_code: str,
    diagram_type: DiagramType
) -> C4ValidationResult:
    """Validate C4 model rules."""
    
    if diagram_type == DiagramType.C4_CONTEXT:
        # Check for Container/Component elements (violation)
        if "Container(" in source_code or "Component(" in source_code:
            return C4ValidationResult(
                is_compliant=False,
                violations=["Context diagram contains Container/Component elements"],
                fix_suggestion="Use System elements only for context view"
            )
        
        # Check for Person elements
        if "Person(" not in source_code and "Person_Ext(" not in source_code:
            return C4ValidationResult(
                is_compliant=False,
                violations=["Context diagram missing Person (actor)"],
                fix_suggestion="Add Person element to show who uses the system"
            )
    
    elif diagram_type == DiagramType.C4_CONTAINER:
        # Check for Component elements (violation)
        if "Component(" in source_code:
            return C4ValidationResult(
                is_compliant=False,
                violations=["Container diagram shows Component elements"],
                fix_suggestion="Use Container elements only"
            )
    
    return C4ValidationResult(is_compliant=True)
```

**Retry Strategy**: If non-compliant, include C4 rule violation in retry prompt with fix suggestion.

### Layer 5: Azure Icon Accuracy (Non-blocking, logs warnings)
**Purpose**: Verify PlantUML uses correct Azure service sprites (for PlantUML diagrams only).

**Implementation**:
- Extract Azure services mentioned in input description
- Map to expected sprite names (e.g., "azure function" → "AzureFunctions")
- Compare with sprites actually used in PlantUML source
- Log warnings for mismatches (helps improve LLM prompts)

**Service**: `backend/app/services/diagram/azure_icon_validator.py`
```python
# Map common Azure services to correct sprite names
AZURE_SERVICE_SPRITES = {
    "azure function": "AzureFunctions",
    "function app": "AzureFunctions",
    "cosmos db": "AzureCosmosDb",
    "cosmosdb": "AzureCosmosDb",
    "blob storage": "AzureBlobStorage",
    "storage account": "AzureStorageAccounts",
    "api management": "AzureAPIManagement",
    "apim": "AzureAPIManagement",
    "app service": "AzureWebApp",
    "web app": "AzureWebApp",
    "sql database": "AzureSqlDatabase",
    "event hub": "AzureEventHub",
    "service bus": "AzureServiceBus",
    # ... comprehensive mapping from Azure-PlantUML library
}

def validate_azure_icons(
    input_description: str,
    plantuml_source: str
) -> IconValidationResult:
    """Check if correct Azure sprites used."""
    
    # Extract mentioned Azure services from input
    mentioned_services = extract_azure_services(input_description)
    
    # Extract sprites used in PlantUML ($sprite parameter)
    used_sprites = extract_sprites_from_plantuml(plantuml_source)
    
    warnings = []
    for service in mentioned_services:
        expected_sprite = AZURE_SERVICE_SPRITES.get(service.lower())
        if expected_sprite and expected_sprite not in used_sprites:
            warnings.append(
                f"Service '{service}' should use sprite '{expected_sprite}' "
                f"but not found in diagram"
            )
    
    return IconValidationResult(
        has_correct_icons=len(warnings) == 0,
        warnings=warnings
    )
```

**Action**: Log warnings for monitoring/improvement, but don't block (icon accuracy is quality enhancement, not functional requirement).

### Validation Pipeline Flow

```
1. Generate diagram (LLM via diagram_generator.py)
   ↓
2. Layer 1: Syntax Validation
   ↓ [FAIL] → Retry with syntax error feedback (max 3 attempts)
   ↓ [PASS]
3. Layer 2: Semantic Validation (LLM-based)
   ↓ [FAIL] → Retry with semantic feedback (max 3 attempts)
   ↓ [PASS]
4. Layer 3: Visual Quality Checks
   ↓ [ISSUES FOUND] → Log warnings (non-blocking)
   ↓ [CONTINUE]
5. Layer 4: C4 Compliance (C4 diagrams only)
   ↓ [FAIL] → Retry with C4 rule violation feedback
   ↓ [PASS]
6. Layer 5: Azure Icon Accuracy (PlantUML only)
   ↓ [WARNINGS] → Log for improvement (non-blocking)
   ↓ [CONTINUE]
7. Store diagram in database ✅
```

**Retry Budget**: Max 3 total retries per diagram (FR-021). Retries consumed by syntax, semantic, or C4 validation failures. After 3 failed attempts, return error to user with accumulated feedback.

**Performance Impact**: 
- Syntax validation: <100ms (local library call)
- Semantic validation: ~2-4s (LLM API call)
- Visual quality: <50ms (local parsing)
- C4 compliance: <50ms (local rule checking)
- Azure icon validation: <100ms (local pattern matching)
- **Total overhead**: ~2-5s per diagram (acceptable within SC-001 30s budget)

**Services to Implement**:
1. `backend/app/services/diagram/syntax_validator.py` (Layer 1)
2. `backend/app/services/diagram/semantic_validator.py` (Layer 2)
3. `backend/app/services/diagram/visual_quality_checker.py` (Layer 3)
4. `backend/app/services/diagram/c4_compliance_validator.py` (Layer 4)
5. `backend/app/services/diagram/azure_icon_validator.py` (Layer 5)
6. `backend/app/services/diagram/validation_pipeline.py` (orchestrates all layers)

**Integration**: `diagram_generator.py` calls `validation_pipeline.validate_diagram()` after each LLM generation before storage.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations** - All constitution principles pass. Separate LLM client and database are architectural choices for isolation/scaling, not principle violations. Diagram quality validation adds necessary quality assurance without violating YAGNI (required for user acceptance per critical requirement).
