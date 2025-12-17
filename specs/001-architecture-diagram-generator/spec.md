# Feature Specification: Architecture Diagram Generator

**Feature Branch**: `001-architecture-diagram-generator`  
**Created**: 2025-12-17  
**Status**: Draft  
**Input**: User description: "I need to build a feature that will take an input a description of functional requirements or technical design description. The features needs to build first mermaid schema for the functional requirements. Derive from the description we need then to have C4 approach and build C1 and C2 mermaid schemas. In addition the feature must provide a way to generation PlantUML documents that will shows Azure icons use for the describe architecture. The mermaid and PlantUML will be generated at multiple stage of the infrastructure and must be kept up to date when the architecture or requirements change. The schema should be versioned and be referenced with the architecture (ADR id). We should be able to manage them through the frontend. We must be able to see the images as a whole in the front end and be able to integrate it in the project state or architecture document if we like. The features must review and state the ambiguity from the functional specs or tech architecture description."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate Functional Requirements Diagram (Priority: P1)

An architect provides a text description of functional requirements or technical design. The system analyzes the description, identifies ambiguities, and generates a Mermaid diagram visualizing the functional flow.

**Why this priority**: Core value proposition - ability to visualize requirements from text. Without this, no other stories can deliver value.

**Independent Test**: Can be fully tested by submitting a functional requirements description and receiving a generated Mermaid diagram with identified ambiguities. Delivers immediate value of visualization.

**Acceptance Scenarios**:

1. **Given** a text description of functional requirements, **When** the architect submits the description, **Then** the system generates a Mermaid diagram representing the functional flow
2. **Given** a requirements description with unclear elements, **When** the system processes it, **Then** the system identifies and lists all ambiguities with specific references to unclear portions
3. **Given** a generated diagram, **When** the architect views it, **Then** the diagram is rendered as an image in the frontend

---

### User Story 2 - Generate C4 Context and Container Diagrams (Priority: P1)

From the same input description, the system generates C4 Level 1 (Context) and Level 2 (Container) diagrams in Mermaid format, showing system boundaries and major components.

**Why this priority**: Essential architectural view needed alongside functional diagrams. Part of core MVP for architecture visualization.

**Independent Test**: Can be tested by providing an architecture description and receiving both C1 and C2 C4 diagrams in Mermaid format. Delivers complete architectural context independently.

**Acceptance Scenarios**:

1. **Given** a technical design description, **When** the architect requests C4 diagrams, **Then** the system generates both Context (C1) and Container (C2) diagrams in Mermaid format
2. **Given** generated C4 diagrams, **When** the architect views them, **Then** both diagrams are rendered side-by-side in the frontend
3. **Given** a description with system boundaries, **When** C4 diagrams are generated, **Then** external systems and internal containers are clearly differentiated

---

### User Story 3 - Generate Azure-Specific PlantUML Diagrams (Priority: P2)

The system generates PlantUML diagrams using Azure service icons based on the architecture description, providing cloud-specific visualization.

**Why this priority**: Adds cloud-specific detail but functional/C4 diagrams provide sufficient value without it. Can be added after core visualization works.

**Independent Test**: Can be tested by submitting Azure architecture description and receiving PlantUML diagram with Azure icons. Delivers cloud-specific value independently.

**Acceptance Scenarios**:

1. **Given** an architecture description mentioning Azure services, **When** the architect requests PlantUML generation, **Then** the system generates PlantUML code using appropriate Azure service icons
2. **Given** generated PlantUML code, **When** the architect views it, **Then** the diagram is rendered with recognizable Azure service icons
3. **Given** a multi-service Azure architecture, **When** PlantUML is generated, **Then** all mentioned Azure services appear with correct icons and relationships

---

### User Story 4 - Version and Link Diagrams to ADRs (Priority: P2)

Each generated diagram is versioned and can be linked to an Architecture Decision Record (ADR) ID for traceability.

**Why this priority**: Important for governance but not required for initial visualization value. Can track versions manually initially.

**Independent Test**: Can be tested by generating a diagram, assigning it a version and ADR reference, then retrieving it by version/ADR. Delivers traceability independently.

**Acceptance Scenarios**:

1. **Given** a newly generated diagram, **When** the system saves it, **Then** the diagram receives a version number (e.g., v1.0.0)
2. **Given** a diagram with a version, **When** the architect links it to an ADR, **Then** the ADR ID is associated with that diagram version
3. **Given** multiple versions of a diagram, **When** the architect views version history, **Then** all versions are listed with their ADR references and timestamps
4. **Given** an ADR ID, **When** the architect searches for associated diagrams, **Then** all diagrams linked to that ADR are displayed

---

### User Story 5 - Manage and Update Diagrams Through Frontend (Priority: P3)

Architects can view, edit inputs, regenerate, and manage all diagrams through a frontend interface. When requirements or architecture change, diagrams can be regenerated to stay current.

**Why this priority**: Quality-of-life improvement. Initial versions can be generated via API/backend without full UI management.

**Independent Test**: Can be tested by using the frontend to create, view, update, and delete diagrams. Delivers complete self-service capability independently.

**Acceptance Scenarios**:

1. **Given** the frontend diagram management page, **When** the architect views it, **Then** all existing diagrams are listed with their types, versions, and ADR links
2. **Given** an existing diagram, **When** the architect updates the input description, **Then** the system regenerates the diagram while preserving version history
3. **Given** a changed architecture description, **When** diagrams are regenerated, **Then** the system highlights what changed between versions
4. **Given** multiple diagram types for one architecture, **When** the architect views them, **Then** all related diagrams (Mermaid functional, C4, PlantUML) are grouped together

---

### User Story 6 - Integrate Diagrams into Project Documents (Priority: P3)

Generated diagrams can be exported or embedded into project documentation and architecture documents.

**Why this priority**: Nice-to-have for documentation automation. Initial versions can copy/paste manually.

**Independent Test**: Can be tested by generating a diagram and exporting it in a document-compatible format. Delivers documentation integration independently.

**Acceptance Scenarios**:

1. **Given** a generated diagram, **When** the architect selects "Export", **Then** the system provides the diagram in multiple formats (PNG, SVG, Markdown embed)
2. **Given** a project document template, **When** the architect embeds a diagram, **Then** the diagram appears with its version number and ADR reference
3. **Given** updated diagram versions, **When** embedded in documents, **Then** the system can update all references to use the latest version

---

### Edge Cases

- What happens when the input description is too vague to generate meaningful diagrams?
- How does the system handle descriptions that mention non-Azure cloud services when generating PlantUML?
- What happens when the architect requests C4 diagrams but the description doesn't contain sufficient architectural detail?
- How are diagrams managed when an ADR is deleted or its ID changes?
- What happens when Mermaid or PlantUML generation fails due to syntax errors? (System validates and retries up to 3 times with error feedback before failing)
- How does versioning work when multiple architects make concurrent changes to the same diagram? (Pessimistic locking ensures only one architect can edit at a time)
- What happens when Azure service icons are not available in PlantUML for mentioned services?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST add new REST API router endpoints to the existing FastAPI backend that accept text descriptions of functional requirements and technical designs, along with optional ADR identifiers
- **FR-002**: System MUST analyze input descriptions using LLM-powered analysis (GPT-4/Claude) combined with pattern matching to identify ambiguous or unclear elements
- **FR-003**: System MUST generate Mermaid diagrams representing functional requirements from input descriptions
- **FR-004**: System MUST generate C4 Level 1 (Context) Mermaid diagrams from architecture descriptions
- **FR-005**: System MUST generate C4 Level 2 (Container) Mermaid diagrams from architecture descriptions
- **FR-006**: System MUST generate PlantUML diagrams with Azure service icons from architecture descriptions
- **FR-007**: System MUST version each generated diagram using semantic versioning (e.g., v1.0.0)
- **FR-008**: System MUST accept ADR identifiers via API and link them to generated DiagramSets
- **FR-009**: System MUST store and maintain version history for all diagrams, including generated Mermaid source, PlantUML source, and rendered SVG/PNG images
- **FR-010**: System MUST provide Mermaid diagram source code to the frontend, where it will be rendered by a React component
- **FR-011**: System MUST render PlantUML diagrams as SVG/PNG images server-side for frontend display
- **FR-012**: Frontend MUST display all generated diagrams for an architecture together
- **FR-013**: System MUST allow architects to update input descriptions and regenerate diagrams
- **FR-014**: System MUST preserve previous versions when diagrams are regenerated
- **FR-015**: System MUST export Mermaid diagrams as source code, and PlantUML diagrams in source code, SVG, and PNG formats
- **FR-016**: System MUST highlight differences between diagram versions
- **FR-017**: System MUST track which Azure services are mentioned in descriptions for PlantUML icon mapping
- **FR-018**: System MUST provide REST API endpoints that documents can call to retrieve diagram images and metadata for dynamic inclusion
- **FR-019**: System MUST list all ambiguities found in input descriptions with specific references
- **FR-020**: System MUST allow filtering/searching diagrams by ADR ID (exact match, case-sensitive), version (exact match, semantic versioning format), or creation date (range queries with ISO 8601 format). Filtering uses query parameters on GET /api/v1/diagram-sets endpoint (e.g., `?adr_id=ADR-001&created_after=2025-01-01T00:00:00Z`). Multiple filters combine with AND logic.
- **FR-021**: When diagram generation produces invalid syntax, system MUST validate the output, provide error context to the LLM, and retry generation up to 3 times before returning an error to the calling application
- **FR-022**: System MUST implement pessimistic locking for diagram updates, allowing only one architect to edit a diagram at a time while others have read-only access

### Key Entities

- **DiagramSet**: Represents all diagrams generated from a single architecture description. Contains multiple diagram types (functional Mermaid, C4 C1/C2, PlantUML), version history, ADR references, and creation/update timestamps.

- **Diagram**: Individual diagram instance with type (functional/C4-context/C4-container/PlantUML), source code (Mermaid or PlantUML), version number, and link to parent DiagramSet. For PlantUML diagrams, also includes rendered SVG/PNG images; Mermaid diagrams are rendered client-side by React component.

- **InputDescription**: Text description of requirements or architecture provided by architect. Includes raw text, identified ambiguities, and references to generated DiagramSets.

- **AmbiguityReport**: List of unclear elements found in InputDescription with specific text references, suggested clarifications, and resolution status.

- **ADRReference**: Architecture Decision Record identifier linked to DiagramSets for traceability. Contains ADR ID, title, and relationship type.

- **DiagramVersion**: Historical record of diagram changes including version number, timestamp, author, change description, and previous version reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Architects can generate functional requirement diagrams from text descriptions in under 30 seconds
- **SC-002**: System identifies at least 80% of ambiguities that human reviewers would flag in requirements descriptions
- **SC-003**: Generated C4 diagrams accurately represent system boundaries and components as verified by architect review in 90% of cases
- **SC-004**: PlantUML diagrams correctly map 95% of mentioned Azure services to appropriate icons
- **SC-005**: Diagram versioning maintains complete history with zero data loss across updates
- **SC-006**: Frontend displays all diagram types for an architecture on a single page with load time under 3 seconds
- **SC-007**: Architects can successfully integrate generated diagrams into documentation in under 5 minutes
- **SC-008**: System reduces time to create architecture diagrams by 70% compared to manual creation

## Assumptions

- Input descriptions are provided in English
- This feature integrates into the existing unified FastAPI backend as a new router module
- Feature reuses existing backend infrastructure (database connections, LLM service, lifecycle management)
- Main project provides ADR identifiers when available; this service does not directly integrate with ADR storage
- Standard C4 modeling conventions are followed (Context and Container levels only, not Component or Code levels)
- Azure service catalog is relatively stable and icon mappings can be maintained
- Mermaid and PlantUML rendering libraries are available and maintained
- Architects have basic understanding of C4 modeling and diagram types
- Document integration mechanism exists or can be developed separately
- Version control follows semantic versioning principles

## Clarifications

### Session 2025-12-17

- Q: How should the system detect ambiguities in input descriptions? → A: LLM-powered analysis with pattern matching (queries GPT-4/Claude to identify unclear requirements)
- Q: How does this feature integrate with the ADR system and main project? → A: The main project has to call an API with the ADR or the description of the spec or functional req and this features generate and store the mermaid, plantUML and svg
- Q: What happens when Mermaid or PlantUML generation fails due to syntax errors? → A: Retry with validation feedback (validate syntax, retry LLM generation with error context up to 3 times)
- Q: How does versioning work when multiple architects make concurrent changes to the same diagram? → A: Pessimistic locking (only one architect can edit at a time, others see read-only)
- Q: How are Mermaid diagrams rendered in the frontend? → A: The mermaid will be displayed as it, in the correct React component by the frontend
- Q: Should the diagram generator be a separate microservice or integrated into the existing FastAPI backend? → A: Integrate as new router in existing FastAPI app at `backend/app/routers/diagram_generation/` with services in `backend/app/services/diagram/` (reuses existing infrastructure, follows established patterns)
- Q: Should diagram services reuse the existing `llm_service.py` or create a separate LLM client? → A: Create separate LLM client in `backend/app/services/diagram/llm_client.py` with diagram-specific configuration and prompt handling
- Q: Should diagram entities use the existing `projects.db` or a separate database? → A: Create separate `diagrams.db` with its own session factory for isolation and independent scaling
