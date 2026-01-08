import { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Project, projectApi } from "../../../services/apiService";
import { useProjectState } from "./useProjectState";
import { useChat } from "./useChat";
import { useProposal } from "./useProposal";
import { useToast } from "../../../hooks/useToast";
import { getTabs } from "../tabs";

export function useProjectDetails(projectId: string | undefined) {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loadingProject, setLoadingProject] = useState(false);

  // Derive active tab from URL path (last segment)
  const currentPath = location.pathname.split("/").pop() || "documents";
  const tabs = getTabs();
  // Validate if path matches a known tab, default to documents if not found
  // (though routing should handle 404s, this is safe fallback state)
  const activeTab = tabs.find((t) => t.path === currentPath)?.id || "documents";

  const setActiveTab = useCallback(
    (tabId: string) => {
      // Find path for the given tabId
      const tab = tabs.find((t) => t.id === tabId);
      if (!tab) return;

      // Navigate to the new path, preserving the base project URL
      // Assuming structure /projects/:projectId/:tabPath
      // We can use a relative path logic or absolute construction
      if (projectId) {
        void navigate(`/projects/${projectId}/${tab.path}`);
      }
    },
    [navigate, projectId, tabs],
  );

  const [textRequirements, setTextRequirements] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);

  const { success, error: showError, warning } = useToast();

  // Fetch project details
  useEffect(() => {
    if (!projectId) {
      setSelectedProject(null);
      return;
    }

    const fetchProject = async () => {
      setLoadingProject(true);
      try {
        const project = await projectApi.get(projectId);
        setSelectedProject(project);
        // Initialize local state
        setTextRequirements(project.textRequirements ?? "");
      } catch (error) {
        showError("Failed to load project details");
        console.error(error);
      } finally {
        setLoadingProject(false);
      }
    };

    void fetchProject();
  }, [projectId, showError]);

  // Feature Hooks
  const stateHook = useProjectState(selectedProject?.id ?? null);
  const chatHook = useChat(selectedProject?.id ?? null);
  const proposalHook = useProposal();

  const loading =
    loadingProject ||
    stateHook.loading ||
    chatHook.loading ||
    proposalHook.loading;

  const loadingMessage = chatHook.loadingMessage;

  // Logging helper
  const logAction = useCallback(
    (_action: string, _details?: Record<string, unknown>) => {
      // Logging disabled
    },
    [],
  );

  // Sync state changes log
  useEffect(() => {
    if (stateHook.projectState) {
      logAction("Project state changed", {
        projectId: stateHook.projectState.projectId,
      });
    }
  }, [stateHook.projectState, logAction]);

  const handleUploadDocuments = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!files || files.length === 0 || !selectedProject) return;

    try {
      await projectApi.uploadDocuments(selectedProject.id, files);
      success("Documents uploaded successfully!");
      setFiles(null);
      const fileInput = document.getElementById(
        "file-input",
      ) as HTMLInputElement | null;
      if (fileInput) fileInput.value = "";
    } catch (error) {
      console.error("Error uploading documents:", error);
      showError("Failed to upload documents");
    }
  };

  const handleSaveTextRequirements = async (): Promise<void> => {
    if (!selectedProject) return;
    try {
      const updated = await projectApi.saveTextRequirements(
        selectedProject.id,
        textRequirements,
      );
      setSelectedProject(updated); // Update local project to reflect changes
      success("Requirements saved successfully!");
    } catch (error) {
      console.error("Error saving requirements:", error);
      showError("Failed to save requirements");
    }
  };

  const handleAnalyzeDocuments = async (): Promise<void> => {
    if (!selectedProject) return;

    if (
      !selectedProject.textRequirements?.trim() &&
      (!files || files.length === 0)
    ) {
      warning(
        "Please provide either text requirements or upload documents before analyzing.",
      );
      return;
    }

    try {
      const state = await stateHook.analyzeDocuments();
      setActiveTab("state");
      success("Analysis complete!");
      logAction("Analysis success", { stateId: state.projectId });
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to analyze documents";
      showError(`Error: ${message}`);
    }
  };

  const handleSendChatMessage = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!chatHook.chatInput.trim()) return;

    try {
      await chatHook.sendMessage(chatHook.chatInput);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Unknown error";
      showError(`Error: ${message}`);
    }
  };

  const handleGenerateProposal = (): void => {
    if (!selectedProject) return;

    proposalHook.generateProposal(selectedProject.id, () => {
      void stateHook.refreshState();
    });
  };

  return {
    // State
    selectedProject,
    activeTab,
    setActiveTab,
    textRequirements,
    setTextRequirements,
    files,
    setFiles,
    loading,
    loadingMessage,

    // Sub-hooks data
    projectState: stateHook.projectState,
    messages: chatHook.messages,
    chatInput: chatHook.chatInput,
    setChatInput: chatHook.setChatInput,
    architectureProposal: proposalHook.architectureProposal,
    proposalStage: proposalHook.proposalStage,

    // Handlers
    handleUploadDocuments,
    handleSaveTextRequirements,
    handleAnalyzeDocuments,
    handleSendChatMessage,
    handleGenerateProposal,
    refreshState: stateHook.refreshState,
  };
}
