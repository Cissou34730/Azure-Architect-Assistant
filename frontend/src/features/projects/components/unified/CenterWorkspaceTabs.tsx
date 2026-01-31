import { useMemo } from "react";
import { useProjectStateContext } from "../../context/useProjectStateContext";
import type { WorkspaceTab } from "./workspace/types";
import { WorkspaceTabContent } from "./workspace/WorkspaceTabContent";

interface CenterWorkspaceTabsProps {
  readonly tabs: readonly WorkspaceTab[];
  readonly activeTabId: string;
  readonly onTabChange: (tabId: string) => void;
  readonly onCloseTab: (tabId: string) => void;
}

const TAB_DOT_CLASS: Record<"input" | "artifact", string> = {
  input: "bg-emerald-500",
  artifact: "bg-blue-500",
};

function TabDot({ group }: { readonly group: "input" | "artifact" }) {
  return <span className={`h-2 w-2 rounded-full ${TAB_DOT_CLASS[group]}`} />;
}

export function CenterWorkspaceTabs({
  tabs,
  activeTabId,
  onTabChange,
  onCloseTab,
}: CenterWorkspaceTabsProps) {
  const { projectState } = useProjectStateContext();
  const documents = useMemo(
    () => projectState?.referenceDocuments ?? [],
    [projectState?.referenceDocuments],
  );

  const hasArtifacts = useMemo(() => {
    if (projectState === null) {
      return false;
    }
    return (
      projectState.requirements.length > 0 ||
      projectState.adrs.length > 0 ||
      projectState.diagrams.length > 0 ||
      projectState.findings.length > 0 ||
      projectState.iacArtifacts.length > 0 ||
      projectState.costEstimates.length > 0
    );
  }, [projectState]);

  if (tabs.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-500">
        Select an input or artifact from the left panel.
      </div>
    );
  }

  const activeTab = tabs.find((tab) => tab.id === activeTabId) ?? tabs[0];

  return (
    <div className="flex flex-col h-full bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="border-b border-gray-200 bg-slate-100">
        <div className="flex items-stretch overflow-x-auto">
          {tabs.map((tab) => {
            const isActive = tab.id === activeTab.id;
            return (
              <div
                key={tab.id}
                className={`group flex items-stretch border-r border-gray-200 ${
                  isActive ? "bg-white" : "bg-slate-100 hover:bg-slate-50"
                }`}
              >
                <button
                  type="button"
                  onClick={() => { onTabChange(tab.id); }}
                  className={`flex items-center gap-2 px-3 text-xs font-medium h-9 ${
                    isActive
                      ? "text-gray-900 border-b-2 border-blue-500"
                      : "text-gray-600"
                  }`}
                >
                  <TabDot group={tab.group} />
                  <span className="truncate max-w-[14rem]">{tab.title}</span>
                </button>
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    onCloseTab(tab.id);
                  }}
                  aria-label={`Close ${tab.title}`}
                  className="h-9 px-2 text-gray-400 hover:text-gray-700 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      </div>

      <div className="flex-1 overflow-hidden bg-white">
        <WorkspaceTabContent tab={activeTab} documents={documents} hasArtifacts={hasArtifacts} />
      </div>
    </div>
  );
}
