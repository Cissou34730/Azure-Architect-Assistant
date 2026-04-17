import { useMemo, useEffect } from "react";
import type { ProjectContextType } from "./types";
import { projectInputContext } from "./ProjectInputContext";
import { projectChatContext } from "./ProjectChatContext";
import { projectStateContext } from "./ProjectStateContext";
import { projectMetaContext } from "./ProjectMetaContext";
import { ErrorBoundary } from "../../../shared/ui/ErrorBoundary";
import { useRenderCount } from "../../../shared/hooks/useRenderCount";

// eslint-disable-next-line max-lines-per-function -- Provider composition keeps the workspace contexts memoized in one place.
export function ProjectProvider({
  value,
  children,
}: {
  readonly value: ProjectContextType;
  readonly children: React.ReactNode;
}) {
  useRenderCount("ProjectProvider");
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log("[Context] ProjectState value changed");
    }
  }, [value.projectState]);
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.log("[Context] ProjectChat (messages) value changed");
    }
  }, [value.messages]);

  const stateValue = useMemo(() => ({
    projectState: value.projectState,
    loading: value.loadingState,
    refreshState: value.refreshState,
    analyzeDocuments: value.analyzeDocuments,
  }), [value.projectState, value.loadingState, value.refreshState, value.analyzeDocuments]);

  const metaValue = useMemo(() => ({
    selectedProject: value.selectedProject,
    setSelectedProject: value.setSelectedProject,
    loadingProject: value.loadingProject,
  }), [
    value.selectedProject,
    value.setSelectedProject,
    value.loadingProject,
  ]);

  const chatValue = useMemo(() => ({
    messages: value.messages,
    sendMessage: value.sendMessage,
    loading: value.loadingChat,
    loadingMessage: value.loadingMessage,
    refreshMessages: value.refreshMessages,
    fetchOlderMessages: value.fetchOlderMessages,
    failedMessages: value.failedMessages,
    retrySendMessage: value.retrySendMessage,
    activeReview: value.activeReview,
  }), [
    value.messages,
    value.sendMessage,
    value.loadingChat,
    value.loadingMessage,
    value.refreshMessages,
    value.fetchOlderMessages,
    value.failedMessages,
    value.retrySendMessage,
    value.activeReview,
  ]);

  const inputValue = useMemo(() => ({
    textRequirements: value.textRequirements,
    setTextRequirements: value.setTextRequirements,
    files: value.files,
    setFiles: value.setFiles,
    inputWorkflow: value.inputWorkflow,
    isUploadingDocuments: value.isUploadingDocuments,
    isAnalyzingDocuments: value.isAnalyzingDocuments,
    clearInputWorkflowMessage: value.clearInputWorkflowMessage,
    handleUploadDocuments: value.handleUploadDocuments,
    handleAnalyzeDocuments: value.handleAnalyzeDocuments,
    handleSaveTextRequirements: value.handleSaveTextRequirements,
    handleGenerateProposal: value.handleGenerateProposal,
  }), [
    value.textRequirements,
    value.setTextRequirements,
    value.files,
    value.setFiles,
    value.inputWorkflow,
    value.isUploadingDocuments,
    value.isAnalyzingDocuments,
    value.clearInputWorkflowMessage,
    value.handleUploadDocuments,
    value.handleAnalyzeDocuments,
    value.handleSaveTextRequirements,
    value.handleGenerateProposal,
  ]);

  return (
    <ErrorBoundary>
      <projectMetaContext.Provider value={metaValue}>
        <ErrorBoundary>
          <projectInputContext.Provider value={inputValue}>
            <ErrorBoundary>
              <projectStateContext.Provider value={stateValue}>
                <ErrorBoundary>
                  <projectChatContext.Provider value={chatValue}>
                    {children}
                  </projectChatContext.Provider>
                </ErrorBoundary>
              </projectStateContext.Provider>
            </ErrorBoundary>
          </projectInputContext.Provider>
        </ErrorBoundary>
      </projectMetaContext.Provider>
    </ErrorBoundary>
  );
}

