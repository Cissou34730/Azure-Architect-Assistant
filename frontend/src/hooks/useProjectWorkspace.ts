import { useState, useEffect, useCallback } from "react";
import { useProjects } from "./useProjects";
import { useProjectState } from "./useProjectState";
import { useChat } from "./useChat";
import { useProposal } from "./useProposal";

export function useProjectWorkspace() {
  const [activeTab, setActiveTab] = useState<
    "documents" | "chat" | "state" | "proposal"
  >("documents");
  const [projectName, setProjectName] = useState("");
  const [textRequirements, setTextRequirements] = useState("");
  const [files, setFiles] = useState<FileList | null>(null);

  const projectsHook = useProjects();
  const { selectedProject } = projectsHook;

  const stateHook = useProjectState(selectedProject?.id ?? null);
  const chatHook = useChat(selectedProject?.id ?? null);
  const proposalHook = useProposal();

  const loading =
    projectsHook.loading ||
    stateHook.loading ||
    chatHook.loading ||
    proposalHook.loading;
  const loadingMessage = chatHook.loadingMessage;

  // Logging helper (disabled for production)
  const logAction = useCallback(
    (_action: string, _details?: Record<string, unknown>) => {
      // Logging disabled - enable for debugging if needed
      // console.log(`[${new Date().toISOString()}] ${action}`, details || "");
    },
    []
  );

  // Update text requirements when project changes
  useEffect(() => {
    if (selectedProject) {
      logAction("Project selected", {
        projectId: selectedProject.id,
        name: selectedProject.name,
      });
      setTextRequirements(selectedProject.textRequirements || "");
    }
  }, [selectedProject, logAction]);

  // Log state changes
  useEffect(() => {
    if (stateHook.projectState) {
      logAction("Project state changed in UI", {
        projectId: stateHook.projectState.projectId,
        lastUpdated: stateHook.projectState.lastUpdated,
        openQuestionsCount: stateHook.projectState.openQuestions.length,
      });
    }
  }, [stateHook.projectState, logAction]);

  // Refresh state when switching to State tab
  useEffect(() => {
    if (activeTab === "state" && selectedProject) {
      logAction("State tab activated, refreshing project state");
      void stateHook.refreshState();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, selectedProject, logAction]);

  // Handler functions
  const handleCreateProject = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!projectName.trim()) return;

    try {
      await projectsHook.createProject(projectName);
      setProjectName("");
    } catch (error) {
      console.error("Error creating project:", error);
    }
  };

  const handleUploadDocuments = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!files || files.length === 0) return;

    try {
      await projectsHook.uploadDocuments(files);
      alert("Documents uploaded successfully!");
      setFiles(null);
      const fileInput = document.getElementById(
        "file-input"
      ) as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (error) {
      console.error("Error uploading documents:", error);
    }
  };

  const handleSaveTextRequirements = async (): Promise<void> => {
    try {
      await projectsHook.saveTextRequirements(textRequirements);
      alert("Requirements saved successfully!");
    } catch (error) {
      console.error("Error saving requirements:", error);
    }
  };

  const handleAnalyzeDocuments = async (): Promise<void> => {
    if (!selectedProject) return;

    if (
      !selectedProject.textRequirements?.trim() &&
      (!files || files.length === 0)
    ) {
      alert(
        "Please provide either text requirements or upload documents before analyzing."
      );
      return;
    }

    try {
      await stateHook.analyzeDocuments();
      setActiveTab("state");
      alert("Analysis complete!");
    } catch (error: unknown) {
      const message =
        error instanceof Error ? error.message : "Failed to analyze documents";
      alert(`Error: ${message}`);
    }
  };

  const handleSendChatMessage = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!chatHook.chatInput.trim()) return;

    const userMessage = chatHook.chatInput;
    logAction("Sending chat message", {
      projectId: selectedProject?.id,
      messagePreview: userMessage.substring(0, 50),
    });

    try {
      await chatHook.sendMessage(userMessage);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : "Unknown error";
      logAction("Chat message failed", { error: message });
      alert(`Error: ${message}`);
    }
  };

  const handleGenerateProposal = (): void => {
    if (!selectedProject) return;

    logAction("User initiated proposal generation", {
      projectId: selectedProject.id,
    });
    proposalHook.generateProposal(selectedProject.id, () => {
      logAction("Proposal generation complete, refreshing state");
      void stateHook.refreshState();
    });
  };

  return {
    // UI State
    activeTab,
    setActiveTab,
    projectName,
    setProjectName,
    textRequirements,
    setTextRequirements,
    files,
    setFiles,
    loading,
    loadingMessage,

    // Data from hooks
    projects: projectsHook.projects,
    selectedProject,
    setSelectedProject: projectsHook.setSelectedProject,
    projectState: stateHook.projectState,
    messages: chatHook.messages,
    chatInput: chatHook.chatInput,
    setChatInput: chatHook.setChatInput,
    architectureProposal: proposalHook.architectureProposal,
    proposalStage: proposalHook.proposalStage,

    // Handler functions
    handleCreateProject,
    handleUploadDocuments,
    handleSaveTextRequirements,
    handleAnalyzeDocuments,
    handleSendChatMessage,
    handleGenerateProposal,
    refreshState: stateHook.refreshState,
    fetchProjects: projectsHook.fetchProjects,
  };
}
