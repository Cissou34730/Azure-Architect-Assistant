import { useProjectMetaContext } from "../context/useProjectMetaContext";
import { useSearchParams } from "react-router-dom";
import { usePanelWidth } from "../hooks/usePanelWidth";
import { useWorkspaceTabs } from "../hooks/useWorkspaceTabs";
import { useUnifiedProjectPage } from "../hooks/useUnifiedProjectPage";
import { useRenderCount } from "../../../shared/hooks/useRenderCount";
import { projectWorkspaceDefaultTabs } from "../workspace.manifest";
import { UnifiedProjectWorkspace } from "./UnifiedProjectWorkspace";
import { useProjectInputContext } from "../context/useProjectInputContext";
import { ProjectNotFound, ProjectLoading } from "./workspaceHelpers";
import { useInputDirtyIndicator, useWorkspaceQuickOpen, useRouteIntentHandlers } from "./workspaceHooks";

export default function UnifiedProjectPage() {
  useRenderCount("UnifiedProjectPage");
  const [searchParams, setSearchParams] = useSearchParams();
  const { selectedProject: selectedProjectMeta } = useProjectMetaContext();
  const {
    loading,
    projectState,
    leftPanelOpen,
    rightPanelOpen,
    handleExportClick,
    toggleLeftPanel,
    toggleRightPanel,
    openLeftPanel,
  } = useUnifiedProjectPage();
  const {
    textRequirements,
  } = useProjectInputContext();

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

  const initialTabs = projectWorkspaceDefaultTabs;
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
    savedText: selectedProjectMeta?.textRequirements ?? "",
    currentText: textRequirements,
    setDirty,
  });
  const { handleUploadClick, handleAdrClick } = useWorkspaceQuickOpen(
    openLeftPanel,
    openTab,
  );

  useRouteIntentHandlers({
    searchParams,
    setSearchParams,
    openLeftPanel,
    openTab,
    onGenerateCandidate: handleUploadClick,
  });

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


