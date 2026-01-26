export interface Project {
  readonly id: string;
  readonly name: string;
  readonly textRequirements?: string;
  readonly createdAt: string;
}

export interface ProjectStateNfrs {
  readonly availability: string;
  readonly security: string;
  readonly performance: string;
  readonly costConstraints: string;
}

export interface ProjectStateAppStructure {
  readonly components: readonly string[];
  readonly integrations: readonly string[];
}

export interface ProjectStateDataCompliance {
  readonly dataTypes: readonly string[];
  readonly complianceRequirements: readonly string[];
  readonly dataResidency: string;
}

export interface ProjectStateTechnicalConstraints {
  readonly constraints: readonly string[];
  readonly assumptions: readonly string[];
}

// AAA Artifact Types
export interface AdrArtifact {
  readonly id: string;
  readonly title: string;
  readonly status: "draft" | "accepted" | "rejected" | "superseded";
  readonly context: string;
  readonly decision: string;
  readonly consequences: string;
  readonly relatedRequirementIds: readonly string[];
  readonly relatedMindMapNodeIds: readonly string[];
  readonly relatedDiagramIds: readonly string[];
  readonly relatedWafEvidenceIds: readonly string[];
  readonly missingEvidenceReason?: string;
  readonly sourceCitations: readonly Record<string, any>[];
  readonly supersedesAdrId?: string;
  readonly createdAt?: string;
}

export interface FindingArtifact {
  readonly id: string;
  readonly title: string;
  readonly severity: "low" | "medium" | "high" | "critical";
  readonly description: string;
  readonly remediation: string;
  readonly wafPillar?: string;
  readonly wafTopic?: string;
  readonly relatedRequirementIds: readonly string[];
  readonly relatedDiagramIds: readonly string[];
  readonly relatedAdrIds: readonly string[];
  readonly relatedMindMapNodeIds: readonly string[];
  readonly sourceCitations: readonly Record<string, any>[];
  readonly createdAt?: string;
}

export interface WafEvaluation {
  readonly id: string;
  readonly status: "covered" | "partial" | "notCovered";
  readonly evidence: string;
  readonly relatedFindingIds: readonly string[];
  readonly sourceCitations: readonly Record<string, any>[];
  readonly createdAt?: string;
}

export interface WafChecklistItem {
  readonly id: string;
  readonly pillar: string;
  readonly topic: string;
  readonly evaluations: readonly WafEvaluation[];
}

export interface WafChecklist {
  readonly version?: string;
  readonly pillars: readonly string[];
  readonly items: readonly WafChecklistItem[];
}

export interface IacFile {
  readonly path: string;
  readonly format: "bicep" | "terraform" | "arm" | "yaml" | "json" | "other";
  readonly content: string;
}

export interface IacValidationResult {
  readonly tool: string;
  readonly status: "pass" | "fail" | "skipped";
  readonly output?: string;
}

export interface IacArtifact {
  readonly id: string;
  readonly createdAt?: string;
  readonly files: readonly IacFile[];
  readonly validationResults: readonly IacValidationResult[];
}

export interface CostLineItem {
  readonly id: string;
  readonly name: string;
  readonly monthlyQuantity: number;
  readonly unitPrice: number;
  readonly monthlyCost: number;
  readonly serviceName?: string;
  readonly productName?: string;
  readonly meterName?: string;
  readonly skuName?: string;
  readonly unitOfMeasure?: string;
}

export interface CostEstimate {
  readonly id: string;
  readonly createdAt?: string;
  readonly currencyCode: string;
  readonly totalMonthlyCost: number;
  readonly lineItems: readonly CostLineItem[];
  readonly pricingGaps: readonly Record<string, any>[];
  readonly baselineReferenceTotalMonthlyCost?: number;
  readonly variancePct?: number;
}

export interface TraceabilityLink {
  readonly id: string;
  readonly fromType: string;
  readonly fromId: string;
  readonly toType: string;
  readonly toId: string;
}

export interface TraceabilityIssue {
  readonly id: string;
  readonly kind: string;
  readonly message: string;
  readonly linkId?: string;
  readonly createdAt?: string;
}

export interface ReferenceDocument {
  readonly id: string;
  readonly category: string;
  readonly title: string;
  readonly url?: string;
  readonly accessedAt: string;
}

export interface MCPQuery {
  readonly id: string;
  readonly queryText: string;
  readonly phase: "architecture" | "validation" | "iac" | "other";
  readonly resultUrls: readonly string[];
  readonly selectedSnippets?: readonly string[];
  readonly executedAt: string;
}

export interface IterationEvent {
  readonly id: string;
  readonly kind: "propose" | "challenge";
  readonly text: string;
  readonly citations: readonly Record<string, any>[];
  readonly architectResponseMessageId?: string;
  readonly createdAt: string;
  readonly relatedArtifactIds: readonly string[];
}

export interface ProjectState {
  readonly projectId: string;
  readonly context: {
    readonly summary: string;
    readonly objectives: readonly string[];
    readonly targetUsers: string;
    readonly scenarioType: string;
  };
  readonly nfrs?: ProjectStateNfrs;
  readonly applicationStructure?: ProjectStateAppStructure;
  readonly dataCompliance?: ProjectStateDataCompliance;
  readonly technicalConstraints: ProjectStateTechnicalConstraints;
  readonly openQuestions: readonly string[];
  readonly lastUpdated: string;

  // AAA Artifacts
  readonly requirements: readonly Record<string, any>[];
  readonly assumptions: readonly Record<string, any>[];
  readonly clarificationQuestions: readonly Record<string, any>[];
  readonly candidateArchitectures: readonly Record<string, any>[];
  readonly adrs: readonly AdrArtifact[];
  readonly wafChecklist: WafChecklist;
  readonly findings: readonly FindingArtifact[];
  readonly diagrams: readonly Record<string, any>[];
  readonly iacArtifacts: readonly IacArtifact[];
  readonly costEstimates: readonly CostEstimate[];
  readonly traceabilityLinks: readonly TraceabilityLink[];
  readonly mindMapCoverage: Record<string, any>;
  readonly traceabilityIssues: readonly TraceabilityIssue[];
  readonly mindMap: Record<string, any>;
  readonly referenceDocuments: readonly ReferenceDocument[];
  readonly mcpQueries: readonly MCPQuery[];
  readonly projectDocumentStats?: Record<string, any>;
  readonly iterationEvents: readonly IterationEvent[];

  // Flat properties for compatibility if needed
  readonly summary?: string;
  readonly objectives?: readonly string[];
  readonly targetUsers?: string;
  readonly scenarioType?: string;
  readonly functionalRequirements?: readonly string[];
  readonly nonFunctionalRequirements?: readonly string[];
  readonly complianceRequirements?: readonly string[];
  readonly dataResidency?: string;
  readonly constraints?: readonly string[];
}

export interface KbSource {
  readonly url: string;
  readonly title: string;
  readonly section: string;
  readonly score: number;
  readonly kbId?: string;
  readonly kbName?: string;
}

export interface Message {
  readonly id: string;
  readonly projectId: string;
  readonly role: "user" | "assistant";
  readonly content: string;
  readonly timestamp: string;
  readonly kbSources?: readonly KbSource[];
}

export interface KbQueryResponse {
  readonly answer: string;
  readonly sources: readonly KbSource[];
  readonly hasResults: boolean;
  readonly suggestedFollowUps?: readonly string[];
}

export interface KbHealthInfo {
  readonly kbId: string;
  readonly kbName: string;
  readonly status: string;
  readonly indexReady: boolean;
  readonly error?: string;
}

export interface KbInfo {
  readonly id: string;
  readonly name: string;
  readonly status: string;
  readonly profiles: readonly string[];
  readonly priority: number;
  readonly indexReady?: boolean;
}

export interface KbListResponse {
  readonly knowledgeBases: readonly KbInfo[];
}

export interface KbHealthResponse {
  readonly overallStatus: string;
  readonly knowledgeBases: readonly KbHealthInfo[];
}

export interface DiagramData {
  readonly id: string;
  readonly diagramType: string;
  readonly sourceCode: string;
  readonly version: string;
  readonly createdAt: string;
}

export interface Ambiguity {
  readonly id: string;
  readonly diagramSetId: string;
  readonly ambiguousText: string;
  readonly suggestedClarification?: string;
  readonly resolved: boolean;
  readonly createdAt: string;
  readonly textFragment?: string; // Optional field used in some components
}

export interface DiagramSetResponse {
  readonly id: string;
  readonly adrId?: string;
  readonly inputDescription: string;
  readonly diagrams: readonly DiagramData[];
  readonly ambiguities: readonly Ambiguity[];
  readonly createdAt: string;
  readonly updatedAt: string;
}
