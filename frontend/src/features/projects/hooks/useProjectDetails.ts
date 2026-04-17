import { useCallback, useMemo } from "react";
import { useProjectState } from "./useProjectState";
import { useChat } from "./useChat";
import { useProposal } from "./useProposal";
import { useProjectData } from "./useProjectData";
import { useChatHandlers } from "./useChatHandlers";
import { useProjectOperations } from "./useProjectOperations";
import type { ProjectState } from "../types/api-project";

import { useProjectLoading } from "./useProjectLoading";

// eslint-disable-next-line max-lines-per-function -- Aggregates multiple hooks into a single cohesive API.
export function useProjectDetails(projectId: string | undefined) {
  const projectData = useProjectData(projectId);
  const { selectedProject, setSelectedProject, textRequirements } = projectData;

  const stateHook = useProjectState(selectedProject?.id ?? null);
  const chatHook = useChat(selectedProject?.id ?? null);
  const { generateProposal, ...proposalHook } = useProposal();
  const sendMessage = useCallback(
    async (message: string, onStateUpdate?: (state: ProjectState) => void) => {
      return chatHook.sendMessage(message, (nextState) => {
        stateHook.setProjectState(nextState);
        onStateUpdate?.(nextState);
      });
    },
    // oxlint-disable-next-line exhaustive-deps -- chatHook and stateHook methods are stable references from custom hooks
    [chatHook.sendMessage, stateHook.setProjectState],
  );

  const operations = useProjectOperations({
    selectedProject,
    setSelectedProject,
    projectState: stateHook.projectState,
    files: projectData.files,
    setFiles: projectData.setFiles,
    textRequirements,
    analyzeDocuments: stateHook.analyzeDocuments,
    refreshState: stateHook.refreshState,
    generateProposal,
  });

  const { handleSendChatMessage } = useChatHandlers({
    chatInput: chatHook.chatInput,
    sendMessage,
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
      loading,
      loadingProject: projectData.loadingProject,
      loadingState: stateHook.loading,
      loadingChat: chatHook.loading,
      loadingProposal: proposalHook.loading,
      loadingMessage: chatHook.loadingMessage,
      activeReview: chatHook.activeReview,
      projectState: stateHook.projectState,
      messages: chatHook.messages,
      chatInput: chatHook.chatInput,
      setChatInput: chatHook.setChatInput,
      sendMessage,
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
      loading,
      stateHook.loading,
      chatHook.loading,
      proposalHook.loading,
      chatHook.loadingMessage,
      chatHook.activeReview,
      stateHook.projectState,
      chatHook.messages,
      chatHook.chatInput,
      chatHook.setChatInput,
      sendMessage,
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
