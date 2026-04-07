import { memo } from "react";
import { Badge } from "../../../../shared/ui";
import { messageContentComp as MessageContentComp } from "./MessageContent";
import type { Message } from "../../../knowledge/types/api-kb";
import { useRenderCount } from "../../../../shared/hooks/useRenderCount";

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

interface MessageBubbleProps {
  message: Message;
}

// eslint-disable-next-line react-refresh/only-export-components -- co-located sub-component for single-concern rendering
function AssistantAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-brand-soft flex items-center justify-center shrink-0">
      <svg className="h-5 w-5 text-brand" fill="currentColor" viewBox="0 0 20 20">
        <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
        <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
      </svg>
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- co-located sub-component for single-concern rendering
function UserAvatar() {
  return (
    <div className="w-8 h-8 rounded-full bg-border-stronger flex items-center justify-center shrink-0">
      <svg className="h-5 w-5 text-secondary" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
      </svg>
    </div>
  );
}

interface BubbleContentProps {
  message: Message;
  isUser: boolean;
  toolActivity: readonly string[];
  kbSources: NonNullable<Message["kbSources"]>;
  isStreaming: boolean;
}

// eslint-disable-next-line react-refresh/only-export-components -- co-located sub-component for single-concern rendering
function BubbleContent({ message, isUser, toolActivity, kbSources, isStreaming }: BubbleContentProps) {
  return (
    <div className={`rounded-lg px-4 py-3 ${isUser ? "bg-brand text-inverse" : "bg-surface text-foreground"}`}>
      <MessageContentComp content={message.content} isUser={isUser} />
      {toolActivity.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border space-y-1">
          <p className="text-xs font-medium text-secondary">Tool activity</p>
          {toolActivity.map((item, index) => (
            // eslint-disable-next-line react/no-array-index-key -- tool activity items have no unique id
            <p key={`${message.id}-tool-${index}`} className="text-xs text-dim">{item}</p>
          ))}
        </div>
      )}
      {isStreaming && <div className="mt-3 text-xs text-dim">Streaming response...</div>}
      {kbSources.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border space-y-1">
          <p className="text-xs font-medium text-secondary mb-2">Sources:</p>
          <div className="flex flex-wrap gap-1">
            {kbSources.map((source) => (
              <a key={source.url} href={source.url} target="_blank" rel="noopener noreferrer" className="inline-block">
                <Badge variant="info" size="sm">{source.title}</Badge>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// eslint-disable-next-line react-refresh/only-export-components -- Memoized component export pattern
function MessageBubbleInner({ message }: MessageBubbleProps) {
  useRenderCount(`MessageBubble(${message.id})`);
  const isUser = message.role === "user";
  const kbSources = message.kbSources ?? [];
  const toolActivity = message.toolActivity ?? [];
  const isStreaming = message.streamingState === "streaming";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && <AssistantAvatar />}
      <div className={`flex-1 max-w-3xl ${isUser ? "flex justify-end" : ""}`}>
        <BubbleContent
          message={message}
          isUser={isUser}
          toolActivity={toolActivity}
          kbSources={kbSources}
          isStreaming={isStreaming}
        />
        <p className="text-xs text-dim mt-1 px-1">
          {timeFormatter.format(new Date(message.timestamp))}
        </p>
      </div>
      {isUser && <UserAvatar />}
    </div>
  );
}

export const messageBubbleComp = memo(MessageBubbleInner);





