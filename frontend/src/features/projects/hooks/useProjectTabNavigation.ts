import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ProjectTab } from "../tabs";

export function useProjectTabNavigation(
  projectId: string | undefined,
  tabs: readonly ProjectTab[]
) {
  const navigate = useNavigate();
  const location = useLocation();

  const segments = location.pathname.split("/");
  const lastSegment = segments[segments.length - 1];
  const currentPath = lastSegment !== "" ? lastSegment : "documents";

  const activeTabMatch = tabs.find((t) => t.path === currentPath);
  const activeTab =
    activeTabMatch !== undefined ? activeTabMatch.id : "documents";

  const setActiveTab = useCallback(
    (tabId: string) => {
      const tab = tabs.find((t) => t.id === tabId);
      if (tab === undefined) return;

      if (projectId !== undefined && projectId !== "") {
        void navigate(`/projects/${projectId}/${tab.path}`);
      }
    },
    [navigate, projectId, tabs]
  );

  return { activeTab, setActiveTab };
}
