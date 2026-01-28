import { ChatPanel } from "../workspace/ChatPanel";
import { useProjectChatContext } from "../../context/useProjectChatContext";

export function CenterChatArea() {
  const { messages, sendMessage, loading } = useProjectChatContext();

  const handleSendMessage = async (content: string) => {
    await sendMessage(content);
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Chat Panel - Takes remaining space */}
      <div className="flex-1 overflow-hidden">
        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          loading={loading}
        />
      </div>
    </div>
  );
}
