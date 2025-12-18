import { useState, useEffect } from "react";
import type { Message, AgentResponse } from "../../../types/agent";

const API_BASE = `${import.meta.env.BACKEND_URL || "http://localhost:8000"}/api`;

interface UseAgentChatProps {
  selectedProjectId: string;
  onProjectStateUpdate?: (state: any) => void;
}

export function useAgentChat({
  selectedProjectId,
  onProjectStateUpdate,
}: UseAgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const loadConversationHistory = async () => {
    if (!selectedProjectId) {
      setMessages([]);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE}/agent/projects/${selectedProjectId}/history`
      );
      const data = await response.json();

      const loadedMessages: Message[] = data.messages.map((msg: any) => ({
        role: msg.role as "user" | "assistant",
        content: msg.content,
        reasoningSteps: undefined,
      }));

      setMessages(loadedMessages);
    } catch (error) {
      console.error("Failed to load conversation history:", error);
      setMessages([]);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setIsLoading(true);

    try {
      const endpoint = selectedProjectId
        ? `${API_BASE}/agent/projects/${selectedProjectId}/chat`
        : `${API_BASE}/agent/chat`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: currentInput }),
      });

      const data: AgentResponse = await response.json();

      const assistantMessage: Message = {
        role: "assistant",
        content: data.answer,
        reasoningSteps: data.reasoning_steps,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (data.project_state && onProjectStateUpdate) {
        onProjectStateUpdate(data.project_state);
      }
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: `Error: ${
          error instanceof Error
            ? error.message
            : "Failed to get response from agent"
        }`,
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  useEffect(() => {
    void loadConversationHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProjectId]);

  return {
    messages,
    input,
    isLoading,
    setInput,
    sendMessage,
    clearChat,
  };
}
