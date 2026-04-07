// oxlint-disable exhaustive-deps -- inline onProjectStateUpdate prop wrap; stability is caller's responsibility
import { useEffect, type Dispatch, type SetStateAction } from "react";
import type { ProjectState } from "../../types/agent";
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
    // oxlint-disable-next-line exhaustive-deps -- inline function wraps prop to allow undefined check; prop stability is caller's responsibility
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

