import { lazy } from "react";
import { useProjectContext } from "../../context/ProjectContext";

const ChatPanel = lazy(() =>
  import("../../components/ChatPanel").then((m) => ({ default: m.ChatPanel })),
);

export function ChatTabAdapter() {
  const {
    messages,
    chatInput,
    setChatInput,
    handleSendChatMessage,
    loading,
    loadingMessage,
  } = useProjectContext();

  return (
    <ChatPanel
      messages={messages}
      chatInput={chatInput}
      onChatInputChange={setChatInput}
      onSendMessage={handleSendChatMessage}
      loading={loading}
      loadingMessage={loadingMessage}
    />
  );
}
