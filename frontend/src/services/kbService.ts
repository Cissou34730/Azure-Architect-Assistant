import { KBHealthResponse, KBQueryResponse } from "../types/api";

const API_BASE = `${
  import.meta.env.BACKEND_URL
}/api`;

export const kbApi = {
  async checkHealth(): Promise<KBHealthResponse> {
    const res = await fetch(`${API_BASE}/kb/health`);
    if (!res.ok) throw new Error("Health check failed");
    return res.json();
  },

  async query(
    question: string,
    topKPerKB: number = 3,
  ): Promise<KBQueryResponse> {
    const res = await fetch(`${API_BASE}/kb/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        top_k_per_kb: topKPerKB,
      }),
    });
    if (!res.ok) throw new Error("Query failed");
    return res.json();
  },

  async queryKBs(
    question: string,
    kbIds: string[],
    topKPerKB: number = 5,
  ): Promise<KBQueryResponse> {
    const res = await fetch(`${API_BASE}/kb/query/multi`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        kb_ids: kbIds,
        top_k_per_kb: topKPerKB,
      }),
    });
    if (!res.ok) throw new Error("Multi-KB query failed");
    return res.json();
  },
};
