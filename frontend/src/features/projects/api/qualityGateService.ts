import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";
import type { QualityGateReport } from "../types/quality-gate";

export const qualityGateApi = {
  async get(projectId: string): Promise<QualityGateReport> {
    return fetchWithErrorHandling<QualityGateReport>(
      `${API_BASE}/projects/${projectId}/quality-gate`,
      {},
      "load quality gate",
    );
  },
};
