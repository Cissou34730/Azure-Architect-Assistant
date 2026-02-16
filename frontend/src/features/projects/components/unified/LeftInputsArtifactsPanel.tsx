import { memo, useMemo } from "react";
import { ChevronLeft } from "lucide-react";
import { featureFlags } from "../../../../config/featureFlags";
import { useProjectContext } from "../../context/useProjectContext";
import { useProjectStateContext } from "../../context/useProjectStateContext";
import type { WorkspaceTab } from "./workspace/types";
import { InputsSection, ArtifactsSection } from "./LeftInputsArtifactsPanel/Sections";
import type { ArtifactCounts } from "./LeftInputsArtifactsPanel/artifactCounts";

interface LeftInputsArtifactsPanelProps {
  readonly onToggle: () => void;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
}

function LeftInputsArtifactsPanelBase({
  onToggle,
  onOpenTab,
}: LeftInputsArtifactsPanelProps) {
  const { projectState } = useProjectStateContext();
  const { textRequirements, inputWorkflow } = useProjectContext();

  const documents = useMemo(
    () => projectState?.referenceDocuments ?? [],
    [projectState?.referenceDocuments],
  );

  const uploadState = useMemo(() => {
    if (inputWorkflow.uploadState !== "idle") {
      return inputWorkflow.uploadState;
    }
    if ((projectState?.projectDocumentStats?.attemptedDocuments ?? 0) > 0) {
      return "success";
    }
    return "idle";
  }, [inputWorkflow.uploadState, projectState?.projectDocumentStats?.attemptedDocuments]);

  const analysisState = useMemo(() => {
    if (inputWorkflow.analysisState !== "idle") {
      return inputWorkflow.analysisState;
    }
    if (projectState?.analysisSummary?.status === "success") {
      return "success";
    }
    return "idle";
  }, [inputWorkflow.analysisState, projectState?.analysisSummary?.status]);

  const artifacts = useMemo<ArtifactCounts>(() => {
    if (projectState === null) {
      return {
        requirements: 0,
        assumptions: 0,
        questions: 0,
        adrs: 0,
        diagrams: 0,
        findings: 0,
        costs: 0,
        iac: 0,
        waf: 0,
        traceabilityLinks: 0,
        traceabilityIssues: 0,
        candidates: 0,
        iterations: 0,
        mcpQueries: 0,
      };
    }
    return {
      requirements: projectState.requirements.length,
      assumptions: projectState.assumptions.length,
      questions: projectState.clarificationQuestions.length,
      adrs: projectState.adrs.length,
      diagrams: projectState.diagrams.length,
      findings: projectState.findings.length,
      costs: projectState.costEstimates.length,
      iac: projectState.iacArtifacts.length,
      waf: projectState.wafChecklist.items.length,
      traceabilityLinks: projectState.traceabilityLinks.length,
      traceabilityIssues: projectState.traceabilityIssues.length,
      candidates: projectState.candidateArchitectures.length,
      iterations: projectState.iterationEvents.length,
      mcpQueries: projectState.mcpQueries.length,
    };
  }, [projectState]);

  return (
    <div className="h-full flex flex-col bg-surface">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card shrink-0">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Project Tree</h2>
          <p className="text-xs text-dim">Inputs → Artifacts</p>
        </div>
        <button
          onClick={onToggle}
          className="p-1 hover:bg-muted rounded transition-colors"
          title="Hide panel"
          type="button"
        >
          <ChevronLeft className="h-5 w-5 text-secondary" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto panel-scroll px-3 py-4 space-y-4">
        <InputsSection
          documents={documents}
          textRequirements={textRequirements}
          uploadState={uploadState}
          analysisState={analysisState}
          workflowMessage={inputWorkflow.message}
          showStatusTrace={featureFlags.enableDocumentStatusTrace}
          showWorkflowTrace={featureFlags.enableUnifiedProjectInitialization}
          onOpenTab={onOpenTab}
        />
        <ArtifactsSection artifacts={artifacts} onOpenTab={onOpenTab} />
      </div>
    </div>
  );
}

const leftInputsArtifactsPanel = memo(LeftInputsArtifactsPanelBase);
export { leftInputsArtifactsPanel as LeftInputsArtifactsPanel };

