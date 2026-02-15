import {
  useRef,
  useEffect,
  useMemo,
  useState,
  useCallback,
  type FormEvent,
  type ChangeEvent,
  type KeyboardEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { Send, Loader2, AlertCircle, RotateCcw } from "lucide-react";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import { messageBubbleComp as MessageBubble } from "./MessageBubble";
import { ChatEmptyStateComp as ChatEmptyState } from "./ChatEmptyState";
import { useChatInput } from "./useChatInput";
import type { Message } from "../../../../types/api";
import { useRenderCount } from "../../../../hooks/useRenderCount";
import type { FailedMessage } from "../../hooks/useChatMessaging";

interface ChatPanelProps {
  messages: readonly Message[];
  onSendMessage: (content: string) => Promise<void>;
  loading?: boolean;
  onLoadOlderMessages?: (beforeId: string) => Promise<readonly Message[]>;
  failedMessages?: readonly FailedMessage[];
  onRetryMessage?: (id: string) => Promise<void>;
}

interface ChatHeaderProps {
  readonly canLoadOlder: boolean;
  readonly loadingOlder: boolean;
  readonly onLoadOlder: () => void;
}

function ChatListHeader({ canLoadOlder, loadingOlder, onLoadOlder }: ChatHeaderProps) {
  if (!canLoadOlder) return null;

  return (
    <div className="p-4 text-center">
      <button
        type="button"
        onClick={onLoadOlder}
        disabled={loadingOlder}
        className="text-sm font-medium text-brand hover:text-brand-strong disabled:text-dim disabled:cursor-not-allowed flex items-center justify-center gap-2 mx-auto"
      >
        {loadingOlder ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading older messages...
          </>
        ) : (
          "Load older messages"
        )}
      </button>
    </div>
  );
}

interface ChatFooterProps {
  readonly loading: boolean;
  readonly sending: boolean;
  readonly failedMessages: readonly FailedMessage[];
  readonly onRetryMessage?: (id: string) => Promise<void>;
}

function ChatListFooter({
  loading,
  sending,
  failedMessages,
  onRetryMessage,
}: ChatFooterProps) {
  if (!loading && !sending && failedMessages.length === 0) return null;

  return (
    <div className="px-6 py-4 space-y-4">
      {(loading || sending) && (
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-full bg-brand-soft flex items-center justify-center shrink-0">
            <Loader2 className="h-5 w-5 text-brand animate-spin" />
          </div>
          <div className="bg-surface rounded-lg px-4 py-3 text-sm text-secondary">
            Thinking...
          </div>
        </div>
      )}

      {failedMessages.map((failed) => (
        <div
          key={failed.id}
          className="flex items-start gap-3 p-4 bg-danger-soft border border-danger-line rounded-lg text-danger-strong"
        >
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium">Message failed to send</p>
            <p className="text-sm opacity-90 line-clamp-1">{failed.content}</p>
            <p className="text-xs mt-1 text-danger">{failed.error}</p>
            <button
              type="button"
              onClick={() => {
                void onRetryMessage?.(failed.id);
              }}
              className="mt-2 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-danger-strong hover:text-danger-strong transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Retry Send
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

interface ChatInputProps {
  readonly input: string;
  readonly sending: boolean;
  readonly isInputDisabled: boolean;
  readonly onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  readonly onInputChange: (event: ChangeEvent<HTMLInputElement>) => void;
  readonly onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
}

function ChatInputForm({
  input,
  sending,
  isInputDisabled,
  onSubmit,
  onInputChange,
  onKeyDown,
}: ChatInputProps) {
  return (
    <div className="border-t border-border p-4 bg-card">
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={onInputChange}
          onKeyDown={onKeyDown}
          placeholder="Type your message... (Cmd+Enter to send)"
          disabled={sending}
          className="flex-1 px-4 py-3 border border-border-stronger rounded-lg focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:bg-surface disabled:text-dim"
        />
        <button
          type="submit"
          disabled={isInputDisabled}
          className="px-6 py-3 bg-brand text-inverse rounded-lg hover:bg-brand-strong disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <Send className="h-4 w-4" />
          <span className="hidden sm:inline">Send</span>
        </button>
      </form>
      <p className="text-xs text-dim mt-2">
        Use{" "}
        <kbd className="px-1 py-0.5 bg-muted border border-border-stronger rounded text-xs">
          Cmd
        </kbd>{" "}
        +{" "}
        <kbd className="px-1 py-0.5 bg-muted border border-border-stronger rounded text-xs">
          Enter
        </kbd>{" "}
        to send
      </p>
    </div>
  );
}

interface ChatMessagesListProps {
  readonly messages: readonly Message[];
  readonly virtuosoRef: RefObject<VirtuosoHandle | null>;
  readonly headerContent: ReactNode;
  readonly footerContent: ReactNode;
}

function ChatMessagesList({
  messages,
  virtuosoRef,
  headerContent,
  footerContent,
}: ChatMessagesListProps) {
  const components = useMemo(
    () => ({
      // eslint-disable-next-line @typescript-eslint/naming-convention -- react-virtuoso requires Header/Footer keys
      Header: () => headerContent,
      // eslint-disable-next-line @typescript-eslint/naming-convention -- react-virtuoso requires Header/Footer keys
      Footer: () => footerContent,
    }),
    [headerContent, footerContent],
  );

  if (messages.length === 0) {
    return (
      <div className="h-full p-6">
        <ChatEmptyState />
      </div>
    );
  }

  return (
    <Virtuoso
      ref={virtuosoRef}
      data={messages}
      initialTopMostItemIndex={messages.length - 1}
      followOutput="smooth"
      className="panel-scroll"
      itemContent={(_index, message) => (
        <div className="px-6 py-3">
          <MessageBubble key={message.id} message={message} />
        </div>
      )}
      components={components}
    />
  );
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



