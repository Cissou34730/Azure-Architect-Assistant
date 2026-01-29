import { useMemo, useEffect } from "react";
import type { ProjectContextType } from "./types";
import { projectContextInstance } from "./ProjectContextInstance";
import { projectChatContext } from "./ProjectChatContext";
import { projectStateContext } from "./ProjectStateContext";
import { projectMetaContext } from "./ProjectMetaContext";
import { ErrorBoundary } from "../../../components/common/ErrorBoundary";
import { useRenderCount } from "../../../hooks/useRenderCount";

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
    loading: value.loading,
    refreshState: value.refreshState,
    analyzeDocuments: value.analyzeDocuments,
  }), [value.projectState, value.loading, value.refreshState, value.analyzeDocuments]);

  const metaValue = useMemo(() => ({
    selectedProject: value.selectedProject,
    setSelectedProject: value.setSelectedProject,
    loadingProject: value.loadingProject,
    activeTab: value.activeTab,
    setActiveTab: value.setActiveTab,
  }), [
    value.selectedProject,
    value.setSelectedProject,
    value.loadingProject,
    value.activeTab,
    value.setActiveTab,
  ]);

  const chatValue = useMemo(() => ({
    messages: value.messages,
    sendMessage: value.sendMessage,
    loading: value.loading,
    loadingMessage: value.loadingMessage,
    refreshMessages: value.refreshMessages,
    fetchOlderMessages: value.fetchOlderMessages,
    failedMessages: value.failedMessages,
    retrySendMessage: value.retrySendMessage,
  }), [
    value.messages,
    value.sendMessage,
    value.loading,
    value.loadingMessage,
    value.refreshMessages,
    value.fetchOlderMessages,
    value.failedMessages,
    value.retrySendMessage,
  ]);

  return (
    <ErrorBoundary>
      <projectMetaContext.Provider value={metaValue}>
        <ErrorBoundary>
          <projectContextInstance.Provider value={value}>
            <ErrorBoundary>
              <projectStateContext.Provider value={stateValue}>
                <ErrorBoundary>
                  <projectChatContext.Provider value={chatValue}>
                    {children}
                  </projectChatContext.Provider>
                </ErrorBoundary>
              </projectStateContext.Provider>
            </ErrorBoundary>
          </projectContextInstance.Provider>
        </ErrorBoundary>
      </projectMetaContext.Provider>
    </ErrorBoundary>
  );
}
