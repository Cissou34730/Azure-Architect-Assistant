/**
 * KB Ingestion API Service
 */

import {
  CreateKBRequest,
  CreateKBResponse,
  StartIngestionResponse,
  IngestionJob,
  JobListResponse,
  KnowledgeBase,
  APIError,
} from "../types/ingestion";

const API_BASE = "http://localhost:8000/api";

/**
 * Custom error class for API errors
 */
class IngestionAPIError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
    public readonly detail?: string
  ) {
    super(message);
    this.name = "IngestionAPIError";
  }
}

/**
 * Handle API response errors consistently
 */
async function handleResponse<T>(
  response: Response,
  defaultError: string
): Promise<T> {
  if (!response.ok) {
    let errorData: Partial<APIError> = {};
    try {
      errorData = await response.json();
    } catch {
      errorData = { detail: defaultError };
    }
    throw new IngestionAPIError(
      errorData.detail || errorData.message || defaultError,
      response.status,
      errorData.detail
    );
  }
  return response.json();
}

/**
 * Create a new knowledge base
 */
export async function createKB(
  request: CreateKBRequest
): Promise<CreateKBResponse> {
  const response = await fetch(`${API_BASE}/kb/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  return handleResponse<CreateKBResponse>(response, "Failed to create KB");
}

/**
 * Start ingestion for a KB
 */
export async function startIngestion(
  kbId: string
): Promise<StartIngestionResponse> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ kb_id: kbId }),
  });

  return handleResponse<StartIngestionResponse>(
    response,
    "Failed to start ingestion"
  );
}

/**
 * Get job status for a KB
 */
export async function getKBStatus(kbId: string): Promise<IngestionJob> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/status`);
  return handleResponse<IngestionJob>(response, "Failed to get status");
}

/**
 * Cancel a running job
 */
export async function cancelJob(kbId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/cancel`, {
    method: "POST",
  });

  await handleResponse<void>(response, "Failed to cancel job");
}

/**
 * Pause a running job
 */
export async function pauseJob(kbId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/pause`, {
    method: "POST",
  });

  await handleResponse<void>(response, "Failed to pause job");
}

/**
 * Resume a paused job
 */
export async function resumeJob(kbId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/resume`, {
    method: "POST",
  });

  await handleResponse<void>(response, "Failed to resume job");
}

/**
 * Delete a knowledge base and all its data
 */
export async function deleteKB(kbId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/kb/${kbId}`, {
    method: "DELETE",
  });

  await handleResponse<void>(response, "Failed to delete KB");
}

/**
 * List all jobs, optionally filtered by KB
 */
export async function listJobs(
  kbId?: string,
  limit?: number
): Promise<JobListResponse> {
  const params = new URLSearchParams();
  if (kbId) params.append("kb_id", kbId);
  if (limit) params.append("limit", limit.toString());

  const url = `${API_BASE}/ingestion/jobs${
    params.toString() ? `?${params.toString()}` : ""
  }`;
  const response = await fetch(url);

  return handleResponse<JobListResponse>(response, "Failed to list jobs");
}

/**
 * List all knowledge bases
 */
export async function listKBs(): Promise<KnowledgeBase[]> {
  const response = await fetch(`${API_BASE}/kb/list`);
  const data = await handleResponse<{ knowledge_bases: KnowledgeBase[] }>(
    response,
    "Failed to list KBs"
  );
  return data.knowledge_bases || [];
}

export { IngestionAPIError };
