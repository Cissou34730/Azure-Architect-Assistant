import { ProjectState } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

export const stateApi = {
  async fetch(projectId: string): Promise<ProjectState | null> {
    try {
      return await fetchWithErrorHandling<ProjectState>(
        `${API_BASE}/project-state/${projectId}`,
        {},
        "fetch state"
      );
    } catch (error) {
      if (error instanceof Error && error.message.includes("404")) {
        return null;
      }
      throw error;
    }
  },
};
