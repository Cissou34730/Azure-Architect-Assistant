import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProjectContext } from "../context/useProjectContext";
import { QuickActionsBar } from "../components/unified/QuickActionsBar";
import { LeftContextPanel } from "../components/unified/LeftContextPanel";
import { CenterChatArea } from "../components/unified/CenterChatArea";
import { RightDeliverablesPanel } from "../components/unified/RightDeliverablesPanel";

export default function UnifiedProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  
  const {
    selectedProject,
    projectState,
    messages,
    sendMessage,
    loading,
  } = useProjectContext();

  // Panel states with localStorage persistence
  const [leftPanelOpen, setLeftPanelOpen] = useState(() => {
    const stored = localStorage.getItem("leftPanelOpen");
    return stored !== null ? stored === "true" : true;
  });
  
  const [rightPanelOpen, setRightPanelOpen] = useState(() => {
    const stored = localStorage.getItem("rightPanelOpen");
    return stored !== null ? stored === "true" : true;
  });

  // Extract data from projectState
  const requirements = projectState?.requirements || [];
  const assumptions = projectState?.assumptions || [];
  const questions = projectState?.clarificationQuestions || [];
  const adrs = projectState?.adrs || [];
  const diagrams = projectState?.diagrams || [];
  const costEstimates = projectState?.costEstimates || [];
  const findings = projectState?.findings || [];
  
  // Mock documents - in real app, these would come from API
  const documents: Array<{ id: string; name: string; size?: number; uploadedAt?: string }> = [];

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + [: Toggle left panel
      if ((e.metaKey || e.ctrlKey) && e.key === "[") {
        e.preventDefault();
        setLeftPanelOpen((prev) => !prev);
      }
      // Cmd/Ctrl + ]: Toggle right panel
      if ((e.metaKey || e.ctrlKey) && e.key === "]") {
        e.preventDefault();
        setRightPanelOpen((prev) => !prev);
      }
      // Cmd/Ctrl + /: Toggle both panels
      if ((e.metaKey || e.ctrlKey) && e.key === "/") {
        e.preventDefault();
        setLeftPanelOpen((prev) => !prev);
        setRightPanelOpen((prev) => !prev);
      }
      // Cmd/Ctrl + U: Focus upload
      if ((e.metaKey || e.ctrlKey) && e.key === "u") {
        e.preventDefault();
        handleUploadClick();
      }
      // Cmd/Ctrl + G: Generate diagram
      if ((e.metaKey || e.ctrlKey) && e.key === "g") {
        e.preventDefault();
        handleGenerateDiagramClick();
      }
      // Cmd/Ctrl + K: Create ADR
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        handleCreateAdrClick();
      }
      // Cmd/Ctrl + E: Export
      if ((e.metaKey || e.ctrlKey) && e.key === "e") {
        e.preventDefault();
        handleExportClick();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleSendMessage = useCallback(
    async (content: string) => {
      if (!selectedProject || !content.trim()) return;
      
      try {
        await sendMessage(content);
      } catch (error) {
        console.error("Failed to send message:", error);
      }
    },
    [selectedProject, sendMessage]
  );

  const handleUploadDocuments = useCallback(
    async (files: FileList) => {
      // TODO: Implement document upload via API
      console.log("Uploading files:", files);
    },
    []
  );

  // Action handlers
  const handleUploadClick = () => {
    // TODO: Trigger document upload - could expand upload section or open modal
    console.log("Upload clicked");
  };

  const handleGenerateDiagramClick = () => {
    // TODO: Trigger diagram generation flow
    console.log("Generate diagram clicked");
  };

  const handleCreateAdrClick = () => {
    // TODO: Trigger ADR creation flow
    console.log("Create ADR clicked");
  };

  const handleExportClick = () => {
    // TODO: Trigger export flow
    console.log("Export clicked");
  };

  const handleNavigateToDiagrams = () => {
    // Navigate to deliverables page with diagrams tab
    navigate(`/projects/${projectId}/deliverables?tab=diagrams`);
  };

  const handleNavigateToAdrs = () => {
    // Navigate to deliverables page with ADRs tab
    navigate(`/projects/${projectId}/deliverables?tab=adrs`);
  };

  const handleNavigateToCosts = () => {
    // Navigate to deliverables page with costs tab
    navigate(`/projects/${projectId}/deliverables?tab=costs`);
  };

  if (!selectedProject) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Project not found</h2>
          <p className="text-gray-600">The requested project could not be loaded.</p>
        </div>
      </div>
    );
  }

  if (loading && !projectState) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      {/* Quick Actions Bar - Sticky at top */}
      <QuickActionsBar
        projectName={selectedProject.name}
        onUploadClick={handleUploadClick}
        onGenerateDiagramClick={handleGenerateDiagramClick}
        onCreateAdrClick={handleCreateAdrClick}
        onExportClick={handleExportClick}
        onMenuClick={() => {
          setLeftPanelOpen(true);
          setRightPanelOpen(true);
        }}
      />

      {/* Main content area - 3 columns */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Context Panel */}
        <LeftContextPanel
          isOpen={leftPanelOpen}
          onToggle={() => setLeftPanelOpen(!leftPanelOpen)}
          requirements={requirements}
          assumptions={assumptions}
          questions={questions}
          documents={documents}
        />

        {/* Center Chat Area - Flexible width */}
        <div className="flex-1 overflow-hidden">
          <CenterChatArea
            messages={messages}
            onSendMessage={handleSendMessage}
            onUploadDocuments={handleUploadDocuments}
            loading={loading}
          />
        </div>

        {/* Right Deliverables Panel */}
        <RightDeliverablesPanel
          isOpen={rightPanelOpen}
          onToggle={() => setRightPanelOpen(!rightPanelOpen)}
          adrs={adrs}
          diagrams={diagrams}
          costEstimates={costEstimates}
          findings={findings}
          requirementsCount={requirements.length}
          onNavigateToDiagrams={handleNavigateToDiagrams}
          onNavigateToAdrs={handleNavigateToAdrs}
          onNavigateToCosts={handleNavigateToCosts}
        />
      </div>
    </div>
  );
}
