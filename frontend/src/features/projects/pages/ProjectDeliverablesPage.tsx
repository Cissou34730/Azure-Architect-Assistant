import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useProjectContext } from "../context/useProjectContext";
import { DiagramGallery, AdrLibrary, IacViewer, CostBreakdown } from "../components/deliverables";
import type { AdrArtifact, IacArtifact, CostEstimate, ProjectState, DiagramData } from "../../../types/api";

type TabType = "diagrams" | "adrs" | "iac" | "costs";

function isTabType(tab: string | null): tab is TabType {
  return tab === "diagrams" || tab === "adrs" || tab === "iac" || tab === "costs";
}

interface TabContentProps {
  readonly activeTab: TabType;
  readonly diagrams: readonly DiagramData[];
  readonly adrs: readonly AdrArtifact[];
  readonly iacArtifacts: readonly IacArtifact[];
  readonly costEstimates: readonly CostEstimate[];
}

function TabContent({
  activeTab,
  diagrams,
  adrs,
  iacArtifacts,
  costEstimates,
}: TabContentProps) {
  switch (activeTab) {
    case "diagrams":
      return <DiagramGallery diagrams={diagrams} />;
    case "adrs":
      return <AdrLibrary adrs={adrs} />;
    case "iac":
      return <IacViewer iacArtifacts={iacArtifacts} />;
    case "costs":
      return <CostBreakdown costEstimates={costEstimates} />;
    default:
      return null;
  }
}

function DeliverablesEmptyState() {
  return (
    <div className="text-center py-12 text-gray-500">
      Project not found
    </div>
  );
}

interface TabNavItemProps {
  readonly tab: { id: TabType; label: string; count: number };
  readonly isActive: boolean;
  readonly onTabChange: (tabId: TabType) => void;
}

function TabNavItem({ tab, isActive, onTabChange }: TabNavItemProps) {
  return (
    <button
      type="button"
      onClick={() => {
        onTabChange(tab.id);
      }}
      className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
        isActive
          ? "border-blue-600 text-blue-600"
          : "border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300"
      }`}
    >
      {tab.label}
      {tab.count > 0 && (
        <span
          className={`ml-2 py-0.5 px-2 rounded-full text-xs ${
            isActive ? "bg-blue-100 text-blue-600" : "bg-gray-100 text-gray-600"
          }`}
        >
          {tab.count}
        </span>
      )}
    </button>
  );
}

function useDeliverablesData(projectState: ProjectState | null) {
  const diagrams: readonly DiagramData[] = projectState?.diagrams ?? [];
  const adrs = projectState?.adrs ?? [];
  const iacArtifacts = projectState?.iacArtifacts ?? [];
  const costEstimates = projectState?.costEstimates ?? [];

  return { diagrams, adrs, iacArtifacts, costEstimates };
}

export default function ProjectDeliverablesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab");
  const [activeTab, setActiveTab] = useState<TabType>(
    isTabType(tabParam) ? tabParam : "diagrams"
  );

  const { selectedProject, projectState } = useProjectContext();
  const { diagrams, adrs, iacArtifacts, costEstimates } =
    useDeliverablesData(projectState);

  if (selectedProject === null) {
    return <DeliverablesEmptyState />;
  }

  const tabs: readonly { id: TabType; label: string; count: number }[] = [
    { id: "diagrams", label: "Diagrams", count: diagrams.length },
    { id: "adrs", label: "ADRs", count: adrs.length },
    { id: "iac", label: "IaC", count: iacArtifacts.length },
    { id: "costs", label: "Cost Estimates", count: costEstimates.length },
  ];

  const handleTabChange = (tabId: TabType) => {
    setActiveTab(tabId);
    setSearchParams({ tab: tabId });
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8" aria-label="Tabs">
          {tabs.map((tab) => (
            <TabNavItem
              key={tab.id}
              tab={tab}
              isActive={activeTab === tab.id}
              onTabChange={handleTabChange}
            />
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="pt-2">
        <TabContent
          activeTab={activeTab}
          diagrams={diagrams}
          adrs={adrs}
          iacArtifacts={iacArtifacts}
          costEstimates={costEstimates}
        />
      </div>
    </div>
  );
}
