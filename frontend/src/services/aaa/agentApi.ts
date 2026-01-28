import type { AgentResponse, Message } from "../../types/agent";
import type { ProjectState } from "../../types/agent";
import { fetchWithErrorHandling } from "../serviceError";

import { API_BASE } from "../config";

export interface AgentConversationHistoryResponse {
  messages: (Message & {
    id: string;
    projectId: string;
    timestamp: string;
    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Backend returns untyped WAF sources
    wafSources?: unknown[];
  })[];
  total: number;
}

export const agentApi = {
  async chat(message: string): Promise<AgentResponse> {
    return fetchWithErrorHandling<AgentResponse>(
      `${API_BASE}/agent/chat`,
      {
        method: "POST",
        // eslint-disable-next-line @typescript-eslint/naming-convention
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      },
      "chat with agent",
    );
  },

  async chatWithProject(
    projectId: string,
    message: string,
  ): Promise<AgentResponse & { projectState?: ProjectState }> {
    const res = await fetchWithErrorHandling<
      // eslint-disable-next-line @typescript-eslint/naming-convention
      AgentResponse & { project_state?: ProjectState }
    >(
      `${API_BASE}/agent/projects/${projectId}/chat`,
      {
        method: "POST",
        // eslint-disable-next-line @typescript-eslint/naming-convention
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      },
      "chat with agent (project context)",
    );

    return {
      ...res,
      projectState: res.project_state,
    };
  },

  async getProjectHistory(
    projectId: string,
  ): Promise<AgentConversationHistoryResponse> {
    return fetchWithErrorHandling<AgentConversationHistoryResponse>(
      `${API_BASE}/agent/projects/${projectId}/history`,
      { method: "GET" },
      "load agent conversation history",
    );
  },
};
