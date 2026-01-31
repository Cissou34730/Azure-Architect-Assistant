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
        <div className="h-10 w-10 rounded-lg bg-emerald-50 flex items-center justify-center">
          <FileText className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900">{document.title}</h3>
          <p className="text-xs text-gray-500 capitalize">{document.category}</p>
        </div>
      </div>
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-600">
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
        className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-60"
      >
        Open source document
      </button>
    </div>
  );
}
