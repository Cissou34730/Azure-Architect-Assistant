import { useCallback, useEffect, useState } from "react";
import type { ProjectState } from "../../../types/agent";

const API_BASE = `${
  import.meta.env.BACKEND_URL || "http://localhost:8000"
}/api`;

export function useProjectState(selectedProjectId: string) {
  const [projectState, setProjectState] = useState<ProjectState | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadProjectState = useCallback(async () => {
    if (!selectedProjectId) {
      setProjectState(null);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/projects/${selectedProjectId}/state`
      );
      const data = await response.json();
      setProjectState(data.projectState);
    } catch (error) {
      console.error("Failed to load project state:", error);
      setProjectState(null);
    } finally {
      setIsLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    void loadProjectState();
  }, [loadProjectState]);

  return {
    projectState,
    isLoading,
    setProjectState,
    refreshState: loadProjectState,
  };
}
