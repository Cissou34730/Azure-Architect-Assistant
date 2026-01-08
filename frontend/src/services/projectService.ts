import { Project, ProjectState } from "../types/api";

const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

export const projectApi = {
  async get(id: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects/${id}`);
    if (!res.ok) throw new Error("Failed to fetch project");
    return res.json();
  },

  async fetchAll(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/projects`);
    if (!res.ok) throw new Error("Failed to fetch projects");
    return res.json();
  },

  async create(name: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) throw new Error("Failed to create project");
    return res.json();
  },

  async uploadDocuments(projectId: string, files: FileList): Promise<void> {
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files", files[i]);
    }

    const res = await fetch(
      `${API_BASE}/projects/${projectId}/documents/upload`,
      {
        method: "POST",
        body: formData,
      },
    );
    if (!res.ok) throw new Error("Failed to upload documents");
  },

  async saveTextRequirements(
    projectId: string,
    text: string,
  ): Promise<Project> {
    const res = await fetch(
      `${API_BASE}/projects/${projectId}/requirements/text`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      },
    );
    if (!res.ok) throw new Error("Failed to save requirements");
    return res.json();
  },

  async analyzeDocuments(projectId: string): Promise<ProjectState> {
    const res = await fetch(
      `${API_BASE}/projects/${projectId}/documents/analyze`,
      {
        method: "POST",
      },
    );
    if (!res.ok) throw new Error("Failed to analyze documents");
    return res.json();
  },
};
