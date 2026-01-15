import { Message } from "../../../types/api";
import { MessageItem } from "./ChatPanel/MessageItem";
import { ChatLoadingStatus } from "./ChatPanel/ChatLoadingStatus";

interface ChatPanelProps {
  readonly messages: readonly Message[];
  readonly chatInput: string;
  readonly onChatInputChange: (input: string) => void;
  readonly onSendMessage: (e: React.FormEvent) => void;
  readonly loading: boolean;
  readonly loadingMessage: string;
}

export function ChatPanel({
  messages,
  chatInput,
  onChatInputChange,
  onSendMessage,
  loading,
  loadingMessage,
}: ChatPanelProps) {
  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Clarification Chat</h2>

      <ChatLoadingStatus loading={loading} message={loadingMessage} />

      <div className="h-96 overflow-y-auto border border-gray-200 rounded-md p-4 mb-4">
        {messages.map((msg) => (
          <MessageItem key={msg.id} message={msg} />
        ))}
      </div>

      <form onSubmit={onSendMessage} className="flex gap-2">
        <input
          type="text"
          value={chatInput}
          onChange={(e) => {
            onChatInputChange(e.target.value);
          }}
          placeholder="Ask a question or provide clarification..."
          className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || chatInput.trim() === ""}
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </form>
    </div>
  );
}
