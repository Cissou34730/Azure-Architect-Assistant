import {
  useRef,
  useEffect,
  useMemo,
  useState,
  useCallback,
} from "react";
import type { VirtuosoHandle } from "react-virtuoso";
import { useChatInput } from "./useChatInput";
import type { Message } from "../../../../types/api";
import { useRenderCount } from "../../../../hooks/useRenderCount";
import type { FailedMessage } from "../../hooks/useChatMessaging";
import { ChatListHeader } from "./ChatListHeader";
import { ChatListFooter } from "./ChatListFooter";
import { ChatInputForm } from "./ChatInputForm";
import { ChatMessagesList } from "./ChatMessagesList";

interface ChatPanelProps {
  messages: readonly Message[];
  onSendMessage: (content: string) => Promise<void>;
  loading?: boolean;
  onLoadOlderMessages?: (beforeId: string) => Promise<readonly Message[]>;
  failedMessages?: readonly FailedMessage[];
  onRetryMessage?: (id: string) => Promise<void>;
}

export function ChatPanel({
  messages,
  onSendMessage,
  loading = false,
  onLoadOlderMessages,
  failedMessages = [],
  onRetryMessage,
}: ChatPanelProps) {
  useRenderCount("ChatPanel");
  const {
    input,
    sending,
    handleSubmit,
    handleKeyDown,
    handleInputChange,
  } = useChatInput(onSendMessage);

  const virtuosoRef = useRef<VirtuosoHandle>(null);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [hasMoreOlder, setHasMoreOlder] = useState(true);

  const handleLoadOlder = useCallback(async () => {
    if (
      onLoadOlderMessages === undefined ||
      messages.length === 0 ||
      loadingOlder
    ) {
      return;
    }

    setLoadingOlder(true);
    try {
      const oldestId = messages[0].id;
      const older = await onLoadOlderMessages(oldestId);
      if (older.length < 50) {
        setHasMoreOlder(false);
      }
    } finally {
      setLoadingOlder(false);
    }
  }, [onLoadOlderMessages, messages, loadingOlder]);

  useEffect(() => {
    if (messages.length > 0 && (sending || loading)) {
      virtuosoRef.current?.scrollToIndex({
        index: messages.length - 1,
        behavior: "smooth",
        align: "end",
      });
    }
  }, [messages.length, loading, sending]);

  const isInputDisabled = input.trim() === "" || sending;
  const canLoadOlder =
    onLoadOlderMessages !== undefined && hasMoreOlder;

  const headerContent = useMemo(
    () => (
      <ChatListHeader
        canLoadOlder={canLoadOlder}
        loadingOlder={loadingOlder}
        onLoadOlder={handleLoadOlder}
      />
    ),
    [canLoadOlder, loadingOlder, handleLoadOlder],
  );

  const footerContent = useMemo(
    () => (
      <ChatListFooter
        loading={loading}
        sending={sending}
        failedMessages={failedMessages}
        onRetryMessage={onRetryMessage}
      />
    ),
    [loading, sending, failedMessages, onRetryMessage],
  );

  return (
    <div className="flex flex-col h-full bg-card">
      <div className="flex-1 min-h-0">
        <ChatMessagesList
          messages={messages}
          virtuosoRef={virtuosoRef}
          headerContent={headerContent}
          footerContent={footerContent}
        />
      </div>

      <ChatInputForm
        input={input}
        sending={sending}
        isInputDisabled={isInputDisabled}
        onSubmit={handleSubmit}
        onInputChange={handleInputChange}
        onKeyDown={handleKeyDown}
      />
    </div>
  );
}



