import { useProjectStateContext } from "../../../context/useProjectStateContext";
import type { ReferenceDocument } from "../../../../../types/api";
import { DocumentsTab } from "../LeftContextPanel/DocumentsTab";
import { InputDocumentView } from "./InputDocumentView";
import { ArtifactViews } from "./ArtifactViews";
import type { WorkspaceTab, ArtifactWorkspaceTab } from "./types";

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
  return documents.find((doc) => doc.id === documentId);
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

  if (tab.kind === "input-overview") {
    return (
      <div className="h-full">
        <DocumentsTab
          documents={documents}
          onOpenDocument={(documentId) => {
            const document = getDocumentById(documents, documentId);
            if (document === undefined) {
              return;
            }
            onOpenTab({
              id: `input-document-${document.id}`,
              kind: "input-document",
              title: document.title,
              group: "input",
              documentId: document.id,
              pinned: false,
              dirty: false,
            });
          }}
        />
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

  if (isArtifactTab(tab)) {
    return (
      <ArtifactViews
        tabKind={tab.kind}
        projectState={projectState}
        hasArtifacts={hasArtifacts}
      />
    );
  }

  return (
    <div className="p-6 text-sm text-dim">
      Select an item to view details.
    </div>
  );
}

function isArtifactTab(tab: WorkspaceTab): tab is ArtifactWorkspaceTab {
  return tab.group === "artifact";
}

