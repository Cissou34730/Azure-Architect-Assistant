import { useCallback } from "react";
import { chatApi } from "../../../services/chatService";
import { Message, ProjectState } from "../../../types/api";

interface UseChatMessagingProps {
  readonly projectId: string | null;
  readonly setMessages: (msgs: readonly Message[]) => void;
  readonly setLoading: (loading: boolean) => void;
  readonly setLoadingMessage: (msg: string) => void;
}

export function useChatMessaging({
  projectId,
  setMessages,
  setLoading,
  setLoadingMessage,
}: UseChatMessagingProps) {
  const fetchMessages = useCallback(async () => {
    if (projectId === null || projectId === "") {
      return;
    }

    try {
      const fetchedMessages = await chatApi.fetchMessages(projectId);
      setMessages(fetchedMessages);
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Fetch failed";
      console.error(`Error fetching messages: ${msg}`);
    }
  }, [projectId, setMessages]);

  const sendMessage = useCallback(
    async (message: string, onStateUpdate?: (state: ProjectState) => void) => {
      if (projectId === null || projectId === "" || message.trim() === "") {
        throw new Error("Invalid message or project");
      }

      setLoading(true);
      setLoadingMessage("Processing your question...");

      try {
        const response = await chatApi.sendMessage(projectId, message);

        if (onStateUpdate !== undefined) {
          onStateUpdate(response.projectState);
        }

        await fetchMessages();

        return response;
      } finally {
        setLoading(false);
        setLoadingMessage("");
      }
    },
    [projectId, fetchMessages, setLoading, setLoadingMessage]
  );

  return { fetchMessages, sendMessage };
}
