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
   * Trigger full WAF ingestion pipeline (crawler -> ingestion -> chunking)
   */
  startIngestion(): { jobId: string; message: string } {
    logger.info("Starting WAF ingestion pipeline");

    // For now, return a job ID and run asynchronously
    // In production, you'd use a proper job queue
    const jobId = `waf-ingestion-${Date.now()}`;

    // Run ingestion in background
    void this.runIngestionPipeline(jobId).catch((error: unknown) => {
      logger.error("Ingestion pipeline failed", { jobId, error });
    });

    return {
      jobId,
      message: "WAF ingestion started. This will take several minutes.",
    };
  }

  /**
   * Run the complete ingestion pipeline
   */
  private async runIngestionPipeline(jobId: string): Promise<void> {
    try {
      logger.info("Step 1: Crawling WAF documentation", { jobId });
      await this.executePythonScript("crawler.py", [], 600000); // 10 min timeout

      logger.info("Step 2: Processing documents", { jobId });
      await this.executePythonScript("ingestion.py", [], 600000);

      logger.info("Step 3: Chunking documents", { jobId });
      await this.executePythonScript("chunker.py", [], 300000);

      logger.info("Step 4: Building vector index", { jobId });
      await this.executePythonScript("indexer.py", [], 900000); // 15 min for embeddings

      logger.info("Ingestion pipeline completed", { jobId });
    } catch (error) {
      logger.error("Ingestion pipeline error", { jobId, error });
      throw error;
    }
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

    // Check intermediate files
    const urlsPath = join(this.scriptsPath, "waf_urls.txt");
    const docsPath = join(this.scriptsPath, "waf_documents.jsonl");
    const chunksPath = join(this.scriptsPath, "chunks_review.jsonl");

    let stage = "not_started";
    let progress = 0;
    let message = "Ingestion not started";

    try {
      if (indexReady) {
        stage = "complete";
        progress = 100;
        message = "Index ready for queries";
      } else if (await this.fileExists(chunksPath)) {
        stage = "indexing";
        progress = 75;
        message = "Building vector index...";
      } else if (await this.fileExists(docsPath)) {
        stage = "chunking";
        progress = 50;
        message = "Chunking documents...";
      } else if (await this.fileExists(urlsPath)) {
        stage = "processing";
        progress = 25;
        message = "Processing documents...";
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
