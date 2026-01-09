import { ProjectState } from "../types/api";

const API_BASE = `${import.meta.env.BACKEND_URL}/api`;

export const stateApi = {
  async fetch(projectId: string): Promise<ProjectState | null> {
    const res = await fetch(`${API_BASE}/project-state/${projectId}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("Failed to fetch project state");
    return res.json();
  },
};
