export interface Message {
  role: "user" | "assistant";
  content: string;
  reasoningSteps?: ReasoningStep[];
}

export interface ReasoningStep {
  action: string;
  action_input: string;
  observation: string;
}

export interface AgentResponse {
  answer: string;
  success: boolean;
  reasoning_steps: ReasoningStep[];
  project_state?: ProjectState;
  error?: string;
}

export interface Project {
  id: string;
  name: string;
  textRequirements: string;
  createdAt: string;
}

export interface ProjectState {
  projectId?: string;
  lastUpdated?: string;
  context?: {
    summary?: string;
    objectives?: string[];
    targetUsers?: string;
    scenarioType?: string;
  };
  nfrs?: {
    availability?: string;
    security?: string;
    performance?: string;
    costConstraints?: string;
  };
  applicationStructure?: {
    components?: Array<{ name: string; description: string }>;
    integrations?: string[];
  };
  dataCompliance?: {
    dataTypes?: string[];
    complianceRequirements?: string[];
    dataResidency?: string;
  };
  technicalConstraints?: {
    constraints?: string[];
    assumptions?: string[];
  };
  openQuestions?: string[];
}

export type AgentStatus = "unknown" | "healthy" | "not_initialized";
