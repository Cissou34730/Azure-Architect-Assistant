import { useRef, useEffect } from "react";
import { Send, Loader2 } from "lucide-react";
import { messageBubbleComp as MessageBubble } from "./MessageBubble";
import { ChatEmptyStateComp as ChatEmptyState } from "./ChatEmptyState";
import { useChatInput } from "./useChatInput";
import type { Message } from "../../../../types/api";

interface ChatPanelProps {
  messages: readonly Message[];
  onSendMessage: (content: string) => Promise<void>;
  loading?: boolean;
}

export function ChatPanel({
  messages,
  onSendMessage,
  loading = false,
}: ChatPanelProps) {
  const {
    input,
    sending,
    handleSubmit,
    handleKeyDown,
    handleInputChange,
  } = useChatInput(onSendMessage);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Use requestAnimationFrame to avoid forced reflow
  useEffect(() => {
    if (messagesEndRef.current !== null) {
      requestAnimationFrame(() => {
        // Smooth scrolling can be surprisingly expensive when messages are long.
        messagesEndRef.current?.scrollIntoView({ behavior: "auto" });
      });
    }
  }, [messages]);

  const isInputDisabled = input.trim() === "" || sending;

  return (
    <div className="flex flex-col h-full">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <ChatEmptyState />
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
            disabled={isInputDisabled}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Send</span>
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2">
          Use{" "}
          <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">
            Cmd
          </kbd>{" "}
          +{" "}
          <kbd className="px-1 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">
            Enter
          </kbd>{" "}
          to send
        </p>
      </div>
    </div>
  );
}
