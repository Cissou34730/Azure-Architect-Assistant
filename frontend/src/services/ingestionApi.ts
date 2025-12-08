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
  KBStatusSimple,
  KBIngestionDetails,
} from "../types/ingestion";

const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

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
// Phase 3: KB-level status (ready | pending | not_ready)
export async function getKBReadyStatus(kbId: string): Promise<KBStatusSimple> {
  const response = await fetch(`${API_BASE}/kb/${kbId}/status`);
  return handleResponse<KBStatusSimple>(response, "Failed to get KB status");
}

// Phase 3: Ingestion details for pending state
export async function getKBIngestionDetails(
  kbId: string
): Promise<KBIngestionDetails> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/details`);
  return handleResponse<KBIngestionDetails>(
    response,
    "Failed to get ingestion details"
  );
}

export async function pauseIngestion(
  kbId: string
): Promise<{ message: string; kb_id: string }> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/pause`, {
    method: "POST",
  });
  return handleResponse<{ message: string; kb_id: string }>(
    response,
    "Failed to pause ingestion"
  );
}

export async function resumeIngestion(
  kbId: string
): Promise<{ message: string; kb_id: string }> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/resume`, {
    method: "POST",
  });
  return handleResponse<{ message: string; kb_id: string }>(
    response,
    "Failed to resume ingestion"
  );
}

export async function cancelIngestion(
  kbId: string
): Promise<{ message: string; kb_id: string }> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/cancel`, {
    method: "POST",
  });
  return handleResponse<{ message: string; kb_id: string }>(
    response,
    "Failed to cancel ingestion"
  );
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
