import { fetchWithErrorHandling } from "../serviceError";

import { API_BASE } from "../config";

// eslint-disable-next-line @typescript-eslint/no-restricted-types -- Dynamic backend state structure
type ProjectState = Record<string, unknown>;

export const aaaProjectApi = {
  async uploadDocuments(projectId: string, files: FileList): Promise<void> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("documents", file);
    });

    // eslint-disable-next-line @typescript-eslint/no-restricted-types -- Backend returns untyped document metadata
    await fetchWithErrorHandling<{ documents: unknown[] }>(
      `${API_BASE}/projects/${projectId}/documents`,
      { method: "POST", body: formData },
      "upload project documents"
    );
  },

  async analyzeDocuments(projectId: string): Promise<ProjectState> {
    const data = await fetchWithErrorHandling<{ projectState: ProjectState }>(
      `${API_BASE}/projects/${projectId}/analyze-docs`,
      { method: "POST" },
      "analyze project documents"
    );

    return data.projectState;
  },

  async fetchState(projectId: string): Promise<ProjectState | null> {
    try {
      const data = await fetchWithErrorHandling<{ projectState: ProjectState }>(
        `${API_BASE}/projects/${projectId}/state`,
        { method: "GET" },
        "fetch project state"
      );

      return data.projectState;
    } catch {
      // State may not exist yet; treat as empty.
      return null;
    }
  },
};
