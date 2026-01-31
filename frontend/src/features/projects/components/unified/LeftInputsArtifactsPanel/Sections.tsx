import { FileText, FolderOpen, NotebookPen, ListChecks, MessageSquareQuote, ScrollText, Network, FileBadge, ShieldAlert, Database, Layers, Waypoints } from "lucide-react";
import { SectionHeader, TreeButton, TreeGroup, TreeRow, EmptyRow } from "./TreeElements";
import { getArtifactTotal, type ArtifactCounts } from "./artifactCounts";
import type { ReferenceDocument } from "../../../../../types/api";
import type { WorkspaceTab, ArtifactTab } from "../workspace/types";

interface InputsSectionProps {
  readonly documents: readonly ReferenceDocument[];
  readonly textRequirements: string;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
}

export function InputsSection({
  documents,
  textRequirements,
  onOpenTab,
}: InputsSectionProps) {
  const inputsCount = documents.length + (textRequirements.trim() !== "" ? 1 : 0);
  return (
    <div className="space-y-2">
      <SectionHeader title="Inputs" count={inputsCount} />
      <TreeButton
        icon={FolderOpen}
        label="Inputs Overview"
        badge={inputsCount}
        color="emerald"
        onClick={() => {
          onOpenTab({
            id: "input-overview",
            kind: "input-overview",
            title: "Inputs",
            group: "input",
          });
        }}
      />

      <TreeGroup label={`Uploaded Documents (${documents.length})`}>
        {documents.length === 0 ? (
          <EmptyRow text="No documents uploaded." />
        ) : (
          documents.map((doc) => (
            <TreeRow
              key={doc.id}
              icon={FileText}
              label={doc.title}
              onClick={() => {
                onOpenTab({
                  id: `input-document-${doc.id}`,
                  kind: "input-document",
                  title: doc.title,
                  group: "input",
                  documentId: doc.id,
                });
              }}
            />
          ))
        )}
      </TreeGroup>

      <TreeButton
        icon={NotebookPen}
        label="Clarifications"
        badge={textRequirements.trim() !== "" ? 1 : 0}
        color="emerald"
        onClick={() => {
          onOpenTab({
            id: "input-overview",
            kind: "input-overview",
            title: "Inputs",
            group: "input",
          });
        }}
      />
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
      {artifactItems.map((item) => (
        <TreeButton
          key={item.id}
          icon={item.icon}
          label={item.label}
          badge={getBadge(item)}
          color="blue"
          onClick={() => {
            onOpenTab({
              id: item.id,
              kind: item.id,
              title: item.title,
              group: "artifact",
            });
          }}
        />
      ))}
    </div>
  );
}

interface ArtifactItem {
  readonly id: ArtifactTab;
  readonly label: string;
  readonly icon: typeof FileText;
  readonly title: string;
  readonly badgeKey: keyof ArtifactCounts | "traceability";
}

const artifactItems: readonly ArtifactItem[] = [
  {
    id: "artifact-requirements",
    label: "Requirements",
    icon: FileBadge,
    title: "Requirements",
    badgeKey: "requirements",
  },
  {
    id: "artifact-assumptions",
    label: "Assumptions",
    icon: ListChecks,
    title: "Assumptions",
    badgeKey: "assumptions",
  },
  {
    id: "artifact-questions",
    label: "Questions",
    icon: MessageSquareQuote,
    title: "Questions",
    badgeKey: "questions",
  },
  {
    id: "artifact-adrs",
    label: "ADRs",
    icon: ScrollText,
    title: "ADRs",
    badgeKey: "adrs",
  },
  {
    id: "artifact-diagrams",
    label: "Diagrams",
    icon: Network,
    title: "Diagrams",
    badgeKey: "diagrams",
  },
  {
    id: "artifact-findings",
    label: "Findings",
    icon: ShieldAlert,
    title: "Findings",
    badgeKey: "findings",
  },
  {
    id: "artifact-iac",
    label: "IaC",
    icon: Database,
    title: "Infrastructure as Code",
    badgeKey: "iac",
  },
  {
    id: "artifact-costs",
    label: "Cost Estimates",
    icon: FileBadge,
    title: "Cost Estimates",
    badgeKey: "costs",
  },
  {
    id: "artifact-waf",
    label: "WAF Checklist",
    icon: ListChecks,
    title: "WAF Checklist",
    badgeKey: "waf",
  },
  {
    id: "artifact-traceability",
    label: "Traceability",
    icon: Waypoints,
    title: "Traceability",
    badgeKey: "traceability",
  },
  {
    id: "artifact-candidates",
    label: "Candidates",
    icon: Layers,
    title: "Candidate Architectures",
    badgeKey: "candidates",
  },
  {
    id: "artifact-iterations",
    label: "Iterations",
    icon: MessageSquareQuote,
    title: "Iteration Events",
    badgeKey: "iterations",
  },
  {
    id: "artifact-mcp",
    label: "MCP Queries",
    icon: FileBadge,
    title: "MCP Queries",
    badgeKey: "mcpQueries",
  },
];
