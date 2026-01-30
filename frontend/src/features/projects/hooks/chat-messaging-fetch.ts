import { useCallback, useRef, useEffect } from "react";
import type { Dispatch, SetStateAction } from "react";
import { chatApi } from "../../../services/chatService";
import { Message } from "../../../types/api";
import {
  restoreLastBatchFromArchive,
  archiveOldMessages,
} from "../../../utils/messageArchive";
import { isFeatureEnabled } from "../../../config/featureFlags";
import {
  findLastNonOptimisticId,
  reconcileMessages,
} from "./chat-messaging-utils";

export function useMessagesRef(messages: readonly Message[]) {
  const messagesRef = useRef(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);
  return messagesRef;
}

export function useMessageArchiver({
  projectId,
  messages,
  setMessages,
}: {
  projectId: string | null;
  messages: readonly Message[];
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
}) {
  useEffect(() => {
    if (projectId !== null && projectId !== "" && messages.length > 200) {
      const capped = archiveOldMessages(projectId, messages);
      if (capped.length !== messages.length) {
        setMessages(capped);
      }
    }
  }, [messages, projectId, setMessages]);
}

export function useFetchMessages({
  projectId,
  messagesRef,
  setMessages,
}: {
  projectId: string | null;
  messagesRef: { current: readonly Message[] };
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
}) {
  return useCallback(async () => {
    if (projectId === null || projectId === "") {
      return;
    }

    const useIncremental = isFeatureEnabled("enableIncrementalChat");
    const currentMessages = messagesRef.current;
    const sinceId = useIncremental
      ? findLastNonOptimisticId(currentMessages)
      : undefined;

    try {
      const fetchedMessages = await chatApi.fetchMessages(projectId, sinceId);

      if (useIncremental && sinceId !== undefined && sinceId !== "") {
        if (fetchedMessages.length > 0) {
          setMessages((prev) => {
            const existingIds = new Set(prev.map((m) => m.id));
            const trulyNew = fetchedMessages.filter(
              (m) => !existingIds.has(m.id),
            );
            return [
              ...prev.filter((m) => !m.id.startsWith("opt-")),
              ...trulyNew,
            ];
          });
        }
        return;
      }

      setMessages((previousMessages) =>
        reconcileMessages(previousMessages, fetchedMessages),
      );
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Fetch failed";
      console.error(`Error fetching messages: ${msg}`);
    }
  }, [projectId, setMessages, messagesRef]);
}

export function useFetchOlderMessages({
  projectId,
  setMessages,
}: {
  projectId: string | null;
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
}) {
  return useCallback(
    async (beforeId: string) => {
      if (projectId === null || projectId === "") {
        return [];
      }

      const { restored } = restoreLastBatchFromArchive(projectId);
      if (restored.length > 0) {
        setMessages((prev) => [...restored, ...prev]);
        return restored;
      }

      try {
        const olderMessages = await chatApi.fetchMessagesBefore(
          projectId,
          beforeId,
        );
        if (olderMessages.length > 0) {
          setMessages((previousMessages) => {
            const reconciled = reconcileMessages(
              previousMessages,
              olderMessages,
            );
            const existingIds = new Set(previousMessages.map((m) => m.id));
            const trulyNewOlder = reconciled.filter(
              (m) => !existingIds.has(m.id),
            );
            return [...trulyNewOlder, ...previousMessages];
          });
        }
        return olderMessages;
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Fetch failed";
        console.error(`Error fetching older messages: ${msg}`);
        return [];
      }
    },
    [projectId, setMessages],
  );
}
