import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useProjectContext } from "../context/useProjectContext";
import { DiagramGallery, AdrLibrary, IacViewer, CostBreakdown } from "../components/deliverables";

type TabType = "diagrams" | "adrs" | "iac" | "costs";

export default function ProjectDeliverablesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const tabParam = searchParams.get("tab") as TabType | null;
  const [activeTab, setActiveTab] = useState<TabType>(tabParam || "diagrams");

  const { selectedProject, projectState } = useProjectContext();

  const diagrams = projectState?.diagrams || [];
  const adrs = projectState?.adrs || [];
  const iacArtifacts = projectState?.iacArtifacts || [];
  const costEstimates = projectState?.costEstimates || [];

  if (!selectedProject) {
    return (
      <div className="text-center py-12 text-gray-500">
        Project not found
      </div>
    );
  }

  const tabs: { id: TabType; label: string; count: number }[] = [
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
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabChange(tab.id)}
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
                      isActive
                        ? "bg-blue-100 text-blue-600"
                        : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="pt-2">
        {activeTab === "diagrams" && <DiagramGallery diagrams={diagrams} />}
        {activeTab === "adrs" && <AdrLibrary adrs={adrs} />}
        {activeTab === "iac" && <IacViewer iacArtifacts={iacArtifacts} />}
        {activeTab === "costs" && <CostBreakdown costEstimates={costEstimates} />}
      </div>
    </div>
  );
}
