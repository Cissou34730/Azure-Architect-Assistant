import {
  KbHealthResponse,
  KbQueryResponse,
  KbListResponse,
} from "../types/api";
import { keysToSnake } from "../utils/apiMapping";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

export const kbApi = {
  async listKbs(): Promise<KbListResponse> {
    return fetchWithErrorHandling<KbListResponse>(
      `${API_BASE}/kb/list`,
      {},
      "list KBs"
    );
  },

  async checkHealth(): Promise<KbHealthResponse> {
    return fetchWithErrorHandling<KbHealthResponse>(
      `${API_BASE}/kb/health`,
      {},
      "check health"
    );
  },

  async query(question: string, topKPerKB = 3): Promise<KbQueryResponse> {
    return fetchWithErrorHandling<KbQueryResponse>(
      `${API_BASE}/query/chat`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify(
          keysToSnake({
            question,
            topKPerKB,
          })
        ),
      },
      "query KBs"
    );
  },

  async queryKBs(
    question: string,
    kbIds: readonly string[],
    topKPerKB = 5
  ): Promise<KbQueryResponse> {
    return fetchWithErrorHandling<KbQueryResponse>(
      `${API_BASE}/query/kb-query`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify(
          keysToSnake({
            question,
            kbIds,
            topKPerKB,
          })
        ),
      },
      "query selected KBs"
    );
  },
};
