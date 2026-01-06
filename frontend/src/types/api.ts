export interface Project {
  id: string;
  name: string;
  textRequirements?: string;
  createdAt: string;
}

export interface ProjectState {
  projectId: string;
  context: {
    summary: string;
    objectives: string[];
    targetUsers: string;
    scenarioType: string;
  };
  summary: string;
  objectives: string[];
  targetUsers: string;
  scenarioType: string;
  functionalRequirements: string[];
  nonFunctionalRequirements: string[];
  complianceRequirements: string[];
  dataResidency: string;
  technicalConstraints: {
    constraints: string[];
    assumptions: string[];
  };
  constraints: string[];
  assumptions: string[];
  openQuestions: string[];
  lastUpdated: string;
}

export interface KBSource {
  url: string;
  title: string;
  section: string;
  score: number;
  kb_id?: string;
  kb_name?: string;
}

export interface Message {
  id: string;
  projectId: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  kbSources?: KBSource[];
}

export interface KBQueryResponse {
  answer: string;
  sources: KBSource[];
  hasResults: boolean;
  suggestedFollowUps?: string[];
}

export interface KBHealthInfo {
  kb_id: string;
  kb_name: string;
  status: string;
  index_ready: boolean;
  error?: string;
}

export interface KBHealthResponse {
  overall_status: string;
  knowledge_bases: KBHealthInfo[];
}
