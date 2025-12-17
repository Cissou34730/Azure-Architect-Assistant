import { useState, useEffect } from "react";
import type { ProjectState } from "../../../types/agent";

export function useProjectState(selectedProjectId: string) {
  const [projectState, setProjectState] = useState<ProjectState | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadProjectState = async () => {
    if (!selectedProjectId) {
      setProjectState(null);
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(
        `http://localhost:8080/api/projects/${selectedProjectId}/state`
      );
      const data = await response.json();
      setProjectState(data.projectState);
    } catch (error) {
      console.error("Failed to load project state:", error);
      setProjectState(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void loadProjectState();
  }, [selectedProjectId]);

  return {
    projectState,
    isLoading,
    setProjectState,
    refreshState: loadProjectState,
  };
}
