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
} from "../types/ingestion";

const API_BASE = "http://localhost:8000/api";

/**
 * Create a new knowledge base
 */
export async function createKB(
  request: CreateKBRequest
): Promise<CreateKBResponse> {
  const response = await fetch(`${API_BASE}/ingestion/kb/create`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Failed to create KB" }));
    throw new Error(error.detail || "Failed to create KB");
  }

  return response.json();
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

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Failed to start ingestion" }));
    throw new Error(error.detail || "Failed to start ingestion");
  }

  return response.json();
}

/**
 * Get job status for a KB
 */
export async function getKBStatus(kbId: string): Promise<IngestionJob> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/status`);

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Failed to get status" }));
    throw new Error(error.detail || "Failed to get status");
  }

  return response.json();
}

/**
 * Cancel a running job
 */
export async function cancelJob(kbId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/ingestion/kb/${kbId}/cancel`, {
    method: "POST",
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Failed to cancel job" }));
    throw new Error(error.detail || "Failed to cancel job");
  }
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

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Failed to list jobs" }));
    throw new Error(error.detail || "Failed to list jobs");
  }

  return response.json();
}

/**
 * List all knowledge bases
 */
export async function listKBs(): Promise<KnowledgeBase[]> {
  const response = await fetch(`${API_BASE}/kb/list`);

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Failed to list KBs" }));
    throw new Error(error.detail || "Failed to list KBs");
  }

  const data = await response.json();
  return data.knowledge_bases || [];
}
