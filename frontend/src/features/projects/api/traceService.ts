import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";
import type { ProjectTraceEventsResponse } from "../types/trace";

export const traceApi = {
  async list(projectId: string): Promise<ProjectTraceEventsResponse> {
    return fetchWithErrorHandling<ProjectTraceEventsResponse>(
      `${API_BASE}/projects/${projectId}/trace`,
      {},
      "load project trace",
    );
  },
};
