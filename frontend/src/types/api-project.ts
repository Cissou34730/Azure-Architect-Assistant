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
  readonly requirements: readonly Requirement[];
  readonly assumptions: readonly Assumption[];
  readonly clarificationQuestions: readonly ClarificationQuestion[];
  readonly candidateArchitectures: readonly CandidateArchitecture[];
  readonly adrs: readonly AdrArtifact[];
  readonly wafChecklist: WafChecklist;
  readonly findings: readonly FindingArtifact[];
  readonly diagrams: readonly DiagramData[];
  readonly iacArtifacts: readonly IacArtifact[];
  readonly costEstimates: readonly CostEstimate[];
  readonly traceabilityLinks: readonly TraceabilityLink[];
  readonly mindMapCoverage: MindMapCoverage;
  readonly traceabilityIssues: readonly TraceabilityIssue[];
  // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Dynamic backend JSON structure
  readonly mindMap: Record<string, unknown>;
  readonly referenceDocuments: readonly ReferenceDocument[];
  readonly mcpQueries: readonly MCPQuery[];
  readonly projectDocumentStats?: UploadSummary;
  readonly analysisSummary?: AnalysisSummary;
  readonly iterationEvents: readonly IterationEvent[];

  // Flat properties for compatibility
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

export interface Requirement {
  readonly id?: string;
  readonly category?: string;
  readonly text?: string;
  readonly ambiguity?: {
    readonly isAmbiguous?: boolean;
    readonly notes?: string;
  };
  readonly sources?: readonly SourceCitation[];
}

export interface ClarificationQuestion {
  readonly id?: string;
  readonly question?: string;
  readonly priority?: number;
  readonly status?: string;
}

export interface Assumption {
  readonly id?: string;
  readonly text?: string;
}

// Imports for ProjectState cross-references (will be re-exported from api.ts)
import type {
  AdrArtifact,
  WafChecklist,
  FindingArtifact,
  IacArtifact,
  CostEstimate,
  TraceabilityLink,
  MindMapCoverage,
  TraceabilityIssue,
  ReferenceDocument,
  MCPQuery,
  IterationEvent,
  SourceCitation,
  CandidateArchitecture,
  UploadSummary,
  AnalysisSummary,
} from "./api-artifacts";
import type { DiagramData } from "./api-diagrams";
