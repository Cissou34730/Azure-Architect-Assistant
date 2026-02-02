import { Message, SendMessageResponse } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

interface ReasoningStep {
  readonly step: string;
  readonly reasoning?: string;
}

interface AgentProjectChatResponse {
  readonly answer: string;
  readonly success: boolean;
  readonly reasoningSteps: readonly ReasoningStep[];
  readonly projectState?: SendMessageResponse["projectState"];
  readonly error?: string;
}

export const chatApi = {
  async sendMessage(
    projectId: string,
    message: string,
    options?: { idempotencyKey?: string },
  ): Promise<SendMessageResponse> {
    const headers: Record<string, string> = {
      // eslint-disable-next-line @typescript-eslint/naming-convention
      "Content-Type": "application/json",
    };

    if (
      options?.idempotencyKey !== undefined &&
      options.idempotencyKey !== ""
    ) {
      headers["X-Idempotency-Key"] = options.idempotencyKey;
    }

    const agentResponse = await fetchWithErrorHandling<AgentProjectChatResponse>(
      `${API_BASE}/agent/projects/${projectId}/chat`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({ message }),
      },
      "send message",
    );

    if (!agentResponse.success) {
      throw new Error(agentResponse.error ?? "Agent chat failed");
    }
    if (agentResponse.projectState === undefined) {
      throw new Error("Agent chat succeeded but returned no project state");
    }

    return {
      message: agentResponse.answer,
      projectState: agentResponse.projectState,
    };
  },

  async fetchMessages(
    projectId: string,
    sinceId?: string,
  ): Promise<readonly Message[]> {
    const url =
      sinceId !== undefined && sinceId !== ""
        ? `${API_BASE}/projects/${projectId}/messages?since_id=${sinceId}`
        : `${API_BASE}/projects/${projectId}/messages`;
    const data = await fetchWithErrorHandling<{
      readonly messages: readonly Message[];
    }>(url, {}, "fetch messages");
    return data.messages;
  },

  async fetchMessagesBefore(
    projectId: string,
    beforeMessageId: string,
    limit = 50,
  ): Promise<readonly Message[]> {
    const data = await fetchWithErrorHandling<{
      readonly messages: readonly Message[];
    }>(
      `${API_BASE}/projects/${projectId}/messages?before_id=${beforeMessageId}&limit=${limit}`,
      {},
      "fetch older messages",
    );
    return data.messages;
  },
};
