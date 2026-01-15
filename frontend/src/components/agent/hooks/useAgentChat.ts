import { useEffect, type Dispatch, type SetStateAction } from "react";
import type { ProjectState } from "../../../types/agent";
import { useConversationHistory } from "./useConversationHistory";
import { useChatMessaging } from "./useChatMessaging";

interface UseAgentChatProps {
  readonly selectedProjectId: string;
  readonly onProjectStateUpdate?: Dispatch<SetStateAction<ProjectState | null>>;
}

export function useAgentChat({
  selectedProjectId,
  onProjectStateUpdate,
}: UseAgentChatProps) {
  const { messages, setMessages, loadHistory } =
    useConversationHistory(selectedProjectId);

  const { input, setInput, isLoading, sendMessage } = useChatMessaging({
    selectedProjectId,
    setMessages,
    onProjectStateUpdate: (state) => {
      if (onProjectStateUpdate !== undefined) {
        onProjectStateUpdate(state);
      }
    },
  });

  const clearChat = () => {
    setMessages([]);
  };

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  return {
    messages,
    input,
    isLoading,
    setInput,
    sendMessage,
    clearChat,
  };
}
