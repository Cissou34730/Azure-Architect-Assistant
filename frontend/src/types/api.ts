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
  readonly assumptions?: readonly string[];
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
