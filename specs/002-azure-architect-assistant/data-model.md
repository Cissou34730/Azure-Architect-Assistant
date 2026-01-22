# Data Model: Azure Architect Assistant (AAA)

This feature uses the existing `Project` / `ProjectDocument` / `ProjectState` persistence model.

## Persistence Strategy

- **Primary persisted artifact store**: `ProjectState.state` (JSON string) in `backend/app/models/project.py`.
- **Stable IDs**: All AAA artifacts stored in state must have a stable `id` (UUID string).
- **Validation**: Use Pydantic models to validate state reads/writes at API/service boundaries.

## Entities (Logical)

These are the logical entities required by the spec. The initial implementation stores them inside `ProjectState.state`.

### Requirement

- `id: string`
- `category: "business" | "functional" | "nfr"`
- `text: string`
- `ambiguity: { isAmbiguous: boolean, notes?: string }`
- `sources: Array<{ documentId?: string, fileName?: string, excerpt?: string }>`

### Assumption

- `id: string`
- `text: string`
- `status: "open" | "confirmed" | "rejected"`
- `relatedRequirementIds: string[]`

### ClarificationQuestion

- `id: string`
- `question: string`
- `status: "open" | "answered" | "deferred"`
- `relatedRequirementIds: string[]`

### CandidateArchitecture

- `id: string`
- `title: string`
- `summary: string`
- `assumptionIds: string[]`
- `diagramIds: string[]`
- `sourceCitations: SourceCitation[]`

### ADR

- `id: string`
- `title: string`
- `status: "draft" | "accepted" | "rejected" | "superseded"`
- `context: string`
- `decision: string`
- `consequences: string`
- `relatedRequirementIds: string[]`
- `relatedMindMapNodeIds: string[]`
- `sourceCitations: SourceCitation[]`
- `supersedesAdrId?: string`

### WAFChecklist

- `version?: string`
- `items: Array<WAFChecklistItem>`

### WAFChecklistItem

- `id: string`
- `pillar: "reliability" | "security" | "cost" | "operationalExcellence" | "performanceEfficiency"`
- `topic: string`
- `status: "covered" | "partial" | "notCovered"`
- `evidenceLinks: string[]` (diagram ids, ADR ids, finding ids)
- `updatedAt: string` (ISO)

### Finding

- `id: string`
- `severity: "critical" | "high" | "medium" | "low" | "info"`
- `title: string`
- `description: string`
- `remediation: string`
- `wafPillar?: string`
- `relatedMindMapNodeIds: string[]`
- `sourceCitations: SourceCitation[]`

### Diagram

- `id: string`
- `type: string` (e.g., `c4_context`, `c4_container`, `mermaid`)
- `source: string`
- `version: number`
- `supersedesDiagramId?: string`
- `updatedAt: string` (ISO)

**Versioning rule**: Diagram updates MUST be append-only (new diagram record with incremented version) with an optional `supersedesDiagramId` pointer.

### IaCArtifact

- `id: string`
- `format: "bicep" | "terraform"`
- `files: Array<{ path: string, content: string }>`
- `validation: { status: "pass" | "fail", details?: string }`
- `sourceCitations: SourceCitation[]`

### CostEstimate

- `id: string`
- `currency: string`
- `period: "monthly" | "yearly"`
- `lineItems: Array<{ service: string, sku?: string, estimatedCost: number, notes?: string }>`
- `assumptions: string[]`

Baseline pricing + variance (SC-007):

- `baseline: { source: "azureRetailPricesApi", totalEstimatedCost?: number, currency?: string, retrievedAt?: string }`
- `variancePct?: number`
- `pricingGaps?: Array<{ service: string, reason: string }>`

### TraceabilityLink

- `id: string`
- `fromType: string`
- `fromId: string`
- `toType: string`
- `toId: string`

### MindMapTopic + Coverage

- **Mind map source of truth**: `/docs/arch_mindmap.json`
- `mindMapCoverage: Array<{ nodeId: string, title: string, status: "addressed" | "partial" | "notAddressed", linkedArtifactIds: string[] }>`

### ReferenceDocument

- `id: string`
- `category: string` (WAF, CAF, Architecture Center, etc.)
- `title: string`
- `url?: string`
- `accessedAt: string` (ISO)

### MCPQuery

- `id: string`
- `queryText: string`
- `phase: "architecture" | "validation" | "iac" | "other"`
- `resultUrls: string[]`
- `selectedSnippets?: string[]`
- `executedAt: string` (ISO)

### SourceCitation

- `id: string`
- `kind: "referenceDocument" | "mcp"`
- `referenceDocumentId?: string`
- `mcpQueryId?: string`
- `url?: string`
- `note?: string`

## ProjectState JSON Shape (Proposed)

At minimum, `ProjectState.state` should include:

- `requirements: Requirement[]`
- `assumptions: Assumption[]`
- `clarificationQuestions: ClarificationQuestion[]`
- `candidateArchitectures: CandidateArchitecture[]`
- `adrs: ADR[]`
- `wafChecklist: WAFChecklist`
- `findings: Finding[]`
- `diagrams: Diagram[]`
- `iacArtifacts: IaCArtifact[]`
- `costEstimates: CostEstimate[]`
- `traceabilityLinks: TraceabilityLink[]`
- `mindMap: { version: string, coverage: MindMapCoverageItem[] }`
- `referenceDocuments: ReferenceDocument[]`
- `mcpQueries: MCPQuery[]`

Ingestion metrics (SC-004):

- `projectDocumentStats: { attemptedDocuments: number, parsedDocuments: number, failedDocuments: number, failures: Array<{ documentId?: string, fileName: string, reason: string }> }`

Iteration events (SC-010):

- `iterationEvents: Array<{ id: string, kind: "propose" | "challenge", text: string, citations: SourceCitation[], architectResponseMessageId?: string, createdAt: string, relatedArtifactIds: string[] }>`
