import { useMemo } from "react";
import { useProjectState } from "./useProjectState";
import { useChat } from "./useChat";
import { useProposal } from "./useProposal";
import { getTabs } from "../tabs";
import { useProjectTabNavigation } from "./useProjectTabNavigation";
import { useProjectData } from "./useProjectData";
import { useChatHandlers } from "./useChatHandlers";
import { useProjectOperations } from "./useProjectOperations";

import { useProjectLoading } from "./useProjectLoading";

// eslint-disable-next-line max-lines-per-function -- Aggregates multiple hooks into a single cohesive API.
export function useProjectDetails(projectId: string | undefined) {
  const tabs = getTabs();
  const { activeTab, setActiveTab } = useProjectTabNavigation(projectId, tabs);

  const projectData = useProjectData(projectId);
  const { selectedProject, setSelectedProject, textRequirements } = projectData;

  const stateHook = useProjectState(selectedProject?.id ?? null);
  const chatHook = useChat(selectedProject?.id ?? null);
  const { generateProposal, ...proposalHook } = useProposal();

  const operations = useProjectOperations({
    selectedProject,
    setSelectedProject,
    files: projectData.files,
    setFiles: projectData.setFiles,
    textRequirements,
    analyzeDocuments: stateHook.analyzeDocuments,
    refreshState: stateHook.refreshState,
    generateProposal,
    setActiveTab,
  });

  const { handleSendChatMessage } = useChatHandlers({
    chatInput: chatHook.chatInput,
    sendMessage: chatHook.sendMessage,
  });

  const loading = useProjectLoading({
    loadingProject: projectData.loadingProject,
    loadingState: stateHook.loading,
    loadingChat: chatHook.loading,
    loadingProposal: proposalHook.loading,
  });

  return useMemo(
    () => ({
      ...projectData,
      activeTab,
      setActiveTab,
      loading,
      loadingMessage: chatHook.loadingMessage,
      projectState: stateHook.projectState,
      messages: chatHook.messages,
      chatInput: chatHook.chatInput,
      setChatInput: chatHook.setChatInput,
      sendMessage: chatHook.sendMessage,
      fetchOlderMessages: chatHook.fetchOlderMessages,
      failedMessages: chatHook.failedMessages,
      retrySendMessage: chatHook.retrySendMessage,
      architectureProposal: proposalHook.architectureProposal,
      proposalStage: proposalHook.proposalStage,
      ...operations,
      handleSendChatMessage,
      refreshState: stateHook.refreshState,
      refreshMessages: chatHook.refreshMessages,
      analyzeDocuments: stateHook.analyzeDocuments,
    }),
    [
      projectData,
      activeTab,
      setActiveTab,
      loading,
      chatHook.loadingMessage,
      stateHook.projectState,
      chatHook.messages,
      chatHook.chatInput,
      chatHook.setChatInput,
      chatHook.sendMessage,
      chatHook.refreshMessages,
      chatHook.fetchOlderMessages,
      chatHook.failedMessages,
      chatHook.retrySendMessage,
      proposalHook.architectureProposal,
      proposalHook.proposalStage,
      operations,
      handleSendChatMessage,
      stateHook.refreshState,
      stateHook.analyzeDocuments,
    ],
  );
}
