/* eslint-disable max-lines -- SSE messaging utilities; each helper is minimal but the full send-message flow requires these lines */
import type { Dispatch, SetStateAction } from "react";
import { chatApi } from "../api/chatService";
import type {
  SendMessageResponse,
  Message,
} from "../../knowledge/types/api-kb";
import type { ProjectState } from "../types/api-project";
import { isFeatureEnabled } from "../../../shared/config/featureFlags";
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

function createStreamingAssistantMessage(
  projectId: string,
  assistantId: string,
): Message {
  return {
    id: assistantId,
    projectId,
    role: "assistant",
    content: "",
    timestamp: new Date().toISOString(),
    streamingState: "streaming",
    toolActivity: [],
  };
}

function upsertStreamingAssistant({
  setMessages,
  projectId,
  assistantId,
  update,
}: {
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  projectId: string;
  assistantId: string;
  update: (message: Message) => Message;
}) {
  setMessages((prev) => {
    const index = prev.findIndex((message) => message.id === assistantId);
    if (index === -1) {
      return [...prev, update(createStreamingAssistantMessage(projectId, assistantId))];
    }
    const next = [...prev];
    next[index] = update(next[index]);
    return next;
  });
}

function removeStreamingAssistant(
  setMessages: Dispatch<SetStateAction<readonly Message[]>>,
  assistantId: string,
) {
  setMessages((prev) => prev.filter((message) => message.id !== assistantId));
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

function buildStreamCallbacks({
  setMessages,
  projectId,
  assistantId,
}: {
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  projectId: string;
  assistantId: string;
}) {
  const upsert = (update: (m: Message) => Message) =>
    { upsertStreamingAssistant({ setMessages, projectId, assistantId, update }); };
  return {
    onMessageStart: () => { upsert((c) => c); },
    onToken: ({ text }: { text: string }) => {
      upsert((c) => ({ ...c, content: `${c.content}${text}`, timestamp: new Date().toISOString() }));
    },
    onToolStart: ({ tool }: { tool: string }) => {
      upsert((c) => ({ ...c, toolActivity: [...(c.toolActivity ?? []), `Running ${tool}`] }));
    },
    onToolResult: ({ tool, status }: { tool: string; status?: string }) => {
      const label = status === "error" ? "failed" : "completed";
      upsert((c) => ({ ...c, toolActivity: [...(c.toolActivity ?? []), `${tool} ${label}`] }));
    },
    onFinal: ({ answer }: { answer: string }) => {
      upsert((c) => ({ ...c, content: answer }));
    },
  };
}

async function sendMessageRequest({
  projectId,
  message,
  optimisticId,
  onStateUpdate,
  setMessages,
  fetchMessages,
}: {
  projectId: string;
  message: string;
  optimisticId: string;
  onStateUpdate?: (state: ProjectState) => void;
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  fetchMessages: () => Promise<void>;
}): Promise<SendMessageResponse> {
  const assistantId = `assistant-${optimisticId}`;
  const callbacks = buildStreamCallbacks({ setMessages, projectId, assistantId });
  const response = await chatApi.sendMessage(projectId, message, { idempotencyKey: optimisticId, callbacks });
  if (onStateUpdate !== undefined) onStateUpdate(response.projectState);
  await fetchMessages();
  removeStreamingAssistant(setMessages, assistantId);
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
      setMessages,
      fetchMessages,
    });

    // Clear stale failed banners once we have a successful round-trip.
    setFailedMessages([]);
    return response;
  } catch (error) {
    const errorMessage =
      error instanceof Error ? error.message : "Failed to send";
    removeStreamingAssistant(setMessages, `assistant-${optimisticId}`);
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

