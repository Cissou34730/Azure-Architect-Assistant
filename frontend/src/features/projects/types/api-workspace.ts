import type {
  AdrArtifact,
  AnalysisSummary,
  CandidateArchitecture,
  CostEstimate,
  FindingArtifact,
  IacArtifact,
  IterationEvent,
  MCPQuery,
  MindMapCoverage,
  ReferenceDocument,
  TraceabilityIssue,
  TraceabilityLink,
  UploadSummary,
  WafChecklist,
} from "./api-artifacts";
import type {
  Assumption,
  ClarificationQuestion,
  ProjectState,
  ProjectStateAppStructure,
  ProjectStateDataCompliance,
  ProjectStateNfrs,
  ProjectStateTechnicalConstraints,
  Requirement,
} from "./api-project";
import type { DiagramData } from "../../diagrams/types/api-diagrams";

export interface ProjectWorkspaceProjectSummary {
  readonly id: string;
  readonly name: string;
  readonly createdAt: string;
  readonly textRequirements: string;
  readonly documentCount: number;
}

export interface ProjectWorkspaceStateSummary {
  readonly lastUpdated: string | null;
  readonly artifactKeys: readonly string[];
}

export interface ProjectWorkspaceInputs {
  readonly context: ProjectState["context"];
  readonly nfrs?: ProjectStateNfrs | null;
  readonly applicationStructure?: ProjectStateAppStructure | null;
  readonly dataCompliance?: ProjectStateDataCompliance | null;
  readonly technicalConstraints?: ProjectStateTechnicalConstraints | null;
  readonly openQuestions: readonly string[];
}

export interface ProjectWorkspaceDocuments {
  readonly items: readonly ReferenceDocument[];
  readonly stats?: UploadSummary | null;
}

export interface ProjectWorkspaceArtifacts {
  readonly requirements: readonly Requirement[];
  readonly assumptions: readonly Assumption[];
  readonly clarificationQuestions: readonly ClarificationQuestion[];
  readonly candidateArchitectures: readonly CandidateArchitecture[];
  readonly adrs: readonly AdrArtifact[];
  readonly findings: readonly FindingArtifact[];
  readonly diagrams: readonly DiagramData[];
  readonly iacArtifacts: readonly IacArtifact[];
  readonly costEstimates: readonly CostEstimate[];
  readonly traceabilityLinks: readonly TraceabilityLink[];
  readonly traceabilityIssues: readonly TraceabilityIssue[];
  readonly mindMapCoverage?: MindMapCoverage | null;
  readonly mindMap?: ProjectState["mindMap"] | null;
  readonly mcpQueries: readonly MCPQuery[];
  readonly iterationEvents: readonly IterationEvent[];
  readonly analysisSummary?: AnalysisSummary | null;
  readonly wafChecklist?: WafChecklist | null;
}

export interface ProjectWorkspaceView {
  readonly project: ProjectWorkspaceProjectSummary;
  readonly state: ProjectWorkspaceStateSummary;
  readonly inputs: ProjectWorkspaceInputs;
  readonly documents: ProjectWorkspaceDocuments;
  readonly artifacts: ProjectWorkspaceArtifacts;
  readonly agent: {
    readonly messageCount: number;
    readonly threadCount: number;
    readonly lastMessageAt: string | null;
  };
  readonly checklists: readonly Record<string, never>[];
  readonly knowledgeBases: readonly Record<string, never>[];
  readonly diagrams: readonly Record<string, never>[];
  readonly settings: {
    readonly provider: string;
    readonly model: string;
  };
}