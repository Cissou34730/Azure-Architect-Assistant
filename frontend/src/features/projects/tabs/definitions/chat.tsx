import { ProjectTab } from "../types";
import { useProjectContext } from "../../context/ProjectContext";
import { ChatPanel } from "../../components/ChatPanel";

const ChatComponent = () => {
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
};

export const chatTab: ProjectTab = {
  id: "chat",
  label: "Chat",
  path: "chat",
  component: ChatComponent,
};
