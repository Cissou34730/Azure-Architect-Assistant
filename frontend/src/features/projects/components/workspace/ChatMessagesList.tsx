import { useMemo, type ReactNode, type RefObject } from "react";
import { Virtuoso, type VirtuosoHandle } from "react-virtuoso";
import { messageBubbleComp as MessageBubble } from "./MessageBubble";
import { ChatEmptyStateComp as ChatEmptyState } from "./ChatEmptyState";
import type { Message } from "../../../../types/api";

interface ChatMessagesListProps {
  readonly messages: readonly Message[];
  readonly virtuosoRef: RefObject<VirtuosoHandle | null>;
  readonly headerContent: ReactNode;
  readonly footerContent: ReactNode;
}

export function ChatMessagesList({
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
