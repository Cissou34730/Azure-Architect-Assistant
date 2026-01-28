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
import { useProjectOverviewData } from "./useProjectOverviewData";
import { ProjectOverviewEmptyState } from "./ProjectOverviewEmptyState";

export default function ProjectOverviewPage() {
  const { selectedProject, projectState, loading } = useProjectContext();
  const {
    requirements,
    adrs,
    findings,
    mindMapCoverage,
    iterationEvents,
    monthlyCost,
    currencyCode,
    hasAnyData,
  } = useProjectOverviewData(projectState ?? null);

  if (selectedProject === null) {
    return (
      <div className="text-center py-12 text-gray-500">
        Project not found
      </div>
    );
  }

  if (loading && projectState === null) {
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

  if (!hasAnyData) {
    return <ProjectOverviewEmptyState />;
  }

  return (
    <div className="space-y-6">
      <HeroStats
        requirementsCount={requirements.length}
        adrsCount={adrs.length}
        findingsCount={findings.length}
        monthlyCost={monthlyCost}
        currencyCode={currencyCode}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <RequirementsCard requirements={requirements} />
        </div>

        <div className="space-y-6">
          <ArchitectureCoverageCard coverage={mindMapCoverage} />
          <WafAssessmentCard findings={findings} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ActivityTimeline events={iterationEvents} />
        </div>

        <QuickActions projectId={selectedProject.id} />
      </div>
    </div>
  );
}
