import { useProjectState } from "./useProjectState";
import { useChat } from "./useChat";
import { useProposal } from "./useProposal";
import { useToast } from "../../../hooks/useToast";
import { getTabs } from "../tabs";
import { useProjectTabNavigation } from "./useProjectTabNavigation";
import { useProjectData } from "./useProjectData";
import { useChatHandlers } from "./useChatHandlers";
import { useProjectOperations } from "./useProjectOperations";

export function useProjectDetails(projectId: string | undefined) {
  const { success, error: showError, warning } = useToast();
  const tabs = getTabs();
  const { activeTab, setActiveTab } = useProjectTabNavigation(projectId, tabs);

  const projectData = useProjectData(projectId, showError);
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
    success,
    showError,
    warning,
  });

  const { handleSendChatMessage } = useChatHandlers({
    chatInput: chatHook.chatInput,
    sendMessage: chatHook.sendMessage,
  });

  const loading =
    projectData.loadingProject ||
    stateHook.loading ||
    chatHook.loading ||
    proposalHook.loading;

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
  };
}
