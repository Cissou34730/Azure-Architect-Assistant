import { useProjectMetaContext } from "../context/useProjectMetaContext";
import { ProjectHeader } from "../components/ProjectHeader";
import { LeftContextPanel } from "../components/unified/LeftContextPanel";
import { CenterChatArea } from "../components/unified/CenterChatArea";
import { RightDeliverablesPanel } from "../components/unified/RightDeliverablesPanel";
import { useUnifiedProjectPage } from "../hooks/useUnifiedProjectPage";
import { useRenderCount } from "../../../hooks/useRenderCount";

export default function UnifiedProjectPage() {
  useRenderCount("UnifiedProjectPage");
  const { selectedProject } = useProjectMetaContext();
  const {
    loading,
    projectState,
    leftPanelOpen,
    rightPanelOpen,
    handleUploadClick,
    handleGenerateDiagramClick,
    handleCreateAdrClick,
    handleExportClick,
    handleNavigateToDiagrams,
    handleNavigateToAdrs,
    handleNavigateToCosts,
    toggleLeftPanel,
    toggleRightPanel,
  } = useUnifiedProjectPage();

  if (selectedProject === null) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Project not found</h2>
          <p className="text-gray-600">The requested project could not be loaded.</p>
        </div>
      </div>
    );
  }

  if (loading && projectState === null) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
          <p className="text-gray-600">Loading project...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      <ProjectHeader
        onUploadClick={handleUploadClick}
        onGenerateClick={handleGenerateDiagramClick}
        onAdrClick={handleCreateAdrClick}
        onExportClick={handleExportClick}
      />

      <div className="flex-1 flex overflow-hidden">
        <LeftContextPanel
          isOpen={leftPanelOpen}
          onToggle={toggleLeftPanel}
        />

        <div className="flex-1 overflow-hidden">
          <CenterChatArea />
        </div>

        <RightDeliverablesPanel
          isOpen={rightPanelOpen}
          onToggle={toggleRightPanel}
          onNavigateToDiagrams={handleNavigateToDiagrams}
          onNavigateToAdrs={handleNavigateToAdrs}
          onNavigateToCosts={handleNavigateToCosts}
        />
      </div>
    </div>
  );
}
