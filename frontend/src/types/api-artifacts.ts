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
  readonly sourceCitations: readonly SourceCitation[];
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
  readonly sourceCitations: readonly SourceCitation[];
  readonly createdAt?: string;
}

interface WafEvaluation {
  readonly id: string;
  readonly status: "covered" | "partial" | "notCovered";
  readonly evidence: string;
  readonly relatedFindingIds: readonly string[];
  readonly sourceCitations: readonly SourceCitation[];
  readonly createdAt?: string;
}

export interface WafChecklistItem {
  readonly id: string;
  readonly pillar: string;
  readonly topic: string;
  readonly description?: string;
  readonly severity?: "low" | "medium" | "high" | "critical";
  readonly guidance?: readonly string[];
  readonly checklistTitle?: string;
  readonly templateSlug?: string;
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
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Backend returns dynamic gap data
  readonly pricingGaps: readonly Record<string, unknown>[];
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
  readonly url?: string | null;
  readonly mimeType?: string;
  readonly accessedAt?: string;
  readonly parseStatus?: "parsed" | "parse_failed";
  readonly analysisStatus?: "not_started" | "analyzing" | "analyzed" | "analysis_failed" | "skipped";
  readonly parseError?: string | null;
  readonly uploadedAt?: string;
  readonly analyzedAt?: string | null;
}

export interface UploadFailure {
  readonly documentId: string | null;
  readonly fileName: string;
  readonly reason: string;
}

export interface UploadSummary {
  readonly attemptedDocuments: number;
  readonly parsedDocuments: number;
  readonly failedDocuments: number;
  readonly failures: readonly UploadFailure[];
}

export interface AnalysisSummary {
  readonly runId: string;
  readonly startedAt: string;
  readonly completedAt: string;
  readonly status: "success" | "failed";
  readonly analyzedDocuments: number;
  readonly skippedDocuments: number;
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
  readonly citations: readonly SourceCitation[];
  readonly architectResponseMessageId?: string;
  readonly createdAt: string;
  readonly relatedArtifactIds: readonly string[];
}

export interface SourceCitation {
  readonly kind?: string;
  readonly url?: string;
  readonly fileName?: string;
  readonly documentId?: string;
  readonly excerpt?: string;
  readonly note?: string;
}

export interface CandidateArchitecture {
  readonly id?: string;
  readonly title?: string;
  readonly summary?: string;
  readonly sourceCitations?: readonly SourceCitation[];
}

export interface MindMapCoverage {
  readonly version?: string;
  readonly computedAt?: string;
  readonly topics: Record<string, { readonly status: string }>;
}
