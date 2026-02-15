import { useProjectMetaContext } from "../context/useProjectMetaContext";
import { useCallback, useEffect } from "react";
import { useSearchParams, type SetURLSearchParams } from "react-router-dom";
import { usePanelWidth } from "../hooks/usePanelWidth";
import { useWorkspaceTabs } from "../hooks/useWorkspaceTabs";
import { useUnifiedProjectPage } from "../hooks/useUnifiedProjectPage";
import { useRenderCount } from "../../../hooks/useRenderCount";
import type { WorkspaceTab } from "../components/unified/workspace/types";
import { UnifiedProjectWorkspace } from "./UnifiedProjectWorkspace";
import { useProjectContext } from "../context/useProjectContext";

export default function UnifiedProjectPage() {
  useRenderCount("UnifiedProjectPage");
  const [searchParams, setSearchParams] = useSearchParams();
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
  useRouteIntentHandlers({
    searchParams,
    setSearchParams,
    openLeftPanel,
    openTab,
    onGenerateCandidate: handleGenerateDiagramClick,
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
  createInputOverviewTab(),
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
    openTab(createInputOverviewTab());
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

function useRouteIntentHandlers({
  searchParams,
  setSearchParams,
  openLeftPanel,
  openTab,
  onGenerateCandidate,
}: {
  readonly searchParams: URLSearchParams;
  readonly setSearchParams: SetURLSearchParams;
  readonly openLeftPanel: () => void;
  readonly openTab: (tab: WorkspaceTab) => void;
  readonly onGenerateCandidate: () => void;
}) {
  useEffect(() => {
    const nextParams = new URLSearchParams(searchParams);
    let shouldUpdateUrl = false;

    const tabIntent = normalizeParam(searchParams.get("tab"));
    if (tabIntent !== "") {
      const tab = resolveTabIntent(tabIntent);
      if (tab !== null) {
        if (tab.group === "input") {
          openLeftPanel();
        }
        openTab(tab);
        nextParams.delete("tab");
        shouldUpdateUrl = true;
      }
    }

    const actionIntent = normalizeParam(searchParams.get("action"));
    const promptIntent = normalizeParam(searchParams.get("prompt"));
    const runIntent = actionIntent !== "" ? actionIntent : promptIntent;
    let consumedAction = false;
    if (runIntent !== "") {
      if (runIntent === "generate-candidate") {
        onGenerateCandidate();
        consumedAction = true;
        shouldUpdateUrl = true;
      } else if (runIntent === "create-adr") {
        openTab(createAdrTab());
        consumedAction = true;
        shouldUpdateUrl = true;
      }
      if (consumedAction) {
        nextParams.delete("action");
        nextParams.delete("prompt");
      }
    }

    if (shouldUpdateUrl) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [
    onGenerateCandidate,
    openLeftPanel,
    openTab,
    searchParams,
    setSearchParams,
  ]);
}

function resolveTabIntent(tabIntent: string): WorkspaceTab | null {
  switch (tabIntent) {
    case "overview":
    case "inputs":
    case "workspace":
      return createInputOverviewTab();
    case "deliverables":
    case "diagrams":
      return createDiagramsTab();
    case "adrs":
      return createAdrTab();
    case "iac":
      return createIacTab();
    case "costs":
      return createCostsTab();
    case "waf":
      return createWafTab();
    default:
      return null;
  }
}

function normalizeParam(value: string | null): string {
  if (value === null) {
    return "";
  }
  return value.trim().toLowerCase();
}

function createInputOverviewTab(): WorkspaceTab {
  return {
    id: "input-overview",
    kind: "input-overview",
    title: "Inputs",
    group: "input",
    pinned: false,
    dirty: false,
  };
}

function createDiagramsTab(): WorkspaceTab {
  return {
    id: "artifact-diagrams",
    kind: "artifact-diagrams",
    title: "Diagrams",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

function createAdrTab(): WorkspaceTab {
  return {
    id: "artifact-adrs",
    kind: "artifact-adrs",
    title: "ADRs",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

function createIacTab(): WorkspaceTab {
  return {
    id: "artifact-iac",
    kind: "artifact-iac",
    title: "Infrastructure as Code",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

function createCostsTab(): WorkspaceTab {
  return {
    id: "artifact-costs",
    kind: "artifact-costs",
    title: "Cost Estimates",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

function createWafTab(): WorkspaceTab {
  return {
    id: "artifact-waf",
    kind: "artifact-waf",
    title: "WAF Checklist",
    group: "artifact",
    pinned: false,
    dirty: false,
  };
}

function ProjectNotFound() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h2 className="text-xl font-semibold text-foreground mb-2">Project not found</h2>
        <p className="text-secondary">The requested project could not be loaded.</p>
      </div>
    </div>
  );
}

function ProjectLoading() {
  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand mx-auto mb-4" />
        <p className="text-secondary">Loading project...</p>
      </div>
    </div>
  );
}

