import { Message, SendMessageResponse } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

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

    return fetchWithErrorHandling<SendMessageResponse>(
      `${API_BASE}/projects/${projectId}/chat`,
      {
        method: "POST",
        headers,
        body: JSON.stringify({ message }),
      },
      "send message",
    );
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
