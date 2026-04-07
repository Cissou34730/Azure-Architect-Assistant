import { FolderOpen, NotebookPen } from "lucide-react";
import { DocumentsTab } from "../components/unified/LeftContextPanel/DocumentsTab";
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
} satisfies Partial<Record<"input-overview", ProjectWorkspaceStaticTabRenderer>>;
