/**
 * KB Ingestion API Service
 */

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
import { API_BASE } from "./config";

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
      headers: {
        // eslint-disable-next-line @typescript-eslint/naming-convention
        "Content-Type": "application/json",
      },
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
      headers: {
        // eslint-disable-next-line @typescript-eslint/naming-convention
        "Content-Type": "application/json",
      },
      // eslint-disable-next-line @typescript-eslint/naming-convention
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

interface IngestionActionResponse {
  readonly message: string;
  readonly kbId: string;
}

export async function pauseIngestion(
  kbId: string
): Promise<IngestionActionResponse> {
  return fetchWithErrorHandling<IngestionActionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/pause`,
    { method: "POST" },
    "pause ingestion"
  );
}

export async function resumeIngestion(
  kbId: string
): Promise<IngestionActionResponse> {
  return fetchWithErrorHandling<IngestionActionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/resume`,
    { method: "POST" },
    "resume ingestion"
  );
}

export async function cancelIngestion(
  kbId: string
): Promise<IngestionActionResponse> {
  return fetchWithErrorHandling<IngestionActionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/cancel`,
    { method: "POST" },
    "cancel ingestion"
  );
}

/**
 * Delete a knowledge base and all its data
 */
export async function deleteKB(kbId: string): Promise<void> {
  // eslint-disable-next-line @typescript-eslint/no-restricted-types
  await fetchWithErrorHandling<Record<string, unknown>>(
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
  if (typeof kbId === "string" && kbId !== "") {
    params.append("kb_id", kbId);
  }
  if (typeof limit === "number" && !isNaN(limit)) {
    params.append("limit", limit.toString());
  }

  const queryString = params.toString();
  const url = `${API_BASE}/ingestion/jobs${
    queryString !== "" ? `?${queryString}` : ""
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
export async function listKBs(): Promise<readonly KnowledgeBase[]> {
  const data = await fetchWithErrorHandling<{
    readonly knowledgeBases: readonly KnowledgeBase[];
  }>(`${API_BASE}/kb/list`, { method: "GET" }, "list KBs");

  return data.knowledgeBases;
}
