import { useRef, useEffect } from "react";
import type { Message } from "../../types/agent";
import { LoadingIndicator } from "../common";

interface AgentChatPanelProps {
  readonly messages: readonly Message[];
  readonly input: string;
  readonly isLoading: boolean;
  readonly showReasoning: boolean;
  readonly selectedProjectId: string;
  readonly onInputChange: (value: string) => void;
  readonly onSendMessage: () => void;
}

function MessageBubble({
  message,
  showReasoning,
}: {
  readonly message: Message;
  readonly showReasoning: boolean;
}) {
  return (
    <div
      className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          message.role === "user"
            ? "bg-accent-primary text-inverse"
            : "bg-muted text-foreground"
        }`}
      >
        <div className="whitespace-pre-wrap text-sm">{message.content}</div>

        {message.role === "assistant" &&
          showReasoning &&
          message.reasoningSteps !== undefined &&
          message.reasoningSteps.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border-stronger">
              <p className="text-xs font-semibold text-secondary mb-2">
                Reasoning Steps:
              </p>
              <div className="space-y-2">
                {message.reasoningSteps.map((step) => (
                  <div
                    key={`${step.action}-${step.actionInput.substring(0, 20)}`}
                    className="text-xs bg-card rounded p-2 border border-border"
                  >
                    <p className="font-semibold text-foreground">
                      Action: {step.action}
                    </p>
                    <p className="text-secondary mt-1">
                      Input: {step.actionInput}
                    </p>
                    <p className="text-secondary mt-1">
                      Result: {step.observation.substring(0, 100)}...
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
      </div>
    </div>
  );
}

function EmptyChat({ selectedProjectId }: { readonly selectedProjectId: string }) {
  return (
    <div className="text-center text-dim mt-12">
      <div className="text-6xl mb-4">💬</div>
      <h3 className="text-xl font-semibold mb-2">Start a conversation</h3>
      <p className="text-sm mb-4">
        {selectedProjectId !== ""
          ? "Ask about your project architecture, requirements, or get Azure recommendations."
          : "Select a project above for context-aware assistance, or ask generic Azure questions."}
      </p>
      <div className="mt-6 space-y-2 text-left max-w-lg mx-auto">
        <p className="text-sm font-medium text-secondary">Try asking:</p>
        <ul className="text-sm text-secondary space-y-1">
          {selectedProjectId !== "" ? (
            <>
              <li>• &quot;We need 99.9% availability&quot;</li>
              <li>• &quot;What security measures should we implement?&quot;</li>
              <li>
                • &quot;How do we handle data residency requirements?&quot;
              </li>
            </>
          ) : (
            <>
              <li>• &quot;How do I secure Azure SQL Database?&quot;</li>
              <li>
                • &quot;What&apos;s the best way to implement
                microservices?&quot;
              </li>
              <li>• &quot;Show me Private Link configuration examples&quot;</li>
            </>
          )}
        </ul>
      </div>
    </div>
  );
}

export function AgentChatPanel({
  messages,
  input,
  isLoading,
  showReasoning,
  selectedProjectId,
  onInputChange,
  onSendMessage,
}: AgentChatPanelProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  return (
    <div className="bg-card rounded-lg shadow-sm border border-border flex flex-col h-[calc(100vh-260px)]">
      <div className="px-4 py-3 border-b border-border bg-surface">
        <h2 className="text-lg font-semibold text-foreground">Agent Chat</h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <EmptyChat selectedProjectId={selectedProjectId} />
        ) : (
          messages.map((message) => (
            <MessageBubble
              key={message.id ?? `msg-${message.role}-${message.content.substring(0, 20)}`}
              message={message}
              showReasoning={showReasoning}
            />
          ))
        )}
        {isLoading && <LoadingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border p-4">
        <div className="flex space-x-3">
          <textarea
            value={input}
            onChange={(e) => {
              onInputChange(e.target.value);
            }}
            onKeyDown={handleKeyDown}
            placeholder={
              selectedProjectId !== ""
                ? "Ask about your project or specify requirements..."
                : "Ask about Azure architecture, security, or best practices..."
            }
            rows={2}
            disabled={isLoading}
            className="flex-1 resize-none rounded-lg border border-border-stronger px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:bg-surface disabled:text-dim"
          />
          <button
            onClick={onSendMessage}
            disabled={isLoading || input.trim() === ""}
            className="px-6 py-3 bg-accent-primary text-inverse rounded-lg hover:bg-accent-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-dim mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}


