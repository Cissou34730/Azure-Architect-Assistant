import { Project, ProjectState } from "../types/agent";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";
import { projectApi } from "./projectService";

export interface AgentHealth {
  readonly status: string;
  readonly mcpClientConnected: boolean;
  readonly openaiConfigured: boolean;
}

export interface AgentStep {
  readonly action: string;
  readonly actionInput: string;
  readonly observation: string;
}

export interface AgentChatResponse {
  readonly answer: string;
  readonly success: boolean;
  readonly reasoningSteps: readonly AgentStep[];
  readonly projectState?: ProjectState;
  readonly error?: string;
}

export const agentApi = {
  async getHealth(): Promise<AgentHealth> {
    return fetchWithErrorHandling<AgentHealth>(
      `${API_BASE}/agent/health`,
      {},
      "get health"
    );
  },

  async getProjects(): Promise<readonly Project[]> {
    return projectApi.fetchAll();
  },

  async chat(message: string): Promise<AgentChatResponse> {
    return fetchWithErrorHandling<AgentChatResponse>(
      `${API_BASE}/agent/chat`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      },
      "agent chat"
    );
  },

  async projectChat(
    projectId: string,
    message: string
  ): Promise<AgentChatResponse> {
    return fetchWithErrorHandling<AgentChatResponse>(
      `${API_BASE}/agent/projects/${projectId}/chat`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      },
      "project chat"
    );
  },

  async getProjectState(projectId: string): Promise<ProjectState> {
    const data = await fetchWithErrorHandling<{
      readonly projectState: ProjectState;
    }>(`${API_BASE}/projects/${projectId}/state`, {}, "get project state");
    return data.projectState;
  },

   
  async getHistory(
    projectId: string
    // eslint-disable-next-line @typescript-eslint/no-restricted-types
  ): Promise<readonly Record<string, unknown>[]> {
    const data = await fetchWithErrorHandling<{
      // eslint-disable-next-line @typescript-eslint/no-restricted-types
      readonly messages: readonly Record<string, unknown>[];
    }>(`${API_BASE}/projects/${projectId}/messages`, {}, "get history");
    return data.messages;
  },
};
