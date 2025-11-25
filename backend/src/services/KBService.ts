/**
 * Knowledge Base Service
 * Generic service for interacting with Python KB/RAG service
 * Supports multiple knowledge bases and query profiles
 */

import { logger } from "../logger.js";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type QueryProfile = "chat" | "proposal";

export interface KBQueryRequest {
  question: string;
  profile: QueryProfile;
  topKPerKB?: number;
}

export interface KBSource {
  url: string;
  title: string;
  section: string;
  score: number;
  kb_id?: string;
  kb_name?: string;
}

export interface KBQueryResponse {
  answer: string;
  sources: KBSource[];
  hasResults: boolean;
  suggestedFollowUps?: string[];
}

export interface KBInfo {
  id: string;
  name: string;
  profiles: string[];
  priority: number;
  status: string;
}

export interface KBListResponse {
  knowledge_bases: KBInfo[];
}

export interface KBHealthResponse {
  kb_id: string;
  kb_name: string;
  status: string;
  index_ready: boolean;
  error?: string;
}

export interface HealthStatus {
  status: string;
  index_ready: boolean;
  storage_dir: string;
}

/**
 * Generic Knowledge Base Service
 * Communicates with Python FastAPI service for multi-source RAG operations
 */
export class KBService {
  private pythonServiceUrl: string;
  private log = logger.child("KBService");

  constructor() {
    this.pythonServiceUrl =
      process.env.PYTHON_SERVICE_URL || "http://localhost:8000";

    this.log.info("KB Service initialized", {
      pythonServiceUrl: this.pythonServiceUrl,
    });

    // Verify connection on startup
    this.checkHealth().catch((error) => {
      this.log.warn("Python service not available on startup", { error });
    });
  }

  /**
   * Check overall health of Python service
   */
  async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch(`${this.pythonServiceUrl}/health`);

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      const health = (await response.json()) as HealthStatus;
      this.log.info("Python service health check", health);
      return health;
    } catch (error) {
      this.log.error("Failed to check Python service health", { error });
      throw error;
    }
  }

  /**
   * Check health of all knowledge bases
   */
  async checkKBHealth(): Promise<{ knowledge_bases: KBHealthResponse[] }> {
    try {
      const response = await fetch(`${this.pythonServiceUrl}/kb/health`);

      if (!response.ok) {
        throw new Error(`KB health check failed: ${response.status}`);
      }

      const result = (await response.json()) as {
        knowledge_bases: KBHealthResponse[];
      };
      this.log.info("KB health check successful", {
        kbCount: result.knowledge_bases.length,
      });
      return result;
    } catch (error) {
      this.log.error("Failed to check KB health", { error });
      throw error;
    }
  }

  /**
   * List all available knowledge bases
   */
  async listKnowledgeBases(): Promise<KBListResponse> {
    try {
      const response = await fetch(`${this.pythonServiceUrl}/kb/list`);

      if (!response.ok) {
        throw new Error(`Failed to list KBs: ${response.status}`);
      }

      const result = (await response.json()) as KBListResponse;
      this.log.info("Knowledge bases listed", {
        count: result.knowledge_bases.length,
      });
      return result;
    } catch (error) {
      this.log.error("Failed to list knowledge bases", { error });
      throw error;
    }
  }

  /**
   * Query knowledge bases using CHAT profile (fast, targeted)
   */
  async queryChat(
    question: string,
    topKPerKB?: number
  ): Promise<KBQueryResponse> {
    return this.queryProfile({ question, profile: "chat", topKPerKB });
  }

  /**
   * Query knowledge bases using PROPOSAL profile (comprehensive)
   */
  async queryProposal(
    question: string,
    topKPerKB?: number
  ): Promise<KBQueryResponse> {
    return this.queryProfile({ question, profile: "proposal", topKPerKB });
  }

  /**
   * Query knowledge bases with specified profile
   */
  async queryProfile(request: KBQueryRequest): Promise<KBQueryResponse> {
    try {
      this.log.info("Querying KBs with profile", {
        profile: request.profile,
        question: request.question.substring(0, 100),
        topKPerKB: request.topKPerKB,
      });

      const endpoint =
        request.profile === "chat" ? "/query/chat" : "/query/proposal";

      const response = await fetch(`${this.pythonServiceUrl}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: request.question,
          profile: request.profile,
          topKPerKB: request.topKPerKB,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        this.log.error("KB query failed", {
          status: response.status,
          error: errorText,
        });
        throw new Error(`KB query failed: ${response.status} - ${errorText}`);
      }

      const result = (await response.json()) as KBQueryResponse;

      this.log.info("KB query successful", {
        profile: request.profile,
        hasResults: result.hasResults,
        sourceCount: result.sources.length,
        kbs: [
          ...new Set(result.sources.map((s) => s.kb_id).filter(Boolean)),
        ].join(", "),
      });

      return result;
    } catch (error) {
      this.log.error("KB query failed", { error });
      throw error;
    }
  }

  /**
   * Legacy method for backward compatibility
   * Queries using chat profile with default settings
   */
  async query(request: {
    question: string;
    topK?: number;
    metadataFilters?: Record<string, JsonValue>;
  }): Promise<KBQueryResponse> {
    this.log.info(
      "Legacy query method called, redirecting to chat profile query"
    );
    return this.queryChat(request.question, request.topK);
  }
}

// Singleton instance
let _kbService: KBService | null = null;

export const kbService = {
  checkHealth: (): ReturnType<KBService["checkHealth"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.checkHealth();
  },
  checkKBHealth: (): ReturnType<KBService["checkKBHealth"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.checkKBHealth();
  },
  listKnowledgeBases: (): ReturnType<KBService["listKnowledgeBases"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.listKnowledgeBases();
  },
  queryChat: (
    ...args: Parameters<KBService["queryChat"]>
  ): ReturnType<KBService["queryChat"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.queryChat(...args);
  },
  queryProposal: (
    ...args: Parameters<KBService["queryProposal"]>
  ): ReturnType<KBService["queryProposal"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.queryProposal(...args);
  },
  queryProfile: (
    ...args: Parameters<KBService["queryProfile"]>
  ): ReturnType<KBService["queryProfile"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.queryProfile(...args);
  },
  query: (
    ...args: Parameters<KBService["query"]>
  ): ReturnType<KBService["query"]> => {
    if (!_kbService) _kbService = new KBService();
    return _kbService.query(...args);
  },
};
