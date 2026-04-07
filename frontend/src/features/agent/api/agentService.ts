import type { Project, ProjectState } from "../types/agent";
import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";
import { projectApi } from "../../projects/api/projectService";

interface AgentHealth {
  readonly status: string;
  readonly mcpClientConnected: boolean;
  readonly openaiConfigured: boolean;
}

interface AgentStep {
  readonly action: string;
  readonly actionInput: string;
  readonly observation: string;
}

interface AgentChatResponse {
  readonly answer: string;
  readonly success: boolean;
  readonly reasoningSteps: readonly AgentStep[];
  readonly projectState?: ProjectState;
  readonly error?: string;
}

interface ChatMessage {
  readonly role: string;
  readonly content: string;
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
    }>(`${API_BASE}/projects/${projectId}/workspace`, {}, "get project workspace state");
    return data.projectState;
  },

  async getHistory(projectId: string): Promise<readonly ChatMessage[]> {
    const data = await fetchWithErrorHandling<{
      readonly messages: readonly ChatMessage[];
    }>(`${API_BASE}/projects/${projectId}/messages`, {}, "get history");
    return data.messages;
  },
};
