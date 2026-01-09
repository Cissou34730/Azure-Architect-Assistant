/**
 * API Service - Centralized API calls
 * Points directly to the Python backend (configured via repo .env)
 */

// Point to Python backend directly (no TypeScript proxy layer)
const API_BASE = `${
  import.meta.env.BACKEND_URL
}/api`;

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

export interface Message {
  id: string;
  projectId: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  kbSources?: KBSource[];
}

export interface KBSource {
  url: string;
  title: string;
  section: string;
  score: number;
  kb_id?: string;
  kb_name?: string;
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

/**
 * Knowledge Base API
 */
export const kbApi = {
  async checkHealth(): Promise<KBHealthResponse> {
    const response = await fetch(`${API_BASE}/kb/health`);
    if (!response.ok) {
      throw new Error(`KB health check failed: ${response.status}`);
    }
    return response.json();
  },

  async query(
    question: string,
    topKPerKB: number = 3,
  ): Promise<KBQueryResponse> {
    const response = await fetch(`${API_BASE}/query/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        topKPerKB,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to query knowledge bases");
    }

    return response.json();
  },

  async queryKBs(
    question: string,
    kbIds: string[],
    topKPerKB: number = 5,
  ): Promise<KBQueryResponse> {
    const response = await fetch(`${API_BASE}/query/kb-query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        kb_ids: kbIds,
        topKPerKB,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to query selected knowledge bases");
    }

    return response.json();
  },
};

/**
 * Project API
 */
export const projectApi = {
  async get(id: string): Promise<Project> {
    const response = await fetch(`${API_BASE}/projects/${id}`);
    if (!response.ok) throw new Error("Failed to fetch project");
    const data = (await response.json()) as { project: Project };
    return data.project;
  },

  async fetchAll(): Promise<Project[]> {
    const response = await fetch(`${API_BASE}/projects`);
    const data = await response.json();
    return data.projects;
  },

  async create(name: string): Promise<Project> {
    const response = await fetch(`${API_BASE}/projects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });

    if (!response.ok) {
      throw new Error("Failed to create project");
    }

    const data = await response.json();
    return data.project;
  },

  async uploadDocuments(projectId: string, files: FileList): Promise<void> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("documents", file);
    });

    const response = await fetch(
      `${API_BASE}/projects/${projectId}/documents`,
      {
        method: "POST",
        body: formData,
      },
    );

    if (!response.ok) {
      throw new Error("Failed to upload documents");
    }
  },

  async saveTextRequirements(
    projectId: string,
    text: string,
  ): Promise<Project> {
    const response = await fetch(
      `${API_BASE}/projects/${projectId}/requirements`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ textRequirements: text }),
      },
    );

    if (!response.ok) {
      throw new Error("Failed to save text requirements");
    }

    const data = await response.json();
    return data.project;
  },

  async analyzeDocuments(projectId: string): Promise<ProjectState> {
    const response = await fetch(
      `${API_BASE}/projects/${projectId}/analyze-docs`,
      {
        method: "POST",
      },
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to analyze documents");
    }

    const data = await response.json();
    return data.projectState;
  },
};

/**
 * Project State API
 */
export const stateApi = {
  async fetch(projectId: string): Promise<ProjectState | null> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/state`);

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    return data.projectState;
  },
};

/**
 * Chat API
 */
export const chatApi = {
  async sendMessage(
    projectId: string,
    message: string,
  ): Promise<{
    message: string;
    projectState: ProjectState;
    kbSources?: KBSource[];
  }> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to send message");
    }

    return response.json();
  },

  async fetchMessages(projectId: string): Promise<Message[]> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/messages`);
    const data = await response.json();
    return data.messages;
  },
};

/**
 * Proposal API
 */
export const proposalApi = {
  createProposalStream(
    projectId: string,
    onProgress: (stage: string, detail?: string) => void,
    onComplete: (proposal: string) => void,
    onError: (error: string) => void,
  ): EventSource {
    const url = `${API_BASE}/projects/${projectId}/architecture/proposal`;
    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.stage === "done") {
          onComplete(data.proposal);
          eventSource.close();
        } else if (data.stage === "error") {
          onError(data.error || "Unknown error");
          eventSource.close();
        } else {
          const stageMessages: Record<string, string> = {
            started: "Initializing...",
            querying_waf:
              data.detail || "Querying Azure Well-Architected Framework...",
            querying_knowledge_bases:
              data.detail || "Querying knowledge bases...",
            building_context: "Building context from guidance...",
            generating_proposal: "Generating comprehensive proposal with AI...",
            finalizing: "Finalizing proposal...",
            completed: "Completed successfully",
          };
          onProgress(
            stageMessages[data.stage] || data.detail || "Processing...",
            data.detail,
          );
        }
      } catch (error) {
        console.error("Error parsing SSE message:", error);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      onError("Connection error during proposal generation");
    };

    return eventSource;
  },
};

/**
 * Diagram Generation API
 */
export const diagramApi = {
  async getDiagramSet(diagramSetId: string) {
    const response = await fetch(`${API_BASE}/v1/diagram-sets/${diagramSetId}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch diagram set: ${response.status}`);
    }
    return response.json();
  },

  async createDiagramSet(inputDescription: string, adrId?: string) {
    const response = await fetch(`${API_BASE}/v1/diagram-sets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input_description: inputDescription,
        adr_id: adrId,
      }),
    });
    if (!response.ok) {
      throw new Error(`Failed to create diagram set: ${response.status}`);
    }
    return response.json();
  },
};
