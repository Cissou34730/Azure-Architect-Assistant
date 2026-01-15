/**
 * Custom hook for chat functionality
 */

import { useState, useEffect } from "react";
import { Message } from "../../../types/api";
import { useChatMessaging } from "./useChatMessaging";

export const useChat = (projectId: string | null) => {
  const [messages, setMessages] = useState<readonly Message[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState("");

  const { fetchMessages, sendMessage } = useChatMessaging({
    projectId,
    setMessages,
    setLoading,
    setLoadingMessage,
  });

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
