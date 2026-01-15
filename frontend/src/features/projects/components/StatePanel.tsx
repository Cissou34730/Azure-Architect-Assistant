import { ProjectState } from "../../../types/api";
import { ContextSection } from "./ProjectState/ContextSection";
import { NfrSection } from "./ProjectState/NfrSection";
import { StructureSection } from "./ProjectState/StructureSection";
import { DataComplianceSection } from "./ProjectState/DataComplianceSection";
import { TechnicalConstraintsSection } from "./ProjectState/TechnicalConstraintsSection";
import { OpenQuestionsSection } from "./ProjectState/OpenQuestionsSection";

interface StatePanelProps {
  readonly projectState: ProjectState | null;
  readonly onRefreshState: () => void;
  readonly loading: boolean;
}

export function StatePanel({
  projectState,
  onRefreshState,
  loading,
}: StatePanelProps) {
  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Architecture Sheet</h2>
        <button
          onClick={onRefreshState}
          disabled={loading}
          className="bg-gray-600 text-white px-3 py-1 rounded-md hover:bg-gray-700 disabled:opacity-50 text-sm flex items-center gap-1"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
          Refresh
        </button>
      </div>

      {projectState !== null ? (
        <div className="space-y-4">
          <ContextSection context={projectState.context} />
          <NfrSection nfrs={projectState.nfrs} />
          <StructureSection structure={projectState.applicationStructure} />
          <DataComplianceSection
            dataCompliance={projectState.dataCompliance}
          />
          <TechnicalConstraintsSection
            constraints={projectState.technicalConstraints}
          />
          <OpenQuestionsSection questions={projectState.openQuestions} />
        </div>
      ) : (
        <p className="text-gray-500">
          No architecture sheet available. Please analyze documents first.
        </p>
      )}
    </div>
  );
}
