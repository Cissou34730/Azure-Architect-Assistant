import { useProjectState } from "./useProjectState";
import { useChat } from "./useChat";
import { useProposal } from "./useProposal";
import { getTabs } from "../tabs";
import { useProjectTabNavigation } from "./useProjectTabNavigation";
import { useProjectData } from "./useProjectData";
import { useChatHandlers } from "./useChatHandlers";
import { useProjectOperations } from "./useProjectOperations";

import { useProjectLoading } from "./useProjectLoading";

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

  return {
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
    architectureProposal: proposalHook.architectureProposal,
    proposalStage: proposalHook.proposalStage,
    ...operations,
    handleSendChatMessage,
    refreshState: stateHook.refreshState,
    analyzeDocuments: stateHook.analyzeDocuments,
  };
}
