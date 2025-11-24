/**
 * WAF Service
 * Communicates with Python FastAPI service for RAG operations
 */

import { logger } from "../logger.js";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export interface WAFQueryRequest {
  question: string;
  topK?: number;
  metadataFilters?: Record<string, JsonValue>;
}

export interface WAFQueryResponse {
  answer: string;
  sources: Array<{
    url: string;
    title: string;
    section: string;
    score: number;
  }>;
  hasResults: boolean;
  suggestedFollowUps?: string[];
}

export interface IngestionResponse {
  message: string;
  jobId: string;
}

export interface HealthStatus {
  status: string;
  index_ready: boolean;
  storage_dir: string;
}

export class WAFService {
  private pythonServiceUrl: string;

  constructor() {
    this.pythonServiceUrl =
      process.env.PYTHON_SERVICE_URL || "http://localhost:8000";

    logger.info("WAF Service initialized", {
      pythonServiceUrl: this.pythonServiceUrl,
    });

    // Verify connection on startup
    this.checkHealth().catch((error) => {
      logger.warn("Python service not available on startup", { error });
    });
  }

  /**
   * Check health of Python service
   */
  async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch(`${this.pythonServiceUrl}/health`);

      if (!response.ok) {
        throw new Error(`Health check failed: ${response.status}`);
      }

      const health = (await response.json()) as HealthStatus;
      logger.info("Python service health check", health);
      return health;
    } catch (error) {
      logger.error("Failed to check Python service health", { error });
      throw error;
    }
  }

  /**
   * Query WAF documentation
   */
  async query(request: WAFQueryRequest): Promise<WAFQueryResponse> {
    try {
      logger.info("Sending query to Python service", {
        question: request.question.substring(0, 100),
        topK: request.topK,
      });

      const response = await fetch(`${this.pythonServiceUrl}/query`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: request.question,
          topK: request.topK || 5,
          metadataFilters: request.metadataFilters,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        logger.error("Python service query failed", {
          status: response.status,
          error: errorText,
        });
        throw new Error(`Query failed: ${response.status} - ${errorText}`);
      }

      const result = (await response.json()) as WAFQueryResponse;

      logger.info("Query successful", {
        hasResults: result.hasResults,
        sourceCount: result.sources.length,
      });

      return result;
    } catch (error) {
      logger.error("WAF query failed", { error });
      throw error;
    }
  }

  /**
   * Start ingestion Phase 1 (crawl and clean)
   */
  async startIngestionPhase1(): Promise<IngestionResponse> {
    try {
      logger.info("Starting ingestion Phase 1 via Python service");

      const response = await fetch(`${this.pythonServiceUrl}/ingest/phase1`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Phase 1 ingestion failed: ${response.status} - ${errorText}`
        );
      }

      const result = (await response.json()) as IngestionResponse;
      logger.info("Phase 1 ingestion started", result);
      return result;
    } catch (error) {
      logger.error("Failed to start Phase 1 ingestion", { error });
      throw error;
    }
  }

  /**
   * Start ingestion Phase 2 (build index)
   */
  async startIngestionPhase2(): Promise<IngestionResponse> {
    try {
      logger.info("Starting ingestion Phase 2 via Python service");

      const response = await fetch(`${this.pythonServiceUrl}/ingest/phase2`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(
          `Phase 2 ingestion failed: ${response.status} - ${errorText}`
        );
      }

      const result = (await response.json()) as IngestionResponse;
      logger.info("Phase 2 ingestion started", result);
      return result;
    } catch (error) {
      logger.error("Failed to start Phase 2 ingestion", { error });
      throw error;
    }
  }

  /**
   * Start full ingestion pipeline (legacy compatibility)
   */
  async startIngestion(): Promise<IngestionResponse> {
    try {
      // Phase 1
      const phase1 = await this.startIngestionPhase1();
      logger.info("Full pipeline: Phase 1 started", phase1);

      // Note: Phase 2 should be triggered separately after validation
      // For backward compatibility, we just return Phase 1 response
      return {
        message:
          "Phase 1 started. Complete validation and trigger Phase 2 separately.",
        jobId: phase1.jobId,
      };
    } catch (error) {
      logger.error("Failed to start full ingestion", { error });
      throw error;
    }
  }

  /**
   * Check if index is ready
   */
  async isIndexReady(): Promise<boolean> {
    try {
      const health = await this.checkHealth();
      return health.index_ready;
    } catch (error) {
      logger.warn("Could not check index readiness", { error });
      return false;
    }
  }
}

// Export singleton instance
export const wafService = new WAFService();
