import { Message, ProjectState, KBSource } from "../types/api";

const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

export const chatApi = {
  async sendMessage(
    projectId: string,
    message: string
  ): Promise<{
    message: string;
    projectState: ProjectState;
    kbSources?: KBSource[];
  }> {
    const res = await fetch(`${API_BASE}/chat/${projectId}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
  },

  async fetchMessages(projectId: string): Promise<Message[]> {
    const res = await fetch(`${API_BASE}/chat/${projectId}/history`);
    if (!res.ok) throw new Error("Failed to fetch messages");
    return res.json();
  },
};
