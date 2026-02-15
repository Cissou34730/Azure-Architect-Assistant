import { FileText } from "lucide-react";
import type { ReferenceDocument } from "../../../../../types/api";

interface InputDocumentViewProps {
  readonly document: ReferenceDocument;
}

export function InputDocumentView({ document }: InputDocumentViewProps) {
  const hasUrl = document.url !== undefined && document.url !== "";
  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg bg-info-soft flex items-center justify-center">
          <FileText className="h-5 w-5 text-info" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-foreground">{document.title}</h3>
          <p className="text-xs text-dim capitalize">{document.category}</p>
        </div>
      </div>
      <div className="rounded-lg border border-border bg-surface p-4 text-sm text-secondary">
        Document content is stored remotely. Use the action below to open it in a new tab.
      </div>
      <button
        type="button"
        onClick={() => {
          if (hasUrl) {
            window.open(document.url, "_blank");
          }
        }}
        disabled={!hasUrl}
        className="inline-flex items-center gap-2 rounded-md border border-border-stronger bg-card px-4 py-2 text-xs font-semibold text-secondary hover:bg-surface disabled:opacity-60"
      >
        Open source document
      </button>
    </div>
  );
}


