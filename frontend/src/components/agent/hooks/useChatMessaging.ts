import { useState, Dispatch, SetStateAction } from "react";
import { agentApi } from "../../../services/agentService";
import { Message, ProjectState } from "../../../types/agent";

interface UseChatMessagingProps {
  readonly selectedProjectId: string;
  readonly setMessages: Dispatch<SetStateAction<readonly Message[]>>;
  readonly onProjectStateUpdate?: (state: ProjectState) => void;
}

/* eslint-disable max-lines-per-function */
/**
 * Hook for managing chat messaging with the agent.
 * Kept in one block to maintain logical cohesion of the messaging flow.
 */
export function useChatMessaging({
  selectedProjectId,
  setMessages,
  onProjectStateUpdate,
}: UseChatMessagingProps) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (input.trim() === "" || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input,
    };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsLoading(true);

    try {
      const response =
        selectedProjectId !== ""
          ? await agentApi.projectChat(selectedProjectId, currentInput)
          : await agentApi.chat(currentInput);

      if (response.success) {
        const assistantMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          reasoningSteps: [...response.reasoningSteps],
        };
        setMessages((prev) => [...prev, assistantMessage]);

        if (
          response.projectState !== undefined &&
          onProjectStateUpdate !== undefined
        ) {
          onProjectStateUpdate(response.projectState);
        }
      } else {
        const errorContent = response.error ?? "Unknown error occurred";
        const errorMessage: Message = {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Error: ${errorContent}`,
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: `Error: ${
          error instanceof Error ? error.message : "Failed to get response"
        }`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return { input, setInput, isLoading, sendMessage };
}
