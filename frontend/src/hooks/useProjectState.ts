/**
 * Custom hook for project state management
 */

import { useState, useCallback, useEffect } from "react";
import { ProjectState, stateApi, projectApi } from "../services/apiService";

export const useProjectState = (projectId: string | null) => {
  const [projectState, setProjectState] = useState<ProjectState | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchProjectState = useCallback(async () => {
    if (!projectId) return;

    try {
      const state = await stateApi.fetch(projectId);
      setProjectState(state);
    } catch (error) {
      console.error("Error fetching project state:", error);
    }
  }, [projectId]);

  const analyzeDocuments = useCallback(async () => {
    if (!projectId) {
      throw new Error("No project selected");
    }

    setLoading(true);
    try {
      const state = await projectApi.analyzeDocuments(projectId);
      setProjectState(state);
      return state;
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void fetchProjectState();
  }, [fetchProjectState]);

  return {
    projectState,
    setProjectState,
    loading,
    analyzeDocuments,
    refreshState: fetchProjectState,
  };
};
