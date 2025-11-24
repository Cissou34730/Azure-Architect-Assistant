export interface Project {
  id: string;
  name: string;
  textRequirements?: string;
  createdAt: string;
}

export interface ProjectDocument {
  id: string;
  projectId: string;
  fileName: string;
  mimeType: string;
  rawText: string;
  uploadedAt: string;
}

export interface ProjectState {
  projectId: string;
  context: {
    summary: string;
    objectives: string[];
    targetUsers: string;
    scenarioType: string;
  };
  nfrs: {
    availability: string;
    security: string;
    performance: string;
    costConstraints: string;
  };
  applicationStructure: {
    components: string[];
    integrations: string[];
  };
  dataCompliance: {
    dataTypes: string[];
    complianceRequirements: string[];
    dataResidency: string;
  };
  technicalConstraints: {
    constraints: string[];
    assumptions: string[];
  };
  openQuestions: string[];
  lastUpdated: string;
}

export interface WAFSource {
  url: string;
  title: string;
  section: string;
  score: number;
}

export interface ConversationMessage {
  id: string;
  projectId: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  wafSources?: WAFSource[];
}
