import { useState, useEffect, useCallback } from "react";
import type { ProjectState } from "../../../types/agent";
import { agentApi } from "../../../services/agentService";

export function useProjectState(selectedProjectId: string) {
  const [projectState, setProjectState] = useState<ProjectState | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadProjectState = useCallback(async () => {
    if (selectedProjectId === "") {
      setProjectState(null);
      return;
    }

    setIsLoading(true);
    try {
      const state = await agentApi.getProjectState(selectedProjectId);
      setProjectState(state);
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
