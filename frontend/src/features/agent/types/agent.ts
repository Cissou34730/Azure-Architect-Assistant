export interface Message {
  readonly id?: string;
  readonly role: "user" | "assistant";
  readonly content: string;
  readonly reasoningSteps?: readonly ReasoningStep[];
}

export interface ReasoningStep {
  readonly action: string;
  readonly actionInput: string;
  readonly observation: string;
}

export interface Project {
  readonly id: string;
  readonly name: string;
  readonly textRequirements?: string;
  readonly createdAt: string;
}

export interface ProjectState {
  readonly projectId?: string;
  readonly lastUpdated?: string;
  readonly context?: {
    readonly summary?: string;
    readonly objectives?: readonly string[];
    readonly targetUsers?: string;
    readonly scenarioType?: string;
  };
  readonly nfrs?: {
    readonly availability?: string;
    readonly security?: string;
    readonly performance?: string;
    readonly costConstraints?: string;
  };
  readonly applicationStructure?: {
    readonly components?: readonly {
      readonly name: string;
      readonly description: string;
    }[];
    readonly integrations?: readonly string[];
  };
  readonly dataCompliance?: {
    readonly dataTypes?: readonly string[];
    readonly complianceRequirements?: readonly string[];
    readonly dataResidency?: string;
  };
  readonly technicalConstraints?: {
    readonly constraints?: readonly string[];
    readonly assumptions?: readonly string[];
  };
  readonly openQuestions?: readonly string[];
}

export type AgentStatus = "unknown" | "healthy" | "not_initialized";
