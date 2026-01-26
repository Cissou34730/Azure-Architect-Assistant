import { useMemo } from "react";
import type { ProjectContextType } from "./types";
import { projectContextInstance } from "./ProjectContextInstance";
import { ProjectChatContext } from "./ProjectChatContext";
import { ProjectStateContext } from "./ProjectStateContext";
import { ProjectMetaContext } from "./ProjectMetaContext";

export function ProjectProvider({
  value,
  children,
}: {
  readonly value: ProjectContextType;
  readonly children: React.ReactNode;
}) {
  const stateValue = useMemo(() => ({
    projectState: value.projectState ?? null,
    loading: Boolean(value.loading),
    refreshState: value.refreshState,
    analyzeDocuments: value.analyzeDocuments,
  }), [value.projectState, value.loading, value.refreshState, value.analyzeDocuments]);

  const metaValue = useMemo(() => ({
    selectedProject: value.selectedProject ?? null,
    setSelectedProject: value.setSelectedProject,
    loadingProject: Boolean(value.loadingProject),
    activeTab: value.activeTab ?? null,
    setActiveTab: value.setActiveTab,
  }), [
    value.selectedProject,
    value.setSelectedProject,
    value.loadingProject,
    value.activeTab,
    value.setActiveTab,
  ]);

  const chatValue = useMemo(() => ({
    messages: value.messages ?? [],
    sendMessage: value.sendMessage,
    loading: Boolean(value.loading),
    loadingMessage: value.loadingMessage ?? null,
    refreshMessages: value.refreshState,
  }), [
    value.messages,
    value.sendMessage,
    value.loading,
    value.loadingMessage,
    value.refreshState,
  ]);

  return (
    <ProjectMetaContext.Provider value={metaValue}>
      <projectContextInstance.Provider value={value}>
        <ProjectStateContext.Provider value={stateValue}>
          <ProjectChatContext.Provider value={chatValue}>
            {children}
          </ProjectChatContext.Provider>
        </ProjectStateContext.Provider>
      </projectContextInstance.Provider>
    </ProjectMetaContext.Provider>
  );
}
