import type { ProjectState } from "../types/api-project";
import type { ProjectWorkspaceView } from "../types/api-workspace";
import { API_BASE } from "../../../shared/config/api";
import { fetchWithErrorHandling } from "../../../shared/http/fetchWithErrorHandling";
import { workspaceToProjectState } from "./workspaceStateAdapter";

export const stateApi = {
  async fetch(projectId: string): Promise<ProjectState | null> {
    try {
      const data = await fetchWithErrorHandling<ProjectWorkspaceView>(
        `${API_BASE}/projects/${projectId}/workspace`,
        {},
        "fetch workspace state",
      );
      return workspaceToProjectState(data);
    } catch (error) {
      if (error instanceof Error && error.message.includes("404")) {
        return null;
      }
      throw error;
    }
  },
};
