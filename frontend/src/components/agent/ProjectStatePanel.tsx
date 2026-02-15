import type { ProjectState } from "../../types/agent";
import { ContextSection } from "./ProjectState/ContextSection";
import { NfrSection } from "./ProjectState/NfrSection";
import { StructureSection } from "./ProjectState/StructureSection";
import { OpenQuestionsSection } from "./ProjectState/OpenQuestionsSection";

interface ProjectStatePanelProps {
  readonly selectedProjectId: string;
  readonly projectState: ProjectState | null;
  readonly isLoading: boolean;
}

export function ProjectStatePanel({
  selectedProjectId,
  projectState,
  isLoading,
}: ProjectStatePanelProps) {
  return (
    <div className="bg-card rounded-lg shadow-sm border border-border flex flex-col h-[calc(100vh-260px)]">
      <div className="px-4 py-3 border-b border-border bg-surface">
        <h2 className="text-lg font-semibold text-foreground">Project State</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {selectedProjectId === "" ? (
          <EmptyState />
        ) : isLoading || projectState === null ? (
          <LoadingState />
        ) : (
          <ProjectStateContent projectState={projectState} />
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center text-dim mt-12">
      <div className="text-6xl mb-4">📋</div>
      <h3 className="text-xl font-semibold mb-2">No Project Selected</h3>
      <p className="text-sm">
        Select a project from the dropdown above to view its architecture state.
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="text-center text-dim mt-12">
      <div className="text-6xl mb-4">⏳</div>
      <h3 className="text-xl font-semibold mb-2">Loading Project State...</h3>
      <p className="text-sm">
        Please wait while we fetch the project information.
      </p>
    </div>
  );
}

interface ProjectStateContentProps {
  readonly projectState: ProjectState;
}

function ProjectStateContent({ projectState }: ProjectStateContentProps) {
  return (
    <div className="space-y-6">
      {projectState.context !== undefined && (
        <ContextSection context={projectState.context} />
      )}

      {projectState.nfrs !== undefined && (
        <NfrSection nfrs={projectState.nfrs} />
      )}

      {projectState.applicationStructure !== undefined && (
        <StructureSection structure={projectState.applicationStructure} />
      )}

      <OpenQuestionsSection questions={projectState.openQuestions ?? []} />

      {projectState.lastUpdated !== undefined && (
        <div className="text-xs text-dim text-right">
          Last updated: {new Date(projectState.lastUpdated).toLocaleString()}
        </div>
      )}
    </div>
  );
}

