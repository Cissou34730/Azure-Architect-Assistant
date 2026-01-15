import { Project, ProjectState } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

export const projectApi = {
  async get(id: string): Promise<Project> {
    const data = await fetchWithErrorHandling<{ readonly project: Project }>(
      `${API_BASE}/projects/${id}`,
      {},
      "get project"
    );
    return data.project;
  },

  async fetchAll(): Promise<readonly Project[]> {
    const data = await fetchWithErrorHandling<{
      readonly projects: readonly Project[];
    }>(`${API_BASE}/projects`, {}, "fetch projects");
    return data.projects;
  },

  async create(name: string): Promise<Project> {
    const data = await fetchWithErrorHandling<{ readonly project: Project }>(
      `${API_BASE}/projects`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name }),
      },
      "create project"
    );
    return data.project;
  },

  async uploadDocuments(projectId: string, files: FileList): Promise<void> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("documents", file);
    });

    // eslint-disable-next-line @typescript-eslint/no-restricted-types
    await fetchWithErrorHandling<Record<string, unknown>>(
      `${API_BASE}/projects/${projectId}/documents`,
      {
        method: "POST",
        body: formData,
      },
      "upload documents"
    );
  },

  async saveTextRequirements(
    projectId: string,
    text: string
  ): Promise<Project> {
    const data = await fetchWithErrorHandling<{ readonly project: Project }>(
      `${API_BASE}/projects/${projectId}/requirements`,
      {
        method: "PUT",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ textRequirements: text }),
      },
      "save requirements"
    );

    return data.project;
  },

  async analyzeDocuments(projectId: string): Promise<ProjectState> {
    const data = await fetchWithErrorHandling<{
      readonly projectState: ProjectState;
    }>(
      `${API_BASE}/projects/${projectId}/analyze-docs`,
      {
        method: "POST",
      },
      "analyze documents"
    );
    return data.projectState;
  },
};
