import type { WorkspaceTab } from "./components/unified/workspace/types";
import type { ReferenceDocument } from "./types/api-artifacts";

export function createProjectDocumentTab(
  document: Pick<ReferenceDocument, "id" | "title">,
): WorkspaceTab {
  return {
    id: `input-document-${document.id}`,
    kind: "input-document",
    title: document.title,
    group: "input",
    documentId: document.id,
    pinned: false,
    dirty: false,
  };
}