import type { Dispatch, SetStateAction } from "react";
import { chatApi } from "../../../services/chatService";
import { Message, ProjectState, SendMessageResponse } from "../../../types/api";
import { isFeatureEnabled } from "../../../config/featureFlags";
import type { FailedMessage } from "./chat-messaging-types";

function ensureValidSend(projectId: string | null, message: string): string {
  if (projectId === null || projectId === "" || message.trim() === "") {
    throw new Error("Invalid message or project");
  }
  return projectId;
}

function createOptimisticMessage(
  projectId: string,
  content: string,
  optimisticId: string,
): Message {
  return {
    id: optimisticId,
    projectId,
    role: "user",
    content,
    timestamp: new Date().toISOString(),
  };
}

function applyOptimisticMessage({
  projectId,
  message,
  setMessages,
}: {
  projectId: string;
  message: string;
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
}): { optimisticId: string; useOptimistic: boolean } {
  const useOptimistic = isFeatureEnabled("enableOptimisticChat");
  const optimisticId = `opt-${Date.now()}`;

  if (useOptimistic) {
    const optimisticMessage = createOptimisticMessage(
      projectId,
      message,
      optimisticId,
    );
    setMessages((prev) => [...prev, optimisticMessage]);
  }

  return { optimisticId, useOptimistic };
}

async function sendMessageRequest({
  projectId,
  message,
  optimisticId,
  onStateUpdate,
  fetchMessages,
}: {
  projectId: string;
  message: string;
  optimisticId: string;
  onStateUpdate?: (state: ProjectState) => void;
  fetchMessages: () => Promise<void>;
}): Promise<SendMessageResponse> {
  const response = await chatApi.sendMessage(projectId, message, {
    idempotencyKey: optimisticId,
  });

  if (onStateUpdate !== undefined) {
    onStateUpdate(response.projectState);
  }

  await fetchMessages();
  return response;
}

function recordSendFailure({
  errorMessage,
  useOptimistic,
  optimisticId,
  message,
  setMessages,
  setFailedMessages,
}: {
  errorMessage: string;
  useOptimistic: boolean;
  optimisticId: string;
  message: string;
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  setFailedMessages: Dispatch<SetStateAction<readonly FailedMessage[]>>;
}) {
  if (useOptimistic) {
    setMessages((prev) => prev.filter((m) => m.id !== optimisticId));
  }

  setFailedMessages((prev) => [
    ...prev,
    { id: optimisticId, content: message, error: errorMessage },
  ]);
}

export interface HandleSendMessageArgs {
  readonly projectId: string | null;
  readonly message: string;
  readonly onStateUpdate?: (state: ProjectState) => void;
  readonly setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  readonly setLoading: (loading: boolean) => void;
  readonly setLoadingMessage: (msg: string) => void;
  readonly setFailedMessages: Dispatch<SetStateAction<readonly FailedMessage[]>>;
  readonly fetchMessages: () => Promise<void>;
}

export async function handleSendMessage({
  projectId,
  message,
  onStateUpdate,
  setMessages,
  setLoading,
  setLoadingMessage,
  setFailedMessages,
  fetchMessages,
}: HandleSendMessageArgs): Promise<SendMessageResponse> {
  const validProjectId = ensureValidSend(projectId, message);
  const { optimisticId, useOptimistic } = applyOptimisticMessage({
    projectId: validProjectId,
    message,
    setMessages,
  });

  setLoading(true);
  setLoadingMessage("Processing your question...");

  try {
    const response = await sendMessageRequest({
      projectId: validProjectId,
      message,
      optimisticId,
      onStateUpdate,
      fetchMessages,
    });

    // Clear stale failed banners once we have a successful round-trip.
    setFailedMessages([]);
    return response;
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Failed to send";
    recordSendFailure({
      errorMessage,
      useOptimistic,
      optimisticId,
      message,
      setMessages,
      setFailedMessages,
    });
    throw error;
  } finally {
    setLoading(false);
    setLoadingMessage("");
  }
}
