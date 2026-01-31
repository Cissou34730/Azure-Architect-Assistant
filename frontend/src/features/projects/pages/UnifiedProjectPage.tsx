import { useProjectMetaContext } from "../context/useProjectMetaContext";
import { useCallback, useMemo } from "react";
import { usePanelWidth } from "../hooks/usePanelWidth";
import { useWorkspaceTabs } from "../hooks/useWorkspaceTabs";
import { useUnifiedProjectPage } from "../hooks/useUnifiedProjectPage";
import { useRenderCount } from "../../../hooks/useRenderCount";
import type { WorkspaceTab } from "../components/unified/workspace/types";
import { UnifiedProjectWorkspace } from "./UnifiedProjectWorkspace";

export default function UnifiedProjectPage() {
  useRenderCount("UnifiedProjectPage");
  const { selectedProject } = useProjectMetaContext();
  const {
    loading,
    projectState,
    leftPanelOpen,
    rightPanelOpen,
    handleGenerateDiagramClick,
    handleExportClick,
    toggleLeftPanel,
    toggleRightPanel,
    openLeftPanel,
  } = useUnifiedProjectPage();

  const leftPanelWidth = usePanelWidth({
    storageKey: "ux.leftPanelWidth",
    defaultWidth: 320,
    minWidth: 260,
    maxWidth: 480,
  });

  const rightPanelWidth = usePanelWidth({
    storageKey: "ux.rightPanelWidth",
    defaultWidth: 360,
    minWidth: 280,
    maxWidth: 520,
  });

  const initialTabs = useMemo<readonly WorkspaceTab[]>(() => [
    {
      id: "input-overview",
      kind: "input-overview",
      title: "Inputs",
      group: "input",
    },
  ], []);

  const {
    tabs,
    activeTabId,
    setActiveTabId,
    openTab,
    closeTab,
  } = useWorkspaceTabs(initialTabs);

  const handleUploadClick = useCallback(() => {
    openLeftPanel();
    openTab({
      id: "input-overview",
      kind: "input-overview",
      title: "Inputs",
      group: "input",
    });
  }, [openLeftPanel, openTab]);

  const handleAdrClick = useCallback(() => {
    openTab({
      id: "artifact-adrs",
      kind: "artifact-adrs",
      title: "ADRs",
      group: "artifact",
    });
  }, [openTab]);

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
    <UnifiedProjectWorkspace
      leftPanelOpen={leftPanelOpen}
      rightPanelOpen={rightPanelOpen}
      onToggleLeft={toggleLeftPanel}
      onToggleRight={toggleRightPanel}
      onUploadClick={handleUploadClick}
      onGenerateClick={handleGenerateDiagramClick}
      onAdrClick={handleAdrClick}
      onExportClick={handleExportClick}
      tabs={tabs}
      activeTabId={activeTabId}
      onTabChange={setActiveTabId}
      onCloseTab={closeTab}
      onOpenTab={openTab}
      leftPanelWidth={leftPanelWidth.width}
      rightPanelWidth={rightPanelWidth.width}
      onResizeLeft={leftPanelWidth.setWidth}
      onResizeRight={rightPanelWidth.setWidth}
    />
  );
}
