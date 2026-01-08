/**
 * Custom hook for chat functionality
 */

import { useState, useCallback, useEffect } from "react";
import { Message, chatApi, ProjectState } from "../../../services/apiService";

export const useChat = (projectId: string | null) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");

  const fetchMessages = useCallback(async () => {
    if (!projectId) return;

    try {
      const fetchedMessages = await chatApi.fetchMessages(projectId);
      setMessages(fetchedMessages);
    } catch (error) {
      console.error("Error fetching messages:", error);
    }
  }, [projectId]);

  const sendMessage = useCallback(
    async (message: string, onStateUpdate?: (state: ProjectState) => void) => {
      if (!projectId || !message.trim()) {
        throw new Error("Invalid message or project");
      }

      setLoading(true);
      setLoadingMessage("Processing your question...");

      try {
        const response = await chatApi.sendMessage(projectId, message);

        // Update project state if callback provided
        if (onStateUpdate && response.projectState) {
          onStateUpdate(response.projectState);
        }

        // Refresh messages to get the complete conversation
        await fetchMessages();

        return response;
      } finally {
        setLoading(false);
        setLoadingMessage("");
      }
    },
    [projectId, fetchMessages],
  );

  useEffect(() => {
    void fetchMessages();
  }, [fetchMessages]);

  return {
    messages,
    chatInput,
    setChatInput,
    loading,
    loadingMessage,
    sendMessage,
    refreshMessages: fetchMessages,
  };
};
