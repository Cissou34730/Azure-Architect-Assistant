import { useState } from "react";
import { useAgentHealth } from "./hooks/useAgentHealth";
import { useProjects } from "./hooks/useProjects";
import { useProjectState } from "./hooks/useProjectState";
import { useAgentChat } from "./hooks/useAgentChat";
import { WorkspaceHeader } from "./WorkspaceHeader";
import { ProjectSelector } from "./ProjectSelector";
import { AgentChatPanel } from "./AgentChatPanel";
import { ProjectStatePanel } from "./ProjectStatePanel";

export function AgentChatWorkspace() {
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [showReasoning, setShowReasoning] = useState(false);

  const { agentStatus } = useAgentHealth();
  const { projects } = useProjects();
  const { projectState, setProjectState } = useProjectState(selectedProjectId);
  const { messages, input, isLoading, setInput, sendMessage, clearChat } =
    useAgentChat({
      selectedProjectId,
      onProjectStateUpdate: setProjectState,
    });

  const handleProjectChange = (projectId: string) => {
    setSelectedProjectId(projectId);
  };

  return (
    <div className="max-w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <div className="mb-6">
        <WorkspaceHeader
          agentStatus={agentStatus}
          showReasoning={showReasoning}
          onClearChat={clearChat}
          onToggleReasoning={() => setShowReasoning(!showReasoning)}
        />

        <ProjectSelector
          projects={projects}
          selectedProjectId={selectedProjectId}
          onProjectChange={handleProjectChange}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AgentChatPanel
          messages={messages}
          input={input}
          isLoading={isLoading}
          showReasoning={showReasoning}
          selectedProjectId={selectedProjectId}
          onInputChange={setInput}
          onSendMessage={sendMessage}
        />

        <ProjectStatePanel
          selectedProjectId={selectedProjectId}
          projectState={projectState}
          isLoading={false}
        />
      </div>
    </div>
  );
}
