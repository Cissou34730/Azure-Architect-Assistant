import { lazy } from "react";
import { useProjectContext } from "../../context/useProjectContext";

const CHAT_PANEL_LAZY = lazy(() =>
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

  const CHAT_PANEL = CHAT_PANEL_LAZY;

  return (
    <CHAT_PANEL
      messages={messages}
      chatInput={chatInput}
      onChatInputChange={setChatInput}
      onSendMessage={handleSendChatMessage}
      loading={loading}
      loadingMessage={loadingMessage}
    />
  );
}
