import { useProjectContext } from "../context/useProjectContext";
import { StatCardSkeleton } from "../../../components/common";
import {
  HeroStats,
  RequirementsCard,
  ArchitectureCoverageCard,
  WafAssessmentCard,
  QuickActions,
  ActivityTimeline,
} from "../components/overview";

export default function ProjectOverviewPage() {
  const { selectedProject, projectState, loading } = useProjectContext();

  if (!selectedProject) {
    return (
      <div className="text-center py-12 text-gray-500">
        Project not found
      </div>
    );
  }

  if (loading && !projectState) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  const requirements = projectState?.requirements || [];
  const adrs = projectState?.adrs || [];
  const findings = projectState?.findings || [];
  const costEstimates = projectState?.costEstimates || [];
  const mindMapCoverage = projectState?.mindMapCoverage;
  const iterationEvents = projectState?.iterationEvents || [];

  const latestCost = costEstimates.length > 0
    ? costEstimates[costEstimates.length - 1]
    : null;
  const monthlyCost = latestCost?.totalMonthlyCost || 0;
  const currencyCode = latestCost?.currencyCode || "USD";

  const hasAnyData = requirements.length > 0 ||
    adrs.length > 0 ||
    findings.length > 0 ||
    iterationEvents.length > 0;

  if (!hasAnyData) {
    return (
      <div className="flex flex-col items-center justify-center py-16 px-4">
        <div className="text-center max-w-md">
          <div className="mb-4 rounded-full bg-blue-50 p-6 inline-block">
            <svg
              className="h-16 w-16 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">
            Get Started
          </h3>
          <p className="text-gray-600 mb-6">
            Upload and analyze documents in the Workspace to start building your architecture.
          </p>
          <button
            onClick={() => {
              const event = new CustomEvent("navigate-to-workspace");
              window.dispatchEvent(event);
            }}
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors font-medium"
          >
            Go to Workspace
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Hero Stats */}
      <HeroStats
        requirementsCount={requirements.length}
        adrsCount={adrs.length}
        findingsCount={findings.length}
        monthlyCost={monthlyCost}
        currencyCode={currencyCode}
      />

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Requirements - Takes 2 columns */}
        <div className="lg:col-span-2">
          <RequirementsCard requirements={requirements} />
        </div>

        {/* Right Column - Coverage and WAF stacked */}
        <div className="space-y-6">
          <ArchitectureCoverageCard coverage={mindMapCoverage} />
          <WafAssessmentCard findings={findings} />
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity Timeline - Takes 2 columns */}
        <div className="lg:col-span-2">
          <ActivityTimeline events={iterationEvents} />
        </div>

        {/* Quick Actions */}
        <QuickActions projectId={selectedProject.id} />
      </div>
    </div>
  );
}
