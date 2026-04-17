import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";
import type { JsonObject } from "../../../shared/lib/json";
import type { ProjectState } from "../types/api-project";
import type {
  PendingChangeDetail,
  PendingChangeStatus,
  PendingChangeSummary,
} from "../types/pending-changes";

export interface PendingChangeReviewResult {
  readonly changeSet: PendingChangeDetail;
  readonly projectState: ProjectState | null;
  readonly conflicts: readonly JsonObject[];
}

interface PendingChangesListOptions {
  readonly status?: PendingChangeStatus;
}

export const pendingChangesApi = {
  async list(
    projectId: string,
    options?: PendingChangesListOptions,
  ): Promise<readonly PendingChangeSummary[]> {
    const querySuffix =
      options?.status !== undefined
        ? `?status=${encodeURIComponent(options.status)}`
        : "";
    return fetchWithErrorHandling<readonly PendingChangeSummary[]>(
      `${API_BASE}/projects/${projectId}/pending-changes${querySuffix}`,
      {},
      "list pending changes",
    );
  },

  async get(projectId: string, changeSetId: string): Promise<PendingChangeDetail> {
    return fetchWithErrorHandling<PendingChangeDetail>(
      `${API_BASE}/projects/${projectId}/pending-changes/${changeSetId}`,
      {},
      "load pending change",
    );
  },

  async approve(
    projectId: string,
    changeSetId: string,
    reason: string | null,
  ): Promise<PendingChangeReviewResult> {
    return fetchWithErrorHandling<PendingChangeReviewResult>(
      `${API_BASE}/projects/${projectId}/pending-changes/${changeSetId}/approve`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      },
      "approve pending change",
    );
  },

  async reject(
    projectId: string,
    changeSetId: string,
    reason: string | null,
  ): Promise<PendingChangeReviewResult> {
    return fetchWithErrorHandling<PendingChangeReviewResult>(
      `${API_BASE}/projects/${projectId}/pending-changes/${changeSetId}/reject`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      },
      "reject pending change",
    );
  },
};
