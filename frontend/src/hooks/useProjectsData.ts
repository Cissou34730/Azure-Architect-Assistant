import { useState, useEffect, useCallback } from "react";
import { Project } from "../types/api";
import { projectApi } from "../services/projectService";

export interface ProjectSelectorState {
  readonly projects: readonly Project[];
  readonly currentProject: Project | null;
  readonly loading: boolean;
  readonly error: string | null;
}

export function useProjectsData(projectId: string | undefined) {
  const [state, setState] = useState<ProjectSelectorState>({
    projects: [],
    currentProject: null,
    loading: false,
    error: null,
  });

  const fetchProjects = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const fetched = await projectApi.fetchAll();
      const current =
        projectId !== undefined
          ? (fetched.find((p) => p.id === projectId) ?? null)
          : null;
      setState((prev) => ({
        ...prev,
        projects: fetched,
        currentProject: current,
      }));
    } catch (err) {
      setState((prev) => ({
        ...prev,
        error: err instanceof Error ? err.message : "Failed to load projects",
      }));
    } finally {
      setState((prev) => ({ ...prev, loading: false }));
    }
  }, [projectId]);

  useEffect(() => {
    void fetchProjects();
  }, [fetchProjects]);

  return { state, setState, fetchProjects };
}
