import { useProjectMetaContext } from "../context/useProjectMetaContext";
import { useCallback, useEffect } from "react";
import { usePanelWidth } from "../hooks/usePanelWidth";
import { useWorkspaceTabs } from "../hooks/useWorkspaceTabs";
import { useUnifiedProjectPage } from "../hooks/useUnifiedProjectPage";
import { useRenderCount } from "../../../hooks/useRenderCount";
import type { WorkspaceTab } from "../components/unified/workspace/types";
import { UnifiedProjectWorkspace } from "./UnifiedProjectWorkspace";
import { useProjectContext } from "../context/useProjectContext";

export default function UnifiedProjectPage() {
  useRenderCount("UnifiedProjectPage");
  const { selectedProject: selectedProjectMeta } = useProjectMetaContext();
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
  const { textRequirements, selectedProject: selectedProjectContext } = useProjectContext();

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

  const initialTabs = DEFAULT_TABS;
  const resetKey = selectedProjectMeta?.id ?? projectState?.projectId ?? "no-project";

  const {
    tabs,
    activeTabId,
    setActiveTabId,
    openTab,
    closeTab,
    togglePin,
    reorderTabs,
    setDirty,
  } = useWorkspaceTabs(initialTabs, resetKey);

  useInputDirtyIndicator({
    savedText: selectedProjectContext?.textRequirements ?? "",
    currentText: textRequirements,
    setDirty,
  });

  const { handleUploadClick, handleAdrClick } = useWorkspaceQuickOpen(openLeftPanel, openTab);

  if (selectedProjectMeta === null) {
    return <ProjectNotFound />;
  }

  if (loading && projectState === null) {
    return <ProjectLoading />;
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
      onTogglePin={togglePin}
      onReorderTab={reorderTabs}
      leftPanelWidth={leftPanelWidth.width}
      rightPanelWidth={rightPanelWidth.width}
      onResizeLeft={leftPanelWidth.setWidth}
      onResizeRight={rightPanelWidth.setWidth}
    />
  );
}

const DEFAULT_TABS: readonly WorkspaceTab[] = [
  {
    id: "input-overview",
    kind: "input-overview",
    title: "Inputs",
    group: "input",
    pinned: false,
    dirty: false,
  },
];

function useInputDirtyIndicator({
  savedText,
  currentText,
  setDirty,
}: {
  readonly savedText: string;
  readonly currentText: string;
  readonly setDirty: (tabId: string, dirty: boolean) => void;
}) {
  useEffect(() => {
    const hasChanges = currentText.trim() !== savedText.trim();
    setDirty("input-overview", hasChanges);
  }, [currentText, savedText, setDirty]);
}

function useWorkspaceQuickOpen(
  openLeftPanel: () => void,
  openTab: (tab: WorkspaceTab) => void,
) {
  const handleUploadClick = useCallback(() => {
    openLeftPanel();
    openTab({
      id: "input-overview",
      kind: "input-overview",
      title: "Inputs",
      group: "input",
      pinned: false,
      dirty: false,
    });
  }, [openLeftPanel, openTab]);

  const handleAdrClick = useCallback(() => {
    openTab({
      id: "artifact-adrs",
      kind: "artifact-adrs",
      title: "ADRs",
      group: "artifact",
      pinned: false,
      dirty: false,
    });
  }, [openTab]);

  return { handleUploadClick, handleAdrClick };
}

function ProjectNotFound() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Project not found</h2>
        <p className="text-gray-600">The requested project could not be loaded.</p>
      </div>
    </div>
  );
}

function ProjectLoading() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
        <p className="text-gray-600">Loading project...</p>
      </div>
    </div>
  );
}
