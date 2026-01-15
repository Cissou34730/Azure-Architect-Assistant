import { useState, useCallback } from "react";
import { agentApi } from "../../../services/agentService";
import { Message } from "../../../types/agent";
import { normalizeMessage } from "./utils";

export function useConversationHistory(selectedProjectId: string) {
  const [messages, setMessages] = useState<readonly Message[]>([]);

  const loadHistory = useCallback(async () => {
    if (selectedProjectId === "") {
      setMessages([]);
      return;
    }

    try {
      const messagesData = await agentApi.getHistory(selectedProjectId);
      const loadedMessages = messagesData.map(normalizeMessage);
      setMessages(loadedMessages);
    } catch (error) {
      console.error("Failed to load conversation history:", error);
      setMessages([]);
    }
  }, [selectedProjectId]);

  return { messages, setMessages, loadHistory };
}
