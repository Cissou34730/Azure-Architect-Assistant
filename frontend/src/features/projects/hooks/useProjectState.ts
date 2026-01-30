/**
 * Custom hook for project state management
 */

import { useState, useCallback, useEffect, useMemo } from "react";
import { ProjectState } from "../../../types/api";
import { stateApi } from "../../../services/stateService";
import { projectApi } from "../../../services/projectService";

export const useProjectState = (projectId: string | null) => {
  const [projectState, setProjectState] = useState<ProjectState | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchProjectState = useCallback(async () => {
    if (projectId === null || projectId === "") {
      return;
    }

    try {
      const state = await stateApi.fetch(projectId);
      setProjectState(state);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Fetch failed";
      console.error(`Error fetching project state: ${msg}`);
    }
  }, [projectId]);

  const analyzeDocuments = useCallback(async () => {
    if (projectId === null || projectId === "") {
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

  return useMemo(
    () => ({
      projectState,
      setProjectState,
      loading,
      analyzeDocuments,
      refreshState: fetchProjectState,
    }),
    [projectState, loading, analyzeDocuments, fetchProjectState],
  );
};
