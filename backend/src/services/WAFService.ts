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
  private scriptsPath: string;

  constructor() {
    // Determine Python path (consider virtual environment)
    this.pythonPath = process.env.PYTHON_PATH || "python";
    this.scriptsPath = join(__dirname, "..", "python");

    logger.info("WAF Service initialized", {
      pythonPath: this.pythonPath,
      scriptsPath: this.scriptsPath,
    });
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
      const scriptPath = join(this.scriptsPath, scriptName);

      logger.info(`Executing Python script: ${scriptName}`, { args });

      const pythonProcess = spawn(this.pythonPath, [scriptPath, ...args], {
        cwd: this.scriptsPath,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
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
      await this.executePythonScript("ingestion.py", [], 600000);

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
      await this.executePythonScript("build_index.py", [], 900000); // 15 min for embeddings

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
      const rootPath = join(this.scriptsPath, "..", "..", "..");
      await this.executePythonScript(
        join(rootPath, "auto_approve_docs.py"),
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
   * Run the complete ingestion pipeline (legacy - deprecated)
   */
  private async runIngestionPipeline(jobId: string): Promise<void> {
    await this.runFullIngestionPipeline(jobId);
  }

  /**
   * Query the WAF documentation
   */
  async query(request: WAFQueryRequest): Promise<WAFQueryResponse> {
    logger.info("Processing WAF query", { question: request.question });

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
        60000
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
      const scriptPath = join(this.scriptsPath, scriptName);

      logger.info(`Executing Python script with input: ${scriptName}`);

      const pythonProcess = spawn(this.pythonPath, [scriptPath], {
        cwd: this.scriptsPath,
        env: {
          ...process.env,
          PYTHONUNBUFFERED: "1",
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
    const indexPath = join(this.scriptsPath, "waf_storage_clean");

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
    const rootPath = join(this.scriptsPath, "..", "..", "..");
    const manifestPath = join(rootPath, "validation_manifest.json");
    const cleanedDocsPath = join(rootPath, "cleaned_documents");

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
}

// Singleton instance
export const wafService = new WAFService();
