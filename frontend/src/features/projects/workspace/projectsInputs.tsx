import { BarChart3, FolderOpen, GitBranch, NotebookPen, StickyNote } from "lucide-react";
import { DocumentsTab } from "../components/unified/LeftContextPanel/DocumentsTab";
import { ProjectNotesPanel } from "../components/unified/ProjectNotesPanel";
import { QualityGateTab } from "../components/unified/QualityGateTab";
import { TraceTab } from "../components/unified/TraceTab";
import { createProjectDocumentTab } from "../workspaceTabFactories";
import type {
  ProjectWorkspaceInputTreeEntry,
  ProjectWorkspaceStaticTabDefinition,
} from "../workspaceDefinition";
import type { ProjectWorkspaceStaticTabRenderer } from "../workspaceTabRenderTypes";

export const projectWorkspaceInputContributorId = "projects-inputs";

export const projectWorkspaceInputTreeEntries: readonly ProjectWorkspaceInputTreeEntry[] = [
  {
    id: "inputs-overview",
    tabId: "input-overview",
    label: "Inputs Overview",
    icon: FolderOpen,
    color: "emerald",
    badgeKey: "inputs",
  },
  {
    id: "clarifications",
    tabId: "input-overview",
    label: "Clarifications",
    icon: NotebookPen,
    color: "emerald",
    badgeKey: "clarifications",
  },
  {
    id: "project-notes",
    tabId: "project-notes",
    label: "Project Notes",
    icon: StickyNote,
    color: "emerald",
    badgeKey: "notes",
  },
  {
    id: "quality-gate",
    tabId: "quality-gate",
    label: "Quality Gate",
    icon: BarChart3,
    color: "emerald",
    badgeKey: "quality",
  },
  {
    id: "trace",
    tabId: "trace",
    label: "Trace",
    icon: GitBranch,
    color: "emerald",
    badgeKey: "trace",
  },
];

export const projectWorkspaceInputTabs: readonly ProjectWorkspaceStaticTabDefinition[] = [
  {
    id: "input-overview",
    kind: "input-overview",
    title: "Inputs",
    group: "input",
    intents: ["overview", "inputs", "workspace"],
    treeEntry: { label: "Inputs", icon: FolderOpen, color: "emerald" },
  },
  {
    id: "project-notes",
    kind: "project-notes",
    title: "Notes",
    group: "input",
    intents: ["notes", "project-notes"],
    treeEntry: { label: "Notes", icon: StickyNote, color: "emerald" },
  },
  {
    id: "quality-gate",
    kind: "quality-gate",
    title: "Quality Gate",
    group: "input",
    intents: ["quality", "quality-gate", "report"],
    treeEntry: { label: "Quality Gate", icon: BarChart3, color: "emerald" },
  },
  {
    id: "trace",
    kind: "trace",
    title: "Trace",
    group: "input",
    intents: ["trace", "timeline", "telemetry"],
    treeEntry: { label: "Trace", icon: GitBranch, color: "emerald" },
  },
];

function getDocumentById<TDocument extends { id: string }>(
  documents: readonly TDocument[],
  documentId: string,
): TDocument | undefined {
  return documents.find((document) => document.id === documentId);
}

export const projectWorkspaceInputRenderers = {
  ["input-overview"]: ({ documents, onOpenTab }) => (
    <DocumentsTab
      documents={documents}
      onOpenDocument={(documentId) => {
        const document = getDocumentById(documents, documentId);
        if (document === undefined) {
          return;
        }
        onOpenTab(createProjectDocumentTab(document));
      }}
    />
  ),
  ["project-notes"]: ({ projectState }) => (
    <ProjectNotesPanel projectId={projectState.projectId} />
  ),
  ["quality-gate"]: ({ projectState }) => (
    <QualityGateTab
      projectId={projectState.projectId}
      lastUpdated={projectState.lastUpdated}
    />
  ),
  ["trace"]: ({ projectState }) => (
    <TraceTab
      projectId={projectState.projectId}
      lastUpdated={projectState.lastUpdated}
    />
  ),
} satisfies Partial<
  Record<"input-overview" | "project-notes" | "quality-gate" | "trace", ProjectWorkspaceStaticTabRenderer>
>;
