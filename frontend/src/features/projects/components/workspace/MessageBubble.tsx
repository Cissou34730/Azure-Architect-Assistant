import { memo } from "react";
import { Badge } from "../../../../components/common";
import { messageContentComp as MessageContentComp } from "./MessageContent";
import type { Message } from "../../../../types/api";

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

interface MessageBubbleProps {
  message: Message;
}

// eslint-disable-next-line react-refresh/only-export-components -- Memoized component export pattern
function MessageBubbleInner({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const timestamp = new Date(message.timestamp);
  const kbSources = message.kbSources ?? [];

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
          <svg
            className="h-5 w-5 text-blue-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
            <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
          </svg>
        </div>
      )}

      <div className={`flex-1 max-w-3xl ${isUser ? "flex justify-end" : ""}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser ? "bg-blue-600 text-white" : "bg-gray-50 text-gray-900"
          }`}
        >
          <MessageContentComp content={message.content} isUser={isUser} />

          {!isUser && kbSources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 space-y-1">
              <p className="text-xs font-medium text-gray-600 mb-2">Sources:</p>
              <div className="flex flex-wrap gap-1">
                {kbSources.map((source) => (
                  <a
                    key={source.url}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block"
                  >
                    <Badge variant="info" size="sm">
                      {source.title}
                    </Badge>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-500 mt-1 px-1">
          {timeFormatter.format(timestamp)}
        </p>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center shrink-0">
          <svg
            className="h-5 w-5 text-gray-600"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
              clipRule="evenodd"
            />
          </svg>
        </div>
      )}
    </div>
  );
}

export const messageBubbleComp = memo(MessageBubbleInner);
