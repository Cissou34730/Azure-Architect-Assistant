import type { AgentResponse, Message } from "../../types/agent";
import type { ProjectState } from "../../types/agent";
import { fetchWithErrorHandling } from "../serviceError";

const API_BASE = `${
  import.meta.env.BACKEND_URL
}/api`;

export interface AgentConversationHistoryResponse {
  messages: Array<
    Message & {
      id: string;
      projectId: string;
      timestamp: string;
      wafSources?: unknown[];
    }
  >;
  total: number;
}

export const agentApi = {
  async chat(message: string): Promise<AgentResponse> {
    return fetchWithErrorHandling<AgentResponse>(
      `${API_BASE}/agent/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      },
      "chat with agent"
    );
  },

  async chatWithProject(
    projectId: string,
    message: string
  ): Promise<AgentResponse & { project_state?: ProjectState }> {
    return fetchWithErrorHandling<
      AgentResponse & { project_state?: ProjectState }
    >(
      `${API_BASE}/agent/projects/${projectId}/chat`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      },
      "chat with agent (project context)"
    );
  },

  async getProjectHistory(
    projectId: string
  ): Promise<AgentConversationHistoryResponse> {
    return fetchWithErrorHandling<AgentConversationHistoryResponse>(
      `${API_BASE}/agent/projects/${projectId}/history`,
      { method: "GET" },
      "load agent conversation history"
    );
  },
};
