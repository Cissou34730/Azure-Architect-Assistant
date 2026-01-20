# Feature Specification: Azure Architect Assistant (AAA)

**Feature Branch**: `002-azure-architect-assistant`  
**Created**: 2026-01-08  
**Status**: Draft  
**Input**: User description summarizing the Azure Architect Assistant manifesto and process

## Clarifications

### Session 2026-01-08

- Q: Should human edits be authoritative with the agent detecting and merging without overwriting manual changes? → A: Human edits are authoritative; agent detects/merges without overwriting manual changes.
- Q: Should the agent iterate on architecture by proactively proposing, challenging, and highlighting solutions using all available resources? → A: Yes, the agent must leverage all resources (mind map, WAF checklists, MCP/official docs, diagrams) to propose/challenge/highlight options and iterate with the architect.
- Q: Should the implementation plan be regenerated from scratch to align closely with spec structure and traceability? → A: Regenerate plan from spec (clean slate), ensuring all spec requirements are explicitly covered and traceability is preserved.
- Q: Must the agent rely on reference documents and MCP servers as non-negotiable resources for architectural reasoning? → A: Yes, the agent MUST consult all reference documents (Azure WAF, CAF, Architecture Center, Cloud Design Patterns, security benchmarks, IaC docs, etc.) and MCP servers (Microsoft Learn) to propose, challenge, and validate architecture; the agent is a document-driven assistant, not just a workflow executor.
- Q: Where is the authoritative definition of the 13-topic mind map structure? → A: The mind map structure is defined in `/docs/arch_mindmap.json` (329 lines, 13 top-level topics with hierarchical subtopics); this file MUST be loaded at system initialization and used as the invariant reasoning backbone throughout the architecture lifecycle.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest & Extract Requirements (Priority: P1)

Transform uploaded PDFs/Markdown/Excel/free text into normalized content with structured business needs, functional and non-functional requirements, and an initial C4 context diagram.

**Why this priority**: Foundation for all downstream architecture activities; no other step is possible without structured requirements.

**Independent Test**: Upload mixed-format sources and verify normalized text, categorized requirements, ambiguity markers, and a generated C4 L1 diagram are produced without manual editing.

**Acceptance Scenarios**:

1. **Given** heterogeneous documents, **When** ingestion runs, **Then** normalized text and categorized requirements (business/functional/NFR) are available with ambiguities flagged.
2. **Given** the first ingestion pass, **When** diagrams are requested, **Then** a C4 L1 context diagram is generated and attached to the project state.

---

### User Story 2 - Candidate Architectures (Priority: P1)

Generate at least one candidate Azure architecture (optionally a second variant) with explicit assumptions and links to requirements, updating diagrams and WAF baseline.

**Why this priority**: Provides an initial solution hypothesis to discuss and iterate, unlocking early validation.

**Independent Test**: From an ingested project, request candidate architecture and verify produced options, assumptions, updated C4 L1/L2 diagrams, and WAF checklist initialization.

**Acceptance Scenarios**:

1. **Given** structured requirements, **When** candidate generation is triggered, **Then** a candidate architecture with assumptions and rationale is stored with diagrams.
2. **Given** the candidate, **When** WAF initialization runs, **Then** Reliability/Performance/Cost pillars are populated with covered/partial/not-covered statuses.

---

### User Story 3 - Decisions & ADRs (Priority: P2)

Create and manage ADRs that record architectural decisions, their status, and links to requirements, checklists, and diagrams.

**Why this priority**: Decisions must be explicit and traceable to support governance and future changes.

**Independent Test**: Create an ADR from a decision, change status (draft/accepted/superseded), and verify traceability links to requirements and mind map topics.

**Acceptance Scenarios**:

1. **Given** a proposed decision, **When** an ADR is created, **Then** it records context, decision, consequences, and references to related requirements and diagrams.
2. **Given** a superseded decision, **When** ADR status is updated, **Then** the new ADR references the superseded one and traceability links are updated.

---

### User Story 4 - Validation & Findings (Priority: P2)

Validate the candidate architecture against WAF (all pillars) and security baselines, producing findings with severity and remediation suggestions.

**Why this priority**: Ensures risks and gaps are exposed early without blocking the architect’s judgment.

**Independent Test**: Run validation and confirm findings list includes severity, impacted components, and WAF pillar/topic references; no automatic rejection occurs.

**Acceptance Scenarios**:

1. **Given** an architecture state, **When** validation runs, **Then** findings are produced with severity, WAF pillar/topic, and suggested mitigations.
2. **Given** WAF checklists, **When** validation completes, **Then** checklist items update to reflect covered/partial/not covered with timestamps.

---

### User Story 5 - IaC & Costs (Priority: P3)

Generate IaC (Bicep and/or Terraform) aligned with the validated architecture and produce an Azure cost estimate with key drivers noted.

**Why this priority**: Moves architecture toward execution and cost transparency.

**Independent Test**: Generate IaC and verify lint/validate passes; generate cost estimate and confirm key service costs and assumptions are recorded.

**Acceptance Scenarios**:

1. **Given** a validated architecture, **When** IaC generation is requested, **Then** Bicep/Terraform files are produced and pass static validation.
2. **Given** service selections, **When** cost estimation runs, **Then** a cost breakdown with major services and assumptions is stored and linked to the architecture.

---

### User Story 6 - Mind Map & Traceability (Priority: P3)

Maintain the 13-topic architecture mind map as the reasoning backbone and provide end-to-end traceability chains across inputs, requirements, decisions, diagrams, WAF, IaC, and costs.

**Why this priority**: Ensures completeness, navigability, and auditability of the architecture reasoning.

**Independent Test**: Navigate from a requirement to its ADR, diagram, WAF items, IaC, and cost entries; confirm all 13 topics are touched at least once.

**Acceptance Scenarios**:

1. **Given** a requirement, **When** traceability is queried, **Then** linked ADRs, diagrams, WAF items, IaC components, and costs are returned with stable IDs.
2. **Given** the mind map, **When** coverage is viewed, **Then** each top-level topic shows addressed/partial/not-addressed status with references.

---

### User Story 7 - Document-Driven Iteration (Priority: P1)

Agent proactively queries reference documents (Azure WAF, CAF, Architecture Center, Cloud Design Patterns, MCP/Microsoft Learn) during each iteration to propose options, challenge decisions, and validate choices, documenting consulted sources in artifacts.

**Why this priority**: Agent acts as an architectural reasoning partner grounded in authoritative Azure sources, not just a workflow executor; this is the core value proposition.

**Independent Test**: During candidate generation or validation, verify agent cites specific reference documents (e.g., WAF pillar, Cloud Design Pattern, MCP doc URL) in proposals/challenges and records them in ADRs/findings.

**Acceptance Scenarios**:

1. **Given** a candidate architecture, **When** agent proposes an alternative, **Then** the proposal references specific documents (e.g., "Azure Architecture Center: Event-Driven pattern") and MCP query results.
2. **Given** a validation run, **When** findings are generated, **Then** each finding cites the consulted reference (e.g., WAF Reliability checklist item, Security Benchmark control) with source links.

---

### Edge Cases

- Ingested documents contain conflicting requirements or outdated versions.
- Inputs include unsupported formats or corrupted files.
- Security or compliance requirements are missing or implicitly stated.
- WAF checklist topics remain unaddressed after validation runs.
- Decisions are reversed; superseded ADRs must keep traceability without losing history.
- IaC generation encounters unsupported Azure services or SKU availability constraints in target regions.
- Manual edits by the architect and agent-generated updates may conflict; the agent must not overwrite human changes.
- Iteration pulls conflicting guidance from different sources (WAF vs. MCP docs vs. prior ADRs); conflicts must be surfaced without auto-selection.
- MCP server queries return no results or irrelevant content; agent must document failed lookups and request architect clarification.
- Reference documents are outdated or deprecated; agent must flag version/date concerns when consulting older sources.

## Reference Documents *(mandatory)*

The agent MUST consult these document categories throughout the architecture lifecycle. This is non-negotiable.

### Architecture Mind Map (Foundational)

- **File**: `/docs/arch_mindmap.json` (329 lines)
- **Structure**: 13 top-level topics with hierarchical subtopics covering software architecture fundamentals
- **Usage**: Loaded at initialization; used as reasoning backbone to structure coverage, identify gaps, and prompt architects about uncovered areas
- **Topics**:
  1. Foundations (definitions, principles, documentation)
  2. Requirements & Quality Attributes (performance, reliability, security, cost)
  3. Domain & Design (DDD, strategic/tactical design - reference only, not prescriptive)
  4. Architecture Styles (monoliths, microservices, event-driven, serverless)
  5. Data & Storage (modeling, transactions, caching, analytics)
  6. Integration & Distributed Systems (communication, messaging, reliability patterns)
  7. Cloud & Infrastructure (deployment models, computing, networking, IaC)
  8. Security & Compliance (identity, application security, data protection)
  9. Delivery & Lifecycle (environments, CI/CD, testing)
  10. Observability & Reliability (telemetry, monitoring, SLOs)
  11. Organization & Process (team structures, ways of working)
  12. Practice Ideas (architecture notes, design reviews)
  13. Learning & Practice (career stages, reading lists)

### Azure Frameworks & References
- Azure Well-Architected Framework (WAF) - all pillars and checklists
- Azure Cloud Adoption Framework (CAF)
- Azure Reliability Guidance
- Azure Security Benchmark (ASB)

### Azure Architecture & Patterns
- Azure Architecture Center
- Microsoft Cloud Design Patterns
- Azure Services Documentation (per-service best practices)
- Azure Naming & Tagging Guidelines

### Data & AI (when applicable)
- Microsoft Fabric Architecture
- Azure OpenAI Service Documentation
- Retrieval-Augmented Generation (RAG) on Azure
- Medallion Architecture

### Network & Infrastructure
- Hub-spoke network topology in Azure
- Azure Virtual WAN
- Private Link & DNS Integration
- Azure Firewall Architecture

### Identity, Security & Governance
- Microsoft Entra ID Architecture
- Azure Key Vault
- Microsoft Defender for Cloud
- Azure Policy
- Azure Web Application Firewall

### Infrastructure as Code & Delivery
- Bicep Documentation
- Terraform AzureRM Provider
- Azure DevOps YAML Schema
- Azure Pricing APIs

### Representation & Documentation
- C4 Model
- Mermaid syntax
- PlantUML
- Structurizr DSL

### Non-Prescriptive Methodologies
- TOGAF Standard (reference only, not mandatory)
- 12-Factor App (reference only, not mandatory)

### MCP Server Usage

The agent MUST query MCP servers (Microsoft Learn, code samples) using explicit search patterns:
- **Architecture Phase**: Query "Azure {service} architecture patterns", "Azure {pattern-name} implementation"
- **Validation Phase**: Query "Azure Well-Architected Framework {pillar} {topic}", "Azure Security Benchmark {control-id}"
- **IaC Phase**: Query "Bicep {resource-type} template", "Terraform azurerm {resource} example" with language filters
- **All Phases**: Document query terms, result URLs, and consulted content in artifacts

### Excluded Documents
- Domain-Driven Design (DDD)
- Hexagonal / Clean / Onion Architecture
- Any non-Azure cloud platforms (AWS, GCP, on-premises)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST ingest PDF, Markdown, Excel, and free text, normalizing them into a single project corpus.
  - For PDF/Excel inputs, “ingest” means extracting human-readable text sufficient for requirements extraction.
  - If extraction fails for a document, the system MUST record the failure reason and continue processing remaining inputs.
- **FR-002**: The system MUST extract business needs, functional requirements, and non-functional requirements, marking ambiguities and gaps explicitly.
- **FR-003**: The system MUST generate and iteratively update a C4 Level 1 context diagram immediately after the first ingestion.
- **FR-004**: The system MUST propose at least one candidate Azure architecture (and optionally an alternative) with explicit assumptions and rationale.
- **FR-005**: The system MUST initialize and maintain Azure WAF checklists across all pillars, tracking covered/partial/not-covered states.
- **FR-006**: The system MUST produce prioritized clarification questions based on detected ambiguities or missing data.
- **FR-007**: The system MUST support full ADR lifecycle (draft/accepted/rejected/superseded) with traceability to requirements, mind map topics, and diagrams.
- **FR-008**: The system MUST validate architectures against WAF and security baselines, generating findings with severity and remediation suggestions.
- **FR-009**: The system MUST maintain end-to-end traceability chains linking inputs → requirements → assumptions/questions → candidate architectures → ADRs → diagrams → WAF items → IaC → costs.
- **FR-010**: The system MUST generate IaC (Bicep and/or Terraform) aligned with the approved architecture and pass static validation checks.
- **FR-011**: The system MUST produce a cost estimate with key cost drivers, assumptions, and linkage to architectural components.
- **FR-012**: The system MUST allow export of project artifacts (requirements, ADRs, diagrams, WAF checklists, IaC, costs) while preserving traceability links.
- **FR-013**: The system MUST treat human edits to artifacts as authoritative, detecting and merging agent updates without overwriting manual changes, and surfacing conflicts for review.
- **FR-014**: The system MUST support iterative architecture sessions where the agent proactively proposes, challenges, and highlights solutions using all available resources (mind map, WAF checklists, MCP/official docs, diagrams), capturing architect responses and updating artifacts accordingly.
- **FR-015**: The system MUST consult reference documents (Azure WAF, CAF, Reliability Guidance, Security Benchmark, Architecture Center, Cloud Design Patterns, Azure Services docs, IaC docs) for every architecture proposal, validation, and IaC generation activity, recording consulted sources in artifacts.
- **FR-016**: The system MUST query MCP servers (Microsoft Learn, code samples) with explicit search terms (e.g., "Azure Event Hub architecture pattern", "Bicep virtual network template") during candidate generation, validation, and IaC generation, capturing query results and source URLs in artifacts.
- **FR-017**: The system MUST document which reference documents and MCP queries were consulted for each ADR, finding, and IaC artifact, enabling audit trails of reasoning sources.
- **FR-018**: The system MUST NOT auto-select solutions when reference documents provide conflicting guidance; instead, it MUST present options with trade-offs and source references for architect decision.
- **FR-019**: The system MUST load the architecture mind map structure from `/docs/arch_mindmap.json` at initialization, validating the presence of all 13 top-level topics and their hierarchical subtopics.
- **FR-020**: The system MUST track coverage of each mind map topic (addressed/partial/not-addressed) throughout the architecture lifecycle, linking requirements, ADRs, diagrams, and findings to specific mind map nodes.
- **FR-021**: The system MUST use mind map topics as structured prompts during iterative sessions, proactively asking architects about uncovered topics (e.g., "Topic 8.4 Data Protection & Privacy shows no coverage; should we address encryption at rest/in transit?").

### Key Entities *(include if feature involves data)*

- **Requirement**: Business, functional, and non-functional statements with ambiguity markers and sources.
- **Assumption**: Hypotheses recorded during design, each linked to impacted requirements and decisions.
- **ClarificationQuestion**: Questions raised from gaps/ambiguities with status (open/answered/deferred).
- **CandidateArchitecture**: Proposed solution with assumptions, rationale, and linked diagrams.
- **ADR**: Architectural decision record with status (draft/accepted/rejected/superseded) and links to requirements, mind map topics, and findings.
- **WAFChecklistItem**: Pillar/topic item with coverage state (covered/partial/not covered) and evidence links.
- **Finding**: Validation output with severity, impacted components, and suggested remediation.
- **Diagram**: C4/Mermaid artifacts with version and linked components.
- **IaCArtifact**: Generated Bicep/Terraform modules and validation status.
- **CostEstimate**: Cost breakdown with assumptions and linkage to services/components.
- **TraceabilityLink**: Stable identifiers connecting upstream and downstream artifacts.
- **MindMapTopic**: One of 13 invariant architecture topics loaded from `/docs/arch_mindmap.json`, with hierarchical subtopics (e.g., 2.1 Requirements, 2.2 Performance & Scalability), coverage status (addressed/partial/not-addressed), and references to linked artifacts.
- **ReferenceDocument**: Categorized Azure reference (WAF/CAF/Architecture Center/etc.) with usage timestamps and linked artifacts.
- **MCPQuery**: Recorded MCP server query with search terms, results, source URLs, and linked artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of top-level mind map topics show at least one linked artifact or note (addressed/partial) in the project state.
- **SC-002**: WAF checklists for all pillars are initialized and updated per validation run, with no pillar left untracked.
- **SC-003**: First C4 Level 1 context diagram is produced within the initial ingestion iteration and remains versioned through updates.
- **SC-004**: 95% of ingested documents are parsed without errors; any failures are logged with reasons and surfaced for remediation.
- **SC-005**: 100% of recorded decisions have ADRs linked to originating requirements.
  - When available, an ADR SHOULD also link to at least one diagram and/or WAF evidence item.
  - When no diagram/WAF link is available yet, the ADR MUST record an explicit reason.
- **SC-006**: Generated IaC artifacts pass static validation (lint/format/check) with 0 critical errors prior to delivery.
- **SC-007**: Cost estimates include all major Azure services in the architecture and document assumptions.
  - Baseline pricing MUST be automatically retrieved via the Azure Retail Prices (Pricing) API.
  - The system MUST compute and record variance against the baseline, with target within ±15%, only when the estimate includes the minimal required usage inputs to price each major service line item.
  - Minimal required usage inputs are service-dependent (e.g., hours, GB-month, requests/transactions) and MUST be recorded as explicit assumptions per line item.
  - Any pricing gaps (missing meters/SKUs/usage inputs) MUST be recorded as explicit assumptions and excluded from the variance calculation. If variance cannot be meaningfully computed due to gaps, the system SHOULD omit `variancePct` rather than report a misleading value.
- **SC-008**: End-to-end traceability exports include links from requirements to ADRs, WAF items, IaC, and costs with no broken references in spot checks.
- **SC-009**: No architect-authored content is overwritten by agent updates; detected conflicts are reported and require human confirmation.
- **SC-010**: Each design iteration records at least one propose/challenge note with linked resources (e.g., WAF topic, MCP doc, diagram) and corresponding architect response, with updated WAF/mind map coverage when applicable.
- **SC-011**: 100% of candidate architectures, ADRs, and findings cite at least one consulted reference document or MCP query result with source identification.
- **SC-012**: MCP queries are recorded with explicit search terms and result URLs; spot checks confirm queries are relevant to architectural decisions being made.
- **SC-013**: The mind map structure from `/docs/arch_mindmap.json` is successfully loaded at initialization with all 13 top-level topics and subtopics validated.
- **SC-014**: Mind map coverage tracking shows at least one artifact (requirement/ADR/diagram/finding) linked to each of the 13 top-level topics by project completion; uncovered topics are explicitly flagged with architect acknowledgment.
