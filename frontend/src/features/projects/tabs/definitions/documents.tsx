import { ProjectTab } from "../types";
import { DocumentsTabAdapter } from "../adapters/DocumentsTabAdapter";

export const documentsTab: ProjectTab = {
  id: "documents",
  label: "Documents",
  path: "documents",
  component: DocumentsTabAdapter,
};
