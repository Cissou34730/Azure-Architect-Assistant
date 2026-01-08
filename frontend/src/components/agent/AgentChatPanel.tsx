import { useRef, useEffect } from "react";
import type { Message } from "../../types/agent";
import { LoadingIndicator } from "../common";

interface AgentChatPanelProps {
  messages: Message[];
  input: string;
  isLoading: boolean;
  showReasoning: boolean;
  selectedProjectId: string;
  onInputChange: (value: string) => void;
  onSendMessage: () => void;
}

function MessageBubble({
  message,
  showReasoning,
}: {
  message: Message;
  showReasoning: boolean;
}) {
  return (
    <div
      className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          message.role === "user"
            ? "bg-accent-primary text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        <div className="whitespace-pre-wrap text-sm">{message.content}</div>

        {message.role === "assistant" &&
          showReasoning &&
          message.reasoningSteps &&
          message.reasoningSteps.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-300">
              <p className="text-xs font-semibold text-gray-700 mb-2">
                Reasoning Steps:
              </p>
              <div className="space-y-2">
                {message.reasoningSteps.map((step, stepIndex) => (
                  <div
                    key={stepIndex}
                    className="text-xs bg-white rounded p-2 border border-gray-200"
                  >
                    <p className="font-semibold text-gray-800">
                      Action: {step.action}
                    </p>
                    <p className="text-gray-600 mt-1">
                      Input: {step.action_input}
                    </p>
                    <p className="text-gray-600 mt-1">
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

function EmptyChat({ selectedProjectId }: { selectedProjectId: string }) {
  return (
    <div className="text-center text-gray-500 mt-12">
      <div className="text-6xl mb-4">💬</div>
      <h3 className="text-xl font-semibold mb-2">Start a conversation</h3>
      <p className="text-sm mb-4">
        {selectedProjectId
          ? "Ask about your project architecture, requirements, or get Azure recommendations."
          : "Select a project above for context-aware assistance, or ask generic Azure questions."}
      </p>
      <div className="mt-6 space-y-2 text-left max-w-lg mx-auto">
        <p className="text-sm font-medium text-gray-700">Try asking:</p>
        <ul className="text-sm text-gray-600 space-y-1">
          {selectedProjectId ? (
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSendMessage();
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 flex flex-col h-[calc(100vh-260px)]">
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
        <h2 className="text-lg font-semibold text-gray-900">Agent Chat</h2>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <EmptyChat selectedProjectId={selectedProjectId} />
        ) : (
          messages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              showReasoning={showReasoning}
            />
          ))
        )}
        {isLoading && <LoadingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex space-x-3">
          <textarea
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder={
              selectedProjectId
                ? "Ask about your project or specify requirements..."
                : "Ask about Azure architecture, security, or best practices..."
            }
            rows={2}
            disabled={isLoading}
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-accent-primary focus:border-transparent disabled:bg-gray-50 disabled:text-gray-500"
          />
          <button
            onClick={onSendMessage}
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-accent-primary text-white rounded-lg hover:bg-accent-dark disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
