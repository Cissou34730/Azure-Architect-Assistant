import { useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProjectContext } from "../context/useProjectContext";
import { useProjectStateContext } from "../context/useProjectStateContext";
import { useProjectChatContext } from "../context/useProjectChatContext";
import { useUnifiedNavigation } from "./useUnifiedNavigation";
import { useSidePanelState } from "./useSidePanelState";

export function useUnifiedProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  const { loadingProject } = useProjectContext();
  const { projectState, loading: loadingState } = useProjectStateContext();
  const { loading: loadingChat } = useProjectChatContext();

  const loading = loadingProject || loadingState || loadingChat;

  const sidePanelState = useSidePanelState();
  const navigation = useUnifiedNavigation(projectId, navigate);

  // Action handlers
  const handleUploadClick = useCallback(() => {
    console.log("Upload clicked");
  }, []);

  const handleGenerateDiagramClick = useCallback(() => {
    console.log("Generate diagram clicked");
  }, []);

  const handleCreateAdrClick = useCallback(() => {
    console.log("Create ADR clicked");
  }, []);

  const handleExportClick = useCallback(() => {
    console.log("Export clicked");
  }, []);

  return {
    projectId,
    loading,
    projectState,
    ...sidePanelState,
    handleUploadClick,
    handleGenerateDiagramClick,
    handleCreateAdrClick,
    handleExportClick,
    ...navigation,
  };
}
