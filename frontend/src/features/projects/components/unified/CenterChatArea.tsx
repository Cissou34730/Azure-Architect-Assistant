import { useCallback, memo } from "react";
import { ChatPanel } from "../workspace/ChatPanel";
import { useProjectChatContext } from "../../context/useProjectChatContext";
import { useRenderCount } from "../../../../hooks/useRenderCount";

function CenterChatArea() {
  useRenderCount("CenterChatArea");
  const { 
    messages, 
    sendMessage, 
    loading, 
    fetchOlderMessages,
    failedMessages,
    retrySendMessage
  } = useProjectChatContext();

  const handleSendMessage = useCallback(async (content: string) => {
    await sendMessage(content);
  }, [sendMessage]);

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Chat Panel - Takes remaining space */}
      <div className="flex-1 overflow-hidden">
        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          loading={loading}
          onLoadOlderMessages={fetchOlderMessages}
          failedMessages={failedMessages}
          onRetryMessage={retrySendMessage}
        />
      </div>
    </div>
  );
}

const centerChatArea = memo(CenterChatArea);
export { centerChatArea as CenterChatArea };
