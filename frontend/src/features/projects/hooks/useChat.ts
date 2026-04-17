/**
 * Custom hook for chat functionality
 */

import { useState, useEffect } from "react";
import type { Message } from "../../knowledge/types/api-kb";
import { useChatMessaging } from "./useChatMessaging";
import { archiveOldMessages } from "../utils/messageArchive";
import type { ActiveChatReview } from "../types/chat-review";

export const useChat = (projectId: string | null) => {
  const [messages, setMessages] = useState<readonly Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");
  const [activeReview, setActiveReview] = useState<ActiveChatReview | null>(null);

  const {
    fetchMessages,
    fetchOlderMessages,
    sendMessage,
    failedMessages,
    retrySendMessage,
  } = useChatMessaging({
    projectId,
    messages,
    setMessages,
    setLoading,
    setLoadingMessage,
    setActiveReview,
  });

  useEffect(() => {
    void fetchMessages();
  }, [fetchMessages]);

  // Apply message archiving when threshold reached
  useEffect(() => {
    if (projectId !== null && projectId !== "" && messages.length > 200) {
      const capped = archiveOldMessages(projectId, messages);
      if (capped !== messages) {
        setMessages(capped);
      }
    }
  }, [messages, projectId]);

  return {
    messages,
    chatInput,
    setChatInput,
    loading,
    loadingMessage,
    activeReview,
    sendMessage,
    refreshMessages: fetchMessages,
    fetchOlderMessages,
    failedMessages,
    retrySendMessage,
  };
};
