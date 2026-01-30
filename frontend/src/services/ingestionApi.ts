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
  KnowledgeBase,
} from "../types/ingestion";
import { fetchWithErrorHandling } from "./serviceError";
import { API_BASE } from "./config";
import { keysToSnake } from "../utils/apiMapping";

/**
 * Create a new knowledge base
 */
export async function createKB(
  request: CreateKBRequest,
): Promise<CreateKBResponse> {
  return fetchWithErrorHandling<CreateKBResponse>(
    `${API_BASE}/kb/create`,
    {
      method: "POST",
      headers: {
        // eslint-disable-next-line @typescript-eslint/naming-convention
        "Content-Type": "application/json",
      },
      // Backend expects snake_case (kb_id, source_type, source_config, ...)
      body: JSON.stringify(keysToSnake(request)),
    },
    "create KB",
  );
}

/**
 * Start ingestion for a KB
 */
export async function startIngestion(
  kbId: string,
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
    "start ingestion",
  );
}

/**
 * Get full ingestion job view for a KB (single-call shape for frontend)
 */
export async function getKBJobView(kbId: string): Promise<IngestionJob> {
  return fetchWithErrorHandling<IngestionJob>(
    `${API_BASE}/ingestion/kb/${kbId}/job-view`,
    { method: "GET" },
    "get KB job view",
  );
}

interface IngestionActionResponse {
  readonly message: string;
  readonly kbId: string;
}

export async function pauseIngestion(
  kbId: string,
): Promise<IngestionActionResponse> {
  return fetchWithErrorHandling<IngestionActionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/pause`,
    { method: "POST" },
    "pause ingestion",
  );
}

export async function resumeIngestion(
  kbId: string,
): Promise<IngestionActionResponse> {
  return fetchWithErrorHandling<IngestionActionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/resume`,
    { method: "POST" },
    "resume ingestion",
  );
}

export async function cancelIngestion(
  kbId: string,
): Promise<IngestionActionResponse> {
  return fetchWithErrorHandling<IngestionActionResponse>(
    `${API_BASE}/ingestion/kb/${kbId}/cancel`,
    { method: "POST" },
    "cancel ingestion",
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
    "delete KB",
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
