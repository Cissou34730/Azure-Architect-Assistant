import { Message, SendMessageResponse } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

export const chatApi = {
  async sendMessage(
    projectId: string,
    message: string,
  ): Promise<SendMessageResponse> {
    return fetchWithErrorHandling<SendMessageResponse>(
      `${API_BASE}/projects/${projectId}/chat`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      },
      "send message",
    );
  },

  async fetchMessages(projectId: string): Promise<readonly Message[]> {
    const data = await fetchWithErrorHandling<{
      readonly messages: readonly Message[];
    }>(`${API_BASE}/projects/${projectId}/messages`, {}, "fetch messages");
    return data.messages;
  },
};
