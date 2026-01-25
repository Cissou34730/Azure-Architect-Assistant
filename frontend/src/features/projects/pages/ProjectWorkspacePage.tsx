import { useState, useCallback, useEffect } from "react";
import { useProjectContext } from "../context/useProjectContext";
import { ChatPanel, ContextSidebar } from "../components/workspace";

export default function ProjectWorkspacePage() {
  const {
    selectedProject,
    projectState,
    messages,
    setChatInput,
    handleSendChatMessage,
    loading,
  } = useProjectContext();

  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Keyboard shortcut for toggling sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + /: Toggle sidebar
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        setSidebarOpen((prev) => !prev);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const requirements = projectState?.requirements || [];
  const assumptions = projectState?.assumptions || [];
  const questions = projectState?.clarificationQuestions || [];
  
  // Mock documents - in real app, these would come from project state or separate API
  const documents: Array<{ id: string; name: string; size?: number; uploadedAt?: string }> = [];

  const handleSend = useCallback(
    async (content: string) => {
      if (!selectedProject || !content.trim()) return;
      
      // Update the chat input first
      setChatInput(content);
      
      // Create a proper form event
      const fakeEvent = {
        preventDefault: () => {},
        currentTarget: {
          elements: {
            chatInput: { value: content }
          }
        }
      } as any;
      
      await handleSendChatMessage(fakeEvent);
      
      // Clear the input after sending
      setChatInput("");
    },
    [selectedProject, handleSendChatMessage, setChatInput]
  );

  if (!selectedProject) {
    return (
      <div className="text-center py-12 text-gray-500">
        Project not found
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-12rem)] -m-6">
      {/* Chat Panel */}
      <div className={`flex-1 transition-all ${sidebarOpen ? "mr-0" : "mr-0"}`}>
        <ChatPanel
          messages={messages}
          onSendMessage={handleSend}
          loading={loading}
        />
      </div>

      {/* Context Sidebar */}
      <div className={`transition-all ${sidebarOpen ? "w-80" : "w-0"}`}>
        <ContextSidebar
          requirements={requirements}
          assumptions={assumptions}
          questions={questions}
          documents={documents}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />
      </div>
    </div>
  );
}
