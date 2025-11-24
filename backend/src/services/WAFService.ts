/**
 * WAF Service
 * Handles Python process integration for WAF ingestion and queries
 */

import { spawn } from "child_process";
import { join } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";
import { logger } from "../logger.js";

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

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
  scores: number[];
  hasResults: boolean;
  discussionEnabled?: boolean;
  suggestedFollowUps?: string[];
}

export interface IngestionStatus {
  stage: string;
  progress: number;
  message: string;
  isComplete: boolean;
  error?: string;
}

export class WAFService {
  private pythonPath: string;
  private ragPath: string;
  private queryProcess: any = null;
  private queryProcessReady: boolean = false;
  private pendingQueries: Map<string, { resolve: any; reject: any }> =
    new Map();

  constructor() {
    // Determine Python path (consider virtual environment)
    this.pythonPath = process.env.PYTHON_PATH || "python";
    this.ragPath = join(__dirname, "..", "rag");

    logger.info("WAF Service initialized", {
      pythonPath: this.pythonPath,
      ragPath: this.ragPath,
    });

    // Start the long-running query service
    this.startQueryService();
  }

  /**
   * Execute a Python script and return the result
   */
  private async executePythonScript(
    scriptName: string,
    args: string[] = [],
    timeout: number = 300000 // 5 minutes default
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const scriptPath = join(this.ragPath, scriptName);

      logger.info(`Executing Python script: ${scriptName}`, { args });

      // Calculate absolute path to storage directory
      const rootPath = join(this.ragPath, "..", "..", "..");
      const storageDir = join(
        rootPath,
        "data",
        "knowledge_bases",
        "waf",
        "index"
      );

      logger.info("[WAFService] Path calculation:", {
        ragPath: this.ragPath,
        rootPath,
        storageDir,
        envVar: "WAF_STORAGE_DIR will be set to: " + storageDir,
      });

      const pythonProcess = spawn(this.pythonPath, [scriptPath, ...args], {
        cwd: this.ragPath,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
          WAF_STORAGE_DIR: storageDir,
        },
      });

      let stdout = "";
      let stderr = "";

      pythonProcess.stdout.on("data", (data: Buffer) => {
        const output = data.toString();
        stdout += output;
        logger.info("Python stdout:", { output });
      });

      pythonProcess.stderr.on("data", (data: Buffer) => {
        const output = data.toString();
        stderr += output;
        logger.info("Python stderr:", { output });
      });

      const timeoutHandle = setTimeout(() => {
        pythonProcess.kill();
        reject(new Error(`Python script timeout after ${timeout}ms`));
      }, timeout);

      pythonProcess.on("close", (code) => {
        clearTimeout(timeoutHandle);

        if (code === 0) {
          resolve(stdout);
        } else {
          logger.error("Python script failed", { code, stderr });
          reject(
            new Error(`Python script failed with code ${code}: ${stderr}`)
          );
        }
      });

      pythonProcess.on("error", (error) => {
        clearTimeout(timeoutHandle);
        logger.error("Failed to start Python script", { error });
        reject(error);
      });
    });
  }

  /**
   * Trigger WAF ingestion Phase 1 (crawl + clean + export)
   */
  startIngestionPhase1(): { jobId: string; message: string } {
    logger.info("Starting WAF ingestion Phase 1");

    const jobId = `waf-phase1-${Date.now()}`;

    // Run Phase 1 in background
    void this.runIngestionPhase1(jobId).catch((error: unknown) => {
      logger.error("Phase 1 failed", { jobId, error });
    });

    return {
      jobId,
      message: "Phase 1 started: Crawling and cleaning documents.",
    };
  }

  /**
   * Trigger WAF ingestion Phase 2 (chunk + embed + index)
   */
  startIngestionPhase2(): { jobId: string; message: string } {
    logger.info("Starting WAF ingestion Phase 2");

    const jobId = `waf-phase2-${Date.now()}`;

    // Run Phase 2 in background
    void this.runIngestionPhase2(jobId).catch((error: unknown) => {
      logger.error("Phase 2 failed", { jobId, error });
    });

    return {
      jobId,
      message: "Phase 2 started: Building index from approved documents.",
    };
  }

  /**
   * Trigger full WAF ingestion pipeline (legacy - backward compatible)
   * Now runs Phase 1 + auto-approve + Phase 2
   */
  startIngestion(): { jobId: string; message: string } {
    logger.info("Starting full WAF ingestion pipeline");

    const jobId = `waf-ingestion-${Date.now()}`;

    // Run full pipeline in background
    void this.runFullIngestionPipeline(jobId).catch((error: unknown) => {
      logger.error("Ingestion pipeline failed", { jobId, error });
    });

    return {
      jobId,
      message:
        "WAF ingestion started. Documents will be auto-approved. This will take several minutes.",
    };
  }

  /**
   * Run Phase 1: Crawl and clean documents
   */
  private async runIngestionPhase1(jobId: string): Promise<void> {
    try {
      logger.info("Phase 1 - Step 1: Crawling WAF documentation", { jobId });
      await this.executePythonScript("crawler.py", [], 600000); // 10 min timeout

      logger.info("Phase 1 - Step 2: Cleaning and exporting documents", {
        jobId,
      });
      await this.executePythonScript("cleaner.py", [], 600000);

      logger.info("Phase 1 completed - Ready for validation", { jobId });
    } catch (error) {
      logger.error("Phase 1 error", { jobId, error });
      throw error;
    }
  }

  /**
   * Run Phase 2: Build index from approved documents
   */
  private async runIngestionPhase2(jobId: string): Promise<void> {
    try {
      logger.info("Phase 2: Building index from approved documents", { jobId });
      await this.executePythonScript("indexer.py", [], 900000); // 15 min for embeddings

      logger.info("Phase 2 completed - Index ready", { jobId });
    } catch (error) {
      logger.error("Phase 2 error", { jobId, error });
      throw error;
    }
  }

  /**
   * Run the complete ingestion pipeline (auto-approve)
   */
  private async runFullIngestionPipeline(jobId: string): Promise<void> {
    try {
      // Phase 1
      await this.runIngestionPhase1(jobId);

      // Auto-approve all documents
      logger.info("Auto-approving all documents", { jobId });
      const rootPath = join(this.ragPath, "..", "..", "..");
      await this.executePythonScript(
        join(rootPath, "scripts", "utils", "approve_documents.py"),
        [],
        60000
      );

      // Phase 2
      await this.runIngestionPhase2(jobId);

      logger.info("Full ingestion pipeline completed", { jobId });
    } catch (error) {
      logger.error("Full ingestion pipeline error", { jobId, error });
      throw error;
    }
  }

  /**
   * Start the long-running query service process
   */
  private startQueryService(): void {
    const scriptPath = join(this.ragPath, "query_service.py");
    const rootPath = join(this.ragPath, "..", "..", "..");
    const storageDir = join(
      rootPath,
      "data",
      "knowledge_bases",
      "waf",
      "index"
    );

    logger.info("[WAFService] Starting long-running query service", {
      scriptPath,
      storageDir,
    });

    this.queryProcess = spawn(this.pythonPath, [scriptPath], {
      cwd: this.ragPath,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
        WAF_STORAGE_DIR: storageDir,
      },
    });

    let stdoutBuffer = "";

    this.queryProcess.stdout.on("data", (data: Buffer) => {
      const text = data.toString();
      stdoutBuffer += text;

      // Process line by line
      const lines = stdoutBuffer.split("\n");
      stdoutBuffer = lines.pop() || ""; // Keep incomplete line in buffer

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const response = JSON.parse(line);

          // Check for ready signal
          if (response.status === "ready") {
            this.queryProcessReady = true;
            logger.info("[WAFService] Query service ready");
            return;
          }

          // Handle query response (match by content for now - could use query IDs)
          const pendingQuery = Array.from(this.pendingQueries.values())[0];
          if (pendingQuery) {
            const queryId = Array.from(this.pendingQueries.keys())[0];
            this.pendingQueries.delete(queryId);
            pendingQuery.resolve(response);
          }
        } catch (e) {
          logger.warn("[WAFService] Failed to parse response line", { line });
        }
      }
    });

    this.queryProcess.stderr.on("data", (data: Buffer) => {
      const text = data.toString();
      logger.info("[WAFService] Query service stderr:", { text });
    });

    this.queryProcess.on("error", (error: Error) => {
      logger.error("[WAFService] Query service error", { error });
      this.queryProcessReady = false;
    });

    this.queryProcess.on("close", (code: number) => {
      logger.warn("[WAFService] Query service closed", { code });
      this.queryProcessReady = false;
      this.queryProcess = null;

      // Reject all pending queries
      for (const [queryId, pending] of this.pendingQueries.entries()) {
        pending.reject(new Error("Query service closed unexpectedly"));
        this.pendingQueries.delete(queryId);
      }
    });
  }

  /**
   * Send a query to the long-running service
   */
  private async queryLongRunningService(
    question: string,
    topK: number = 3
  ): Promise<any> {
    // Wait for service to be ready (with timeout)
    const maxWait = 60000; // 60 seconds for initial index load
    const startWait = Date.now();

    while (!this.queryProcessReady && Date.now() - startWait < maxWait) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    if (!this.queryProcessReady) {
      throw new Error("Query service not ready after 60 seconds");
    }

    return new Promise((resolve, reject) => {
      const queryId = `query-${Date.now()}`;
      this.pendingQueries.set(queryId, { resolve, reject });

      const queryData = {
        question,
        top_k: topK,
      };

      // Send query to service
      this.queryProcess.stdin.write(JSON.stringify(queryData) + "\n");

      // Timeout after 30 seconds
      setTimeout(() => {
        if (this.pendingQueries.has(queryId)) {
          this.pendingQueries.delete(queryId);
          reject(new Error("Query timeout after 30 seconds"));
        }
      }, 30000);
    });
  }

  /**
   * Query the WAF documentation
   */
  async query(request: WAFQueryRequest): Promise<WAFQueryResponse> {
    logger.info("Processing WAF query", { question: request.question });

    try {
      // Use long-running service instead of spawning new process
      const result = await this.queryLongRunningService(
        request.question,
        request.topK || 3
      );

      // Handle error responses
      if (result.error) {
        throw new Error(result.message || result.error);
      }

      logger.info("WAF query completed", {
        hasResults: result.has_results,
        sourceCount: result.sources?.length || 0,
      });

      return {
        answer: result.answer,
        sources: result.sources || [],
        scores: result.scores || [],
        hasResults: result.has_results || false,
        discussionEnabled: result.discussion_enabled,
        suggestedFollowUps: result.suggested_follow_ups,
      };
    } catch (error) {
      logger.error("WAF query failed", { error });
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to query WAF documentation: ${message}`);
    }
  }

  /**
   * Old query method using spawn (kept as fallback)
   */
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  private async queryWithSpawn(
    request: WAFQueryRequest
  ): Promise<WAFQueryResponse> {
    logger.info("Processing WAF query with spawn", {
      question: request.question,
    });

    try {
      // Prepare query input
      const queryInput = JSON.stringify({
        question: request.question,
        top_k: request.topK || 5,
        metadata_filters: request.metadataFilters || null,
      });

      // Execute query wrapper with input via stdin
      const result = await this.executePythonScriptWithInput(
        "query_wrapper.py",
        queryInput,
        120000 // 2 minutes for LLM generation
      );

      // Parse JSON response
      const response = JSON.parse(result) as {
        answer: string;
        sources?: Array<{
          url: string;
          title: string;
          section: string;
          score: number;
        }>;
        scores?: number[];
        has_results?: boolean;
        discussion_enabled?: boolean;
        suggested_follow_ups?: string[];
      };

      logger.info("WAF query completed", {
        hasResults: response.has_results,
        sourceCount: response.sources?.length || 0,
      });

      return {
        answer: response.answer,
        sources: response.sources || [],
        scores: response.scores || [],
        hasResults: response.has_results || false,
        discussionEnabled: response.discussion_enabled,
        suggestedFollowUps: response.suggested_follow_ups,
      };
    } catch (error) {
      logger.error("WAF query failed", { error });
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to query WAF documentation: ${message}`);
    }
  }

  /**
   * Execute Python script with stdin input
   */
  private async executePythonScriptWithInput(
    scriptName: string,
    input: string,
    timeout: number = 60000
  ): Promise<string> {
    return new Promise((resolve, reject) => {
      const scriptPath = join(this.ragPath, scriptName);

      logger.info(`Executing Python script with input: ${scriptName}`);

      // Calculate absolute path to storage directory
      const rootPath = join(this.ragPath, "..", "..", "..");
      const storageDir = join(
        rootPath,
        "data",
        "knowledge_bases",
        "waf",
        "index"
      );

      logger.info("[WAFService] Path calculation for query:", {
        ragPath: this.ragPath,
        rootPath,
        storageDir,
        envVar: "WAF_STORAGE_DIR will be set to: " + storageDir,
      });

      const pythonProcess = spawn(this.pythonPath, [scriptPath], {
        cwd: this.ragPath,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
          WAF_STORAGE_DIR: storageDir,
        },
      });

      let stdout = "";
      let stderr = "";

      pythonProcess.stdout.on("data", (data: Buffer) => {
        stdout += data.toString();
      });

      pythonProcess.stderr.on("data", (data: Buffer) => {
        stderr += data.toString();
      });

      // Write input to stdin
      pythonProcess.stdin.write(input);
      pythonProcess.stdin.end();

      const timeoutHandle = setTimeout(() => {
        pythonProcess.kill();
        reject(new Error(`Python script timeout after ${timeout}ms`));
      }, timeout);

      pythonProcess.on("close", (code) => {
        clearTimeout(timeoutHandle);

        // Log stderr even on success (contains Python logging output)
        if (stderr) {
          logger.info("Python stderr output:", { stderr });
        }

        if (code === 0) {
          resolve(stdout);
        } else {
          logger.error("Python script failed", { code, stderr });
          reject(
            new Error(`Python script failed with code ${code}: ${stderr}`)
          );
        }
      });

      pythonProcess.on("error", (error) => {
        clearTimeout(timeoutHandle);
        reject(error);
      });
    });
  }

  /**
   * Check if the WAF index exists and is ready
   */
  async isIndexReady(): Promise<boolean> {
    const fs = await import("fs/promises");
    const rootPath = join(this.ragPath, "..", "..", "..");
    const indexPath = join(rootPath, "data", "knowledge_bases", "waf", "index");

    try {
      await fs.access(indexPath);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get ingestion status
   */
  async getIngestionStatus(): Promise<IngestionStatus> {
    const indexReady = await this.isIndexReady();

    // Check phase files
    const rootPath = join(this.ragPath, "..", "..", "..");
    const dataPath = join(rootPath, "data", "knowledge_bases", "waf");
    const manifestPath = join(dataPath, "manifest.json");
    const cleanedDocsPath = join(dataPath, "documents");

    let stage = "not_started";
    let progress = 0;
    let message = "Ingestion not started";

    try {
      if (indexReady) {
        stage = "complete";
        progress = 100;
        message = "Index ready for queries";
      } else if (await this.fileExists(manifestPath)) {
        // Check if documents are approved
        const fs = await import("fs/promises");
        const manifestContent = await fs.readFile(manifestPath, "utf-8");
        const manifest = JSON.parse(manifestContent) as Array<{
          status: string;
        }>;
        const approvedCount = manifest.filter(
          (doc) => doc.status === "APPROVED"
        ).length;
        const pendingCount = manifest.filter(
          (doc) => doc.status === "PENDING_REVIEW"
        ).length;

        if (approvedCount > 0 && pendingCount === 0) {
          stage = "ready_for_phase2";
          progress = 60;
          message = `Phase 1 complete. ${approvedCount} documents approved. Ready for Phase 2.`;
        } else if (pendingCount > 0) {
          stage = "pending_validation";
          progress = 50;
          message = `Phase 1 complete. ${pendingCount} documents pending validation.`;
        } else {
          stage = "phase1_complete";
          progress = 50;
          message = "Phase 1 complete. Awaiting document validation.";
        }
      } else if (await this.fileExists(cleanedDocsPath)) {
        stage = "phase1_running";
        progress = 30;
        message = "Phase 1: Cleaning documents...";
      }
    } catch (error) {
      logger.error("Error checking ingestion status", { error });
    }

    return {
      stage,
      progress,
      message,
      isComplete: stage === "complete",
    };
  }

  private async fileExists(path: string): Promise<boolean> {
    const fs = await import("fs/promises");
    try {
      await fs.access(path);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Cleanup: stop the query service process
   */
  public cleanup(): void {
    if (this.queryProcess) {
      logger.info("[WAFService] Shutting down query service");

      try {
        // Send exit command
        this.queryProcess.stdin.write(
          JSON.stringify({ command: "exit" }) + "\n"
        );

        // Force kill after 5 seconds if not closed
        setTimeout(() => {
          if (this.queryProcess) {
            this.queryProcess.kill();
          }
        }, 5000);
      } catch (error) {
        logger.error("[WAFService] Error during cleanup", { error });
        this.queryProcess.kill();
      }
    }
  }
}

// Singleton instance
export const wafService = new WAFService();

// Cleanup on process exit
process.on("SIGINT", () => {
  logger.info("SIGINT received, cleaning up...");
  wafService.cleanup();
  process.exit(0);
});

process.on("SIGTERM", () => {
  logger.info("SIGTERM received, cleaning up...");
  wafService.cleanup();
  process.exit(0);
});
