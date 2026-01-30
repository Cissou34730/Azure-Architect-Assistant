/**
 * Custom hook for chat functionality
 */

import { useState, useEffect } from "react";
import { Message } from "../../../types/api";
import { useChatMessaging } from "./useChatMessaging";
import { archiveOldMessages } from "../../../utils/messageArchive";

export const useChat = (projectId: string | null) => {
  const [messages, setMessages] = useState<readonly Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");

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
    sendMessage,
    refreshMessages: fetchMessages,
    fetchOlderMessages,
    failedMessages,
    retrySendMessage,
  };
};
