import { useState } from "react";
import { ChevronDown, ChevronRight, FileText } from "lucide-react";
import { SectionHeader, TreeButton, TreeGroup, TreeRow, EmptyRow } from "./TreeElements";
import { getArtifactTotal, type ArtifactCounts } from "./artifactCounts";
import type { ReferenceDocument } from "../../../types/api-artifacts";
import type { WorkspaceTab } from "../workspace/types";
import type { ArtifactCategory, ProjectWorkspaceArtifactTabDefinition } from "../../../workspaceDefinition";
import {
  createProjectDocumentTab,
  createProjectWorkspaceTab,
  projectWorkspaceArtifactTreeEntries,
  projectWorkspaceInputTreeEntries,
} from "../../../workspace.manifest";

interface InputsSectionProps {
  readonly documents: readonly ReferenceDocument[];
  readonly textRequirements: string;
  readonly notesCount: number;
  readonly qualityCount: number;
  readonly traceCount: number;
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
  notesCount,
  qualityCount,
  traceCount,
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
          badge={
            treeEntry.badgeKey === "inputs"
              ? inputsCount
              : treeEntry.badgeKey === "clarifications"
              ? (textRequirements.trim() !== "" ? 1 : 0)
              : treeEntry.badgeKey === "quality"
              ? qualityCount
              : treeEntry.badgeKey === "trace"
              ? traceCount
              : notesCount
          }
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

const CATEGORY_LABELS: Record<ArtifactCategory, string> = {
  requirements: "Requirements & Discovery",
  architecture: "Architecture",
  validation: "Validation",
  operations: "Operations",
  activity: "Activity",
};

const CATEGORY_ORDER: readonly ArtifactCategory[] = [
  "requirements",
  "architecture",
  "validation",
  "operations",
  "activity",
];

export function ArtifactsSection({ artifacts, onOpenTab }: ArtifactsSectionProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<ArtifactCategory>>(
    () => new Set(["requirements", "architecture"]),
  );

  const getBadge = (item: ProjectWorkspaceArtifactTabDefinition) => {
    if (item.badgeKey === "traceability") {
      return artifacts.traceabilityLinks + artifacts.traceabilityIssues;
    }
    return artifacts[item.badgeKey];
  };

  const grouped = new Map<ArtifactCategory, ProjectWorkspaceArtifactTabDefinition[]>();
  for (const item of projectWorkspaceArtifactTreeEntries) {
    const category = item.category ?? "activity";
    const existing = grouped.get(category) ?? [];
    existing.push(item);
    grouped.set(category, existing);
  }

  const toggleCategory = (category: ArtifactCategory) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  const getCategoryTotal = (items: ProjectWorkspaceArtifactTabDefinition[]) =>
    items.reduce((sum, item) => sum + getBadge(item), 0);

  return (
    <div className="space-y-2">
      <SectionHeader title="Artifacts" count={getArtifactTotal(artifacts)} />
      {CATEGORY_ORDER.map((category) => {
        const items = grouped.get(category);
        if (items === undefined || items.length === 0) {
          return null;
        }
        const isExpanded = expandedCategories.has(category);
        const total = getCategoryTotal(items);
        return (
          <div key={category} className="rounded-lg border border-border bg-card overflow-hidden">
            <button
              type="button"
              onClick={() => { toggleCategory(category); }}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-dim hover:bg-surface transition-colors"
            >
              {isExpanded ? (
                <ChevronDown className="h-3.5 w-3.5 shrink-0" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 shrink-0" />
              )}
              <span className="flex-1 text-left">{CATEGORY_LABELS[category]}</span>
              <span className="text-xs font-normal tabular-nums text-secondary">{total}</span>
            </button>
            {isExpanded && (
              <div className="border-t border-border p-2 space-y-1">
                {items.map((item) => (
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
            )}
          </div>
        );
      })}
    </div>
  );
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
