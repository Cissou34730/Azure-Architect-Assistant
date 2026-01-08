import { fetchWithErrorHandling } from "../serviceError";

const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

type ProjectState = Record<string, unknown>;

export const aaaProjectApi = {
  async uploadDocuments(projectId: string, files: FileList): Promise<void> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("documents", file);
    });

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
