import { Project, ProjectState, UploadSummary } from "../types/api";
import { API_BASE } from "./config";
import { fetchWithErrorHandling } from "./serviceError";

interface UploadDocumentsResponse {
  readonly documents: readonly Record<string, unknown>[];
  readonly uploadSummary: UploadSummary;
}

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

  async uploadDocuments(
    projectId: string,
    files: FileList,
  ): Promise<UploadDocumentsResponse> {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("documents", file);
    });

    const data = await fetchWithErrorHandling<UploadDocumentsResponse>(
      `${API_BASE}/projects/${projectId}/documents`,
      {
        method: "POST",
        body: formData,
      },
      "upload documents"
    );
    return data;
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

  async delete(projectId: string): Promise<void> {
    await fetchWithErrorHandling<{
      readonly message: string;
      readonly deletedCount: number;
      readonly projectIds: readonly string[];
    }>(
      `${API_BASE}/projects/${projectId}`,
      {
        method: "DELETE",
      },
      "delete project"
    );
  },

  async bulkDelete(
    projectIds: readonly string[]
  ): Promise<{ readonly deletedCount: number }> {
    const data = await fetchWithErrorHandling<{
      readonly message: string;
      readonly deletedCount: number;
      readonly projectIds: readonly string[];
    }>(
      `${API_BASE}/projects/bulk-delete`,
      {
        method: "POST",
        headers: {
          // eslint-disable-next-line @typescript-eslint/naming-convention
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ projectIds }),
      },
      "bulk delete projects"
    );
    return { deletedCount: data.deletedCount };
  },
};
