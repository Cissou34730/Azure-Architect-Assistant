import { useCallback } from "react";
import type { Dispatch, SetStateAction } from "react";
import type { SendMessageResponse } from "../../knowledge/types/api-kb";
import type { ProjectState } from "../types/api-project";
import type { FailedMessage } from "./chat-messaging-types";
import {
  handleSendMessage,
  type HandleSendMessageArgs,
} from "./chat-messaging-send-utils";

type UseSendMessageArgs = Omit<
  HandleSendMessageArgs,
  "message" | "onStateUpdate"
>;

export function useSendMessage({
  projectId,
  setMessages,
  setLoading,
  setLoadingMessage,
  setFailedMessages,
  setActiveReview,
  fetchMessages,
}: UseSendMessageArgs) {
  return useCallback(
    async (message: string, onStateUpdate?: (state: ProjectState) => void) => {
      return handleSendMessage({
        projectId,
        message,
        onStateUpdate,
        setMessages,
        setLoading,
        setLoadingMessage,
        setFailedMessages,
        setActiveReview,
        fetchMessages,
      });
    },
    [
      projectId,
      fetchMessages,
      setLoading,
      setLoadingMessage,
      setMessages,
      setFailedMessages,
      setActiveReview,
    ],
  );
}

interface UseRetrySendMessageArgs {
  readonly failedMessages: readonly FailedMessage[];
  readonly setFailedMessages: Dispatch<SetStateAction<readonly FailedMessage[]>>;
  readonly sendMessage: (
    message: string,
    onStateUpdate?: (state: ProjectState) => void,
  ) => Promise<SendMessageResponse>;
}

export function useRetrySendMessage({
  failedMessages,
  setFailedMessages,
  sendMessage,
}: UseRetrySendMessageArgs) {
  return useCallback(
    async (failedId: string) => {
      const failed = failedMessages.find((m) => m.id === failedId);
      if (failed === undefined) return;

      setFailedMessages((prev) => prev.filter((m) => m.id !== failedId));

      try {
        await sendMessage(failed.content);
      } catch (error) {
        const msg = error instanceof Error ? error.message : "Retry failed";
        setFailedMessages((prev) => [
          ...prev,
          { id: failedId, content: failed.content, error: msg },
        ]);
      }
    },
    [failedMessages, sendMessage, setFailedMessages],
  );
}
