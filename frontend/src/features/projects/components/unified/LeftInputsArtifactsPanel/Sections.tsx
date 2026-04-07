import { FileText } from "lucide-react";
import { SectionHeader, TreeButton, TreeGroup, TreeRow, EmptyRow } from "./TreeElements";
import { getArtifactTotal, type ArtifactCounts } from "./artifactCounts";
import type { ReferenceDocument } from "../../../types/api-artifacts";
import type { WorkspaceTab } from "../workspace/types";
import {
  createProjectDocumentTab,
  createProjectWorkspaceTab,
  projectWorkspaceArtifactTreeEntries,
  projectWorkspaceInputTreeEntries,
} from "../../../workspace.manifest";

interface InputsSectionProps {
  readonly documents: readonly ReferenceDocument[];
  readonly textRequirements: string;
  readonly uploadState: "idle" | "running" | "success" | "error";
  readonly analysisState: "idle" | "running" | "success" | "error";
  readonly workflowMessage: string;
  readonly showStatusTrace: boolean;
  readonly showWorkflowTrace: boolean;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
}

export function InputsSection({
  documents,
  textRequirements,
  uploadState,
  analysisState,
  workflowMessage,
  showStatusTrace,
  showWorkflowTrace,
  onOpenTab,
}: InputsSectionProps) {
  const inputsCount = documents.length + (textRequirements.trim() !== "" ? 1 : 0);
  return (
    <div className="space-y-2">
      <SectionHeader title="Inputs" count={inputsCount} />
      {projectWorkspaceInputTreeEntries.map((treeEntry) => (
        <TreeButton
          key={treeEntry.id}
          icon={treeEntry.icon}
          label={treeEntry.label}
          badge={treeEntry.badgeKey === "inputs" ? inputsCount : (textRequirements.trim() !== "" ? 1 : 0)}
          color={treeEntry.color}
          onClick={() => {
            onOpenTab(createProjectWorkspaceTab(treeEntry.tabId));
          }}
        />
      ))}

      <TreeGroup label={`Uploaded Documents (${documents.length})`}>
        {documents.length === 0 ? (
          <EmptyRow text="No documents uploaded." />
        ) : (
          documents.map((doc) => (
            <TreeRow
              key={doc.id}
              icon={FileText}
              label={doc.title}
              meta={
                showStatusTrace ? (
                  <DocumentStatusBadge
                    parseStatus={doc.parseStatus}
                    analysisStatus={doc.analysisStatus}
                    hasParseError={
                      doc.parseError !== undefined &&
                      doc.parseError !== null &&
                      doc.parseError !== ""
                    }
                  />
                ) : undefined
              }
              onClick={() => {
                onOpenTab(createProjectDocumentTab(doc));
              }}
            />
          ))
        )}
      </TreeGroup>

      {showWorkflowTrace && (
        <TreeGroup label="Processing">
          <EmptyRow text={`Upload: ${toWorkflowLabel(uploadState)}`} />
          <EmptyRow text={`Analysis: ${toWorkflowLabel(analysisState)}`} />
          {workflowMessage.trim() !== "" && <EmptyRow text={workflowMessage} />}
        </TreeGroup>
      )}
    </div>
  );
}

interface ArtifactsSectionProps {
  readonly artifacts: ArtifactCounts;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
}

export function ArtifactsSection({ artifacts, onOpenTab }: ArtifactsSectionProps) {
  const getBadge = (item: ArtifactItem) => {
    if (item.badgeKey === "traceability") {
      return artifacts.traceabilityLinks + artifacts.traceabilityIssues;
    }
    return artifacts[item.badgeKey];
  };

  return (
    <div className="space-y-2">
      <SectionHeader title="Artifacts" count={getArtifactTotal(artifacts)} />
      {projectWorkspaceArtifactTreeEntries.map((item) => (
        <TreeButton
          key={item.id}
          icon={item.treeEntry.icon}
          label={item.treeEntry.label}
          badge={getBadge(item)}
          color={item.treeEntry.color}
          onClick={() => {
            onOpenTab(createProjectWorkspaceTab(item.id));
          }}
        />
      ))}
    </div>
  );
}

interface ArtifactItem {
  readonly id: string;
  readonly badgeKey: keyof ArtifactCounts | "traceability";
}

function toWorkflowLabel(state: "idle" | "running" | "success" | "error"): string {
  switch (state) {
    case "running":
      return "In progress";
    case "success":
      return "Done";
    case "error":
      return "Failed";
    case "idle":
      return "Not started";
  }
}

function DocumentStatusBadge({
  parseStatus,
  analysisStatus,
  hasParseError,
}: {
  readonly parseStatus?: ReferenceDocument["parseStatus"];
  readonly analysisStatus?: ReferenceDocument["analysisStatus"];
  readonly hasParseError: boolean;
}) {
  const statusText =
    analysisStatus === "analyzed"
      ? "Analyzed"
      : analysisStatus === "analyzing"
      ? "Analyzing"
      : parseStatus === "parsed"
      ? "Parsed"
      : parseStatus === "parse_failed"
      ? "Parse failed"
      : "Unknown";

  const statusClass =
    analysisStatus === "analyzed"
      ? "border-success-line bg-success-soft text-success"
      : analysisStatus === "analyzing"
      ? "border-brand-line bg-brand-soft text-brand-strong"
      : parseStatus === "parsed"
      ? "border-info-line bg-info-soft text-info-strong"
      : "border-danger-line bg-danger-soft text-danger-strong";

  return (
    <span
      className={`rounded-full border px-1.5 py-0.5 text-[10px] font-semibold ${statusClass}`}
      title={hasParseError ? "Document has parse errors" : statusText}
    >
      {hasParseError ? "Issue" : statusText}
    </span>
  );
}
