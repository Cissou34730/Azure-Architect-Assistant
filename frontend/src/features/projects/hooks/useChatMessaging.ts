import { useState } from "react";
import type { FailedMessage, UseChatMessagingProps } from "./chat-messaging-types";
import {
  useFetchMessages,
  useFetchOlderMessages,
  useMessageArchiver,
  useMessagesRef,
} from "./chat-messaging-fetch";
import { useRetrySendMessage, useSendMessage } from "./chat-messaging-send";

export type { FailedMessage } from "./chat-messaging-types";

export function useChatMessaging({
  projectId,
  messages,
  setMessages,
  setLoading,
  setLoadingMessage,
}: UseChatMessagingProps) {
  const [failedMessages, setFailedMessages] = useState<
    readonly FailedMessage[]
  >([]);
  const messagesRef = useMessagesRef(messages);
  useMessageArchiver({ projectId, messages, setMessages });

  const fetchMessages = useFetchMessages({
    projectId,
    messagesRef,
    setMessages,
  });
  const fetchOlderMessages = useFetchOlderMessages({ projectId, setMessages });
  const sendMessage = useSendMessage({
    projectId,
    setMessages,
    setLoading,
    setLoadingMessage,
    setFailedMessages,
    fetchMessages,
  });
  const retrySendMessage = useRetrySendMessage({
    failedMessages,
    setFailedMessages,
    sendMessage,
  });

  return {
    fetchMessages,
    fetchOlderMessages,
    sendMessage,
    failedMessages,
    retrySendMessage,
  };
}
