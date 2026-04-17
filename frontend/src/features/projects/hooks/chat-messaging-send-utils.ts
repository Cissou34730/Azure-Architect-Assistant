/* eslint-disable max-lines -- SSE messaging utilities; each helper is minimal but the full send-message flow requires these lines */
import type { Dispatch, SetStateAction } from "react";
import { chatApi } from "../api/chatService";
import type {
  SendMessageResponse,
  Message,
} from "../../knowledge/types/api-kb";
import type { StreamEventMap } from "../api/chatService";
import { isJsonValue, type JsonValue } from "../../../shared/lib/json";
import type { ProjectState } from "../types/api-project";
import { isFeatureEnabled } from "../../../shared/config/featureFlags";
import type { FailedMessage } from "./chat-messaging-types";
import type { ActiveChatReview } from "../types/chat-review";
import {
  appendLegacyToolTrace,
  appendReviewText,
  appendStageEvent,
  appendToolTrace,
  completeActiveChatReview,
  completeToolTrace,
  createActiveChatReview,
  setPendingChangeSignal,
} from "./chat-review-stream-state";

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

// eslint-disable-next-line max-lines-per-function -- Stream review handlers are kept together because they model one event-to-state adapter.
function createReviewHandlers({
  setActiveReview,
  assistantId,
}: {
  setActiveReview: Dispatch<SetStateAction<ActiveChatReview | null>>;
  assistantId: string;
}) {
  return {
    handleMessageStart() {
      setActiveReview(createActiveChatReview(assistantId));
    },
    handleText(textFragment: string) {
      setActiveReview((previousReview) =>
        appendReviewText(previousReview, assistantId, textFragment),
      );
    },
    handleStage(stage: string, confidence: number) {
      setActiveReview((previousReview) =>
        appendStageEvent({
          reviewState: previousReview,
          assistantMessageId: assistantId,
          stage,
          confidence,
        }),
      );
    },
    handleToolStart(toolName: string, toolInput: JsonValue | undefined) {
      setActiveReview((previousReview) =>
        appendLegacyToolTrace({
          reviewState: previousReview,
          assistantMessageId: assistantId,
          toolName,
          toolInput,
        }),
      );
    },
    handleToolCall(toolName: string, argsPreview: string) {
      setActiveReview((previousReview) =>
        appendToolTrace({
          reviewState: previousReview,
          assistantMessageId: assistantId,
          toolName,
          argsPreview,
        }),
      );
    },
    handleToolResult({
      toolName,
      status,
      resultPreview,
      citations,
    }: {
      toolName: string;
      status?: string;
      resultPreview: string;
      citations: readonly string[];
    }) {
      setActiveReview((previousReview) =>
        completeToolTrace({
          reviewState: previousReview,
          assistantMessageId: assistantId,
          toolName,
          resultPreview,
          citations,
          status,
        }),
      );
    },
    handlePendingChange(changeSetId: string, summary: string, patchCount: number) {
      setActiveReview((previousReview) =>
        setPendingChangeSignal(previousReview, assistantId, {
          changeSetId,
          summary,
          patchCount,
        }),
      );
    },
    handleFinal(answer: string, workflowResult: SendMessageResponse["workflowResult"]) {
      setActiveReview((previousReview) =>
        completeActiveChatReview({
          reviewState: previousReview,
          assistantMessageId: assistantId,
          answerPreview: answer,
          workflowResult,
        }),
      );
    },
  };
}

// eslint-disable-next-line max-lines-per-function -- The callback table mirrors the SSE contract and is easier to audit when kept contiguous.
function buildStreamCallbacks({
  setMessages,
  setActiveReview,
  projectId,
  assistantId,
}: {
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  setActiveReview: Dispatch<SetStateAction<ActiveChatReview | null>>;
  projectId: string;
  assistantId: string;
}) {
  const reviewHandlers = createReviewHandlers({ setActiveReview, assistantId });
  const upsert = (update: (m: Message) => Message) =>
    { upsertStreamingAssistant({ setMessages, projectId, assistantId, update }); };
  return {
    onMessageStart: () => {
      upsert((currentMessage) => currentMessage);
      reviewHandlers.handleMessageStart();
    },
    onToken: ({ text }: StreamEventMap["token"]) => {
      upsert((c) => ({ ...c, content: `${c.content}${text}`, timestamp: new Date().toISOString() }));
      reviewHandlers.handleText(text);
    },
    onText: ({ delta }: StreamEventMap["text"]) => {
      upsert((currentMessage) => ({
        ...currentMessage,
        content: `${currentMessage.content}${delta}`,
        timestamp: new Date().toISOString(),
      }));
      reviewHandlers.handleText(delta);
    },
    onStage: ({ stage, confidence }: StreamEventMap["stage"]) => {
      reviewHandlers.handleStage(stage, confidence);
    },
    onToolStart: ({ tool, tool_input: toolInput }: StreamEventMap["tool_start"]) => {
      upsert((c) => ({ ...c, toolActivity: [...(c.toolActivity ?? []), `Running ${tool}`] }));
      reviewHandlers.handleToolStart(
        tool,
        isJsonValue(toolInput) ? toolInput : undefined,
      );
    },
    onToolCall: ({ tool, argsPreview }: StreamEventMap["tool_call"]) => {
      reviewHandlers.handleToolCall(tool, argsPreview);
    },
    onToolResult: ({ tool, status, resultPreview, citations, content }: StreamEventMap["tool_result"]) => {
      const label = status === "error" ? "failed" : "completed";
      upsert((c) => ({ ...c, toolActivity: [...(c.toolActivity ?? []), `${tool} ${label}`] }));
      reviewHandlers.handleToolResult({
        toolName: tool,
        status,
        resultPreview: resultPreview ?? content ?? "",
        citations: citations ?? [],
      });
    },
    onPendingChange: ({ changeSetId, summary, patchCount }: StreamEventMap["pending_change"]) => {
      reviewHandlers.handlePendingChange(changeSetId, summary, patchCount);
    },
    onFinal: ({ answer, workflow_result: workflowResult }: StreamEventMap["final"]) => {
      upsert((c) => ({ ...c, content: answer }));
      reviewHandlers.handleFinal(answer, workflowResult);
    },
  };
}

async function sendMessageRequest({
  projectId,
  message,
  optimisticId,
  onStateUpdate,
  setMessages,
  setActiveReview,
  fetchMessages,
}: {
  projectId: string;
  message: string;
  optimisticId: string;
  onStateUpdate?: (state: ProjectState) => void;
  setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  setActiveReview: Dispatch<SetStateAction<ActiveChatReview | null>>;
  fetchMessages: () => Promise<void>;
}): Promise<SendMessageResponse> {
  const assistantId = `assistant-${optimisticId}`;
  const callbacks = buildStreamCallbacks({
    setMessages,
    setActiveReview,
    projectId,
    assistantId,
  });
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
  readonly setActiveReview: Dispatch<SetStateAction<ActiveChatReview | null>>;
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
  setActiveReview,
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
      setActiveReview,
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

