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
  KBStatusSimple,
  KBIngestionDetails,
} from "../types/ingestion";
import { ServiceError, fetchWithErrorHandling } from "./serviceError";

const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

// Re-export ServiceError as IngestionAPIError for backward compatibility
export { ServiceError as IngestionAPIError };

/**
 * Create a new knowledge base
 */
export async function createKB(
  request: CreateKBRequest
): Promise<CreateKBResponse> {
  return fetchWithErrorHandling<CreateKBResponse>(
    `${API_BASE}/kb/create`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    },
    "create KB"
  );
}

/**
 * Start ingestion for a KB
 */
export async function startIngestion(
  kbId: string
): Promise<StartIngestionResponse> {
  return fetchWithErrorHandling<StartIngestionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/start`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ kb_id: kbId }),
    },
    "start ingestion"
  );
}

/**
 * Get job status for a KB
 */
// Phase 3: KB-level status (ready | pending | not_ready)
export async function getKBReadyStatus(kbId: string): Promise<KBStatusSimple> {
  return fetchWithErrorHandling<KBStatusSimple>(
    `${API_BASE}/kb/${kbId}/status`,
    { method: "GET" },
    "get KB status"
  );
}

// Phase 3: Ingestion details for pending state
export async function getKBIngestionDetails(
  kbId: string
): Promise<KBIngestionDetails> {
  return fetchWithErrorHandling<KBIngestionDetails>(
    `${API_BASE}/ingestion/kb/${kbId}/details`,
    { method: "GET" },
    "get ingestion details"
  );
}

/**
 * Get full ingestion job view for a KB (single-call shape for frontend)
 */
export async function getKBJobView(kbId: string): Promise<IngestionJob> {
  return fetchWithErrorHandling<IngestionJob>(
    `${API_BASE}/ingestion/kb/${kbId}/job-view`,
    { method: "GET" },
    "get KB job view"
  );
}

export async function pauseIngestion(
  kbId: string
): Promise<{ message: string; kb_id: string }> {
  return fetchWithErrorHandling<{ message: string; kb_id: string }>(
    `${API_BASE}/ingestion/kb/${kbId}/pause`,
    { method: "POST" },
    "pause ingestion"
  );
}

export async function resumeIngestion(
  kbId: string
): Promise<{ message: string; kb_id: string }> {
  return fetchWithErrorHandling<{ message: string; kb_id: string }>(
    `${API_BASE}/ingestion/kb/${kbId}/resume`,
    { method: "POST" },
    "resume ingestion"
  );
}

export async function cancelIngestion(
  kbId: string
): Promise<{ message: string; kb_id: string }> {
  return fetchWithErrorHandling<{ message: string; kb_id: string }>(
    `${API_BASE}/ingestion/kb/${kbId}/cancel`,
    { method: "POST" },
    "cancel ingestion"
  );
}

/**
 * Delete a knowledge base and all its data
 */
export async function deleteKB(kbId: string): Promise<void> {
  await fetchWithErrorHandling<void>(
    `${API_BASE}/kb/${kbId}`,
    { method: "DELETE" },
    "delete KB"
  );
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

  return fetchWithErrorHandling<JobListResponse>(
    url,
    { method: "GET" },
    "list jobs"
  );
}

/**
 * List all knowledge bases
 */
export async function listKBs(): Promise<KnowledgeBase[]> {
  const data = await fetchWithErrorHandling<{
    knowledge_bases: KnowledgeBase[];
  }>(`${API_BASE}/kb/list`, { method: "GET" }, "list KBs");
  return data.knowledge_bases || [];
}
