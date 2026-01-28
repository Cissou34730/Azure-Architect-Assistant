import { useAaaWorkspace } from "./hooks/useAaaWorkspace";
import { RequirementReview } from "./components/RequirementReview";
import { ClarificationQuestions } from "./components/ClarificationQuestions";
import { CandidateArchitectures } from "./components/CandidateArchitectures";
import { AdrList } from "./components/AdrList";
import { FindingList } from "./components/FindingList";
import { IacList } from "./components/IacList";
import { CostEstimates } from "./components/CostEstimates";
import { TraceabilityPanel } from "./components/TraceabilityPanel";
import { IterationTimeline } from "./components/IterationTimeline";
import { MindMapCoveragePanel } from "./components/MindMapCoveragePanel";
import { AaaHeader } from "./components/AaaHeader";
import { AaaUploadForm } from "./components/AaaUploadForm";

function downloadTextFile(fileName: string, content: string) {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function Section({
  title,
  children,
}: {
  readonly title: string;
  readonly children: React.ReactNode;
}) {
  return (
    <div className="bg-gray-50 p-4 rounded-md border border-gray-200">
      <h3 className="font-semibold text-lg mb-2">{title}</h3>
      <div className="space-y-2 text-sm">{children}</div>
    </div>
  );
}

export default function AaaWorkspace() {
  const {
    selectedProject,
    files,
    setFiles,
    handleUploadDocuments,
    handleAnalyzeDocuments,
    loading,
    loadingMessage,
    requirements,
    clarificationQuestions,
    candidates,
    adrs,
    findings,
    iacArtifacts,
    costEstimates,
    iterationEvents,
    mindMapCoverage,
    traceabilityIssues,
    coverageTopics,
    traceabilityGroups,
    groupedRequirements,
  } = useAaaWorkspace();

  if (selectedProject === null) return null;

  return (
    <div className="space-y-6">
      <AaaHeader loading={loading} loadingMessage={loadingMessage} />

      <Section title="Upload & Analyze">
        <AaaUploadForm
          files={files}
          setFiles={setFiles}
          handleUploadDocuments={async (e) => {
            await handleUploadDocuments(e);
          }}
          handleAnalyzeDocuments={() => handleAnalyzeDocuments()}
          loading={loading}
        />
      </Section>

      <Section title="Requirements Review">
        <RequirementReview
          requirements={requirements}
          groupedRequirements={groupedRequirements}
        />
      </Section>

      <Section title="Clarification Questions">
        <ClarificationQuestions questions={clarificationQuestions} />
      </Section>

      <Section title="Candidate Architectures">
        <CandidateArchitectures candidates={candidates} />
      </Section>

      <Section title="ADRs">
        <AdrList adrs={adrs} />
      </Section>

      <Section title="Findings">
        <FindingList findings={findings} />
      </Section>

      <Section title="IaC">
        <IacList iac={iacArtifacts} onDownload={downloadTextFile} />
      </Section>

      <Section title="Cost Estimates">
        <CostEstimates costs={costEstimates} />
      </Section>

      <Section title="Mind Map Coverage">
        <MindMapCoveragePanel
          coverage={mindMapCoverage}
          topics={coverageTopics}
        />
      </Section>

      <Section title="Traceability">
        <TraceabilityPanel
          traceabilityGroups={traceabilityGroups}
          traceabilityIssues={traceabilityIssues}
        />
      </Section>

      <Section title="Iteration Timeline">
        <IterationTimeline events={iterationEvents} />
      </Section>
    </div>
  );
}
