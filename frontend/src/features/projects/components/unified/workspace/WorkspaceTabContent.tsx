import { useProjectStateContext } from "../../../context/useProjectStateContext";
import type { ReferenceDocument } from "../../../types/api-artifacts";
import { InputDocumentView } from "./InputDocumentView";
import type { WorkspaceTab } from "./types";
import { renderProjectWorkspaceStaticTabContent } from "../../../workspaceTabRegistry";

interface WorkspaceTabContentProps {
  readonly tab: WorkspaceTab;
  readonly documents: readonly ReferenceDocument[];
  readonly hasArtifacts: boolean;
  readonly onOpenTab: (tab: WorkspaceTab) => void;
}

function getDocumentById(
  documents: readonly ReferenceDocument[],
  documentId: string,
): ReferenceDocument | undefined {
  return documents.find((document) => document.id === documentId);
}

export function WorkspaceTabContent({
  tab,
  documents,
  hasArtifacts,
  onOpenTab,
}: WorkspaceTabContentProps) {
  const { projectState } = useProjectStateContext();

  if (projectState === null) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-dim">
        Loading project data...
      </div>
    );
  }

  if (tab.kind === "input-document") {
    const document = getDocumentById(documents, tab.documentId);
    if (document === undefined) {
      return (
        <div className="p-6 text-sm text-dim">
          This document is no longer available.
        </div>
      );
    }
    return <InputDocumentView document={document} />;
  }

  return renderProjectWorkspaceStaticTabContent(tab.kind, {
    projectState,
    documents,
    hasArtifacts,
    onOpenTab,
  });
}

