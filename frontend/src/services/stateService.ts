import { ProjectState } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

export const stateApi = {
  async fetch(projectId: string): Promise<ProjectState | null> {
    try {
      const data = await fetchWithErrorHandling<{
        readonly projectState: ProjectState;
      }>(`${API_BASE}/projects/${projectId}/state`, {}, "fetch state");
      return data.projectState;
    } catch (error) {
      if (error instanceof Error && error.message.includes("404")) {
        return null;
      }
      throw error;
    }
  },
};
