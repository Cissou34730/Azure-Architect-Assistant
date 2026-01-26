import { useState, useCallback, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useProjectContext } from "../context/useProjectContext";
import { ProjectHeader } from "../components/ProjectHeader";
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

  // Persist panel states to localStorage
  useEffect(() => {
    localStorage.setItem("leftPanelOpen", String(leftPanelOpen));
  }, [leftPanelOpen]);

  useEffect(() => {
    localStorage.setItem("rightPanelOpen", String(rightPanelOpen));
  }, [rightPanelOpen]);

  // Extract data from projectState - simple property access, no memo needed in React 19+
  const requirements = projectState?.requirements || [];
  const assumptions = projectState?.assumptions || [];
  const questions = projectState?.clarificationQuestions || [];
  const adrs = projectState?.adrs || [];
  const diagrams = projectState?.diagrams || [];
  const costEstimates = projectState?.costEstimates || [];
  const findings = projectState?.findings || [];
  
  // Mock documents - in real app, these would come from API
  const documents: Array<{ id: string; name: string; size?: number; uploadedAt?: string }> = [];

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
  const handleUploadClick = useCallback(() => {
    // TODO: Trigger document upload - could expand upload section or open modal
    console.log("Upload clicked");
  }, []);

  const handleGenerateDiagramClick = useCallback(() => {
    // TODO: Trigger diagram generation flow
    console.log("Generate diagram clicked");
  }, []);

  const handleCreateAdrClick = useCallback(() => {
    // TODO: Trigger ADR creation flow
    console.log("Create ADR clicked");
  }, []);

  const handleExportClick = useCallback(() => {
    // TODO: Trigger export flow
    console.log("Export clicked");
  }, []);

  const handleNavigateToDiagrams = useCallback(() => {
    // Navigate to deliverables page with diagrams tab
    navigate(`/projects/${projectId}/deliverables?tab=diagrams`);
  }, [navigate, projectId]);

  const handleNavigateToAdrs = useCallback(() => {
    // Navigate to deliverables page with ADRs tab
    navigate(`/projects/${projectId}/deliverables?tab=adrs`);
  }, [navigate, projectId]);

  const handleNavigateToCosts = useCallback(() => {
    // Navigate to deliverables page with costs tab
    navigate(`/projects/${projectId}/deliverables?tab=costs`);
  }, [navigate, projectId]);

  // Panel toggle handlers
  const toggleLeftPanel = useCallback(() => {
    setLeftPanelOpen((prev) => !prev);
  }, []);

  const toggleRightPanel = useCallback(() => {
    setRightPanelOpen((prev) => !prev);
  }, []);

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
      {/* Project Header - Sticky below main nav */}
      <ProjectHeader
        onUploadClick={handleUploadClick}
        onGenerateClick={handleGenerateDiagramClick}
        onAdrClick={handleCreateAdrClick}
        onExportClick={handleExportClick}
      />

      {/* Main content area - 3 columns */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Context Panel */}
        <LeftContextPanel
          isOpen={leftPanelOpen}
          onToggle={toggleLeftPanel}
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
          onToggle={toggleRightPanel}
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
