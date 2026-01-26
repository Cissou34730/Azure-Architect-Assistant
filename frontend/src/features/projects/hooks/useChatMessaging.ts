import type { Dispatch, SetStateAction } from "react";
import { useCallback } from "react";
import { chatApi } from "../../../services/chatService";
import { Message, ProjectState } from "../../../types/api";

interface UseChatMessagingProps {
  readonly projectId: string | null;
  readonly setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  readonly setLoading: (loading: boolean) => void;
  readonly setLoadingMessage: (msg: string) => void;
}

function serializeKbSources(message: Message): string {
  if (message.kbSources === undefined || message.kbSources.length === 0) {
    return "";
  }

  return message.kbSources
    .map((source) => `${source.url}|${source.title ?? ""}`)
    .join(";;");
}

function canReuseMessage(prevMessage: Message, nextMessage: Message): boolean {
  if (prevMessage === nextMessage) {
    return true;
  }

  if (prevMessage.id !== nextMessage.id) {
    return false;
  }

  if (prevMessage.role !== nextMessage.role) {
    return false;
  }

  if (prevMessage.content !== nextMessage.content) {
    return false;
  }

  if (prevMessage.timestamp !== nextMessage.timestamp) {
    return false;
  }

  return serializeKbSources(prevMessage) === serializeKbSources(nextMessage);
}

function reconcileMessages(
  previousMessages: readonly Message[],
  fetchedMessages: readonly Message[]
): readonly Message[] {
  if (previousMessages.length === 0) {
    return fetchedMessages;
  }

  const previousById = new Map(previousMessages.map((message) => [message.id, message]));
  let reusedAny = false;

  const reconciled = fetchedMessages.map((nextMessage) => {
    const prevMessage = previousById.get(nextMessage.id);
    if (prevMessage !== undefined && canReuseMessage(prevMessage, nextMessage)) {
      reusedAny = true;
      return prevMessage;
    }
    return nextMessage;
  });

  return reusedAny ? reconciled : fetchedMessages;
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
      setMessages((previousMessages) => reconcileMessages(previousMessages, fetchedMessages));
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
