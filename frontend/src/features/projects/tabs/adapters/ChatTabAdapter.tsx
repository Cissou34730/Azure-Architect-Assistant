import { useState } from "react";
import { useParams } from "react-router-dom";
import { useProjectContext } from "../../context/ProjectContext";
import { useAgentChat } from "../../../../components/agent/hooks/useAgentChat";
import { AgentChatPanel } from "../../../../components/agent/AgentChatPanel";

export function ChatTabAdapter() {
  const { projectId } = useParams();
  const { setProjectState } = useProjectContext();
  const [showReasoning] = useState(false);

  const selectedProjectId = projectId ?? "";
  const { messages, input, isLoading, setInput, sendMessage } = useAgentChat({
    selectedProjectId,
    onProjectStateUpdate: setProjectState,
  });

  return (
    <AgentChatPanel
      messages={messages}
      input={input}
      isLoading={isLoading}
      showReasoning={showReasoning}
      selectedProjectId={selectedProjectId}
      onInputChange={setInput}
      onSendMessage={() => void sendMessage()}
    />
  );
}
