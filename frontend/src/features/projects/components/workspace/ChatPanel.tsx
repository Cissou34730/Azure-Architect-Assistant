import { useState, useRef, useEffect, memo, useCallback, useMemo } from "react";
import { Send, Loader2 } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { Badge } from "../../../../components/common";
import type { Message } from "../../../../types/api";

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: "2-digit",
  minute: "2-digit",
});

interface ChatPanelProps {
  messages: readonly Message[];
  onSendMessage: (content: string) => Promise<void>;
  loading?: boolean;
}

export function ChatPanel({ messages, onSendMessage, loading = false }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Use requestAnimationFrame to avoid forced reflow
  useEffect(() => {
    if (messagesEndRef.current) {
      requestAnimationFrame(() => {
        // Smooth scrolling can be surprisingly expensive when messages are long.
        messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
      });
    }
  }, [messages]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    const message = input.trim();
    setInput("");
    setSending(true);

    try {
      await onSendMessage(message);
    } catch (error) {
      console.error("Failed to send message:", error);
    } finally {
      setSending(false);
    }
  }, [input, sending, onSendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e);
    }
  }, [handleSubmit]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  }, []);

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
            <svg
              className="h-16 w-16 mb-4 text-gray-300"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
              />
            </svg>
            <p className="text-lg font-medium text-gray-700 mb-2">
              Start a conversation
            </p>
            <p className="text-sm text-gray-500 max-w-md">
              Ask me to analyze documents, generate architecture candidates, create ADRs, or answer Azure questions.
            </p>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            {(loading || sending) && (
              <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                  <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />
                </div>
                <div className="bg-gray-50 rounded-lg px-4 py-3 text-sm text-gray-600">
                  Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Cmd+Enter to send)"
            disabled={sending}
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2">
          Use <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">Cmd</kbd> + <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">Enter</kbd> to send
        </p>
      </div>
    </div>
  );
}

const MessageBubble = memo(function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
          <svg className="h-5 w-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z" />
            <path d="M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z" />
          </svg>
        </div>
      )}

      <div className={`flex-1 max-w-3xl ${isUser ? "flex justify-end" : ""}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-gray-50 text-gray-900"
          }`}
        >
          <MessageContent content={message.content} isUser={isUser} />

          {!isUser && message.kbSources && message.kbSources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 space-y-1">
              <p className="text-xs font-medium text-gray-600 mb-2">Sources:</p>
              <div className="flex flex-wrap gap-1">
                {message.kbSources.map((source, idx) => (
                  <a
                    key={idx}
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-block"
                  >
                    <Badge variant="info" size="sm">
                      {source.title || `Source ${idx + 1}`}
                    </Badge>
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        <p className="text-xs text-gray-500 mt-1 px-1">
          {timeFormatter.format(new Date(message.timestamp))}
        </p>
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-gray-300 flex items-center justify-center shrink-0">
          <svg className="h-5 w-5 text-gray-600" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
          </svg>
        </div>
      )}
    </div>
  );
});

const MessageContent = memo(function MessageContent({ content, isUser }: { content: string; isUser: boolean }) {
  // Memoize the markdown components to prevent recreating on every render
  const markdownComponents = useMemo<Components>(
    () => ({
      code({ className, children }) {
        const match = /language-(\w+)/.exec(className || "");
        const isInline = !match;
        const code = String(children).replace(/\n$/, "");
        
        return !isInline && match ? (
          <SyntaxHighlighter
            style={oneDark}
            language={match[1]}
            PreTag="div"
          >
            {code}
          </SyntaxHighlighter>
        ) : (
          <code className={className}>
            {children}
          </code>
        );
      },
    }),
    []
  );

  if (isUser) {
    return <p className="text-sm whitespace-pre-wrap">{content}</p>;
  }

  return (
    <div className="prose prose-sm max-w-none prose-pre:bg-gray-900 prose-pre:text-gray-100">
      <ReactMarkdown components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
});
