import { useCallback } from "react";
import type { NavigateFunction } from "react-router-dom";

export function useUnifiedNavigation(
  projectId: string | undefined,
  navigate: NavigateFunction,
) {
  const handleNavigateToDiagrams = useCallback(() => {
    if (projectId !== undefined && projectId !== "") {
      void navigate(`/project/${projectId}/deliverables?tab=diagrams`);
    }
  }, [navigate, projectId]);

  const handleNavigateToAdrs = useCallback(() => {
    if (projectId !== undefined && projectId !== "") {
      void navigate(`/project/${projectId}/deliverables?tab=adrs`);
    }
  }, [navigate, projectId]);

  const handleNavigateToCosts = useCallback(() => {
    if (projectId !== undefined && projectId !== "") {
      void navigate(`/project/${projectId}/deliverables?tab=costs`);
    }
  }, [navigate, projectId]);

  return {
    handleNavigateToDiagrams,
    handleNavigateToAdrs,
    handleNavigateToCosts,
  };
}
