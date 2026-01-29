import { File } from "lucide-react";
import { Virtuoso } from "react-virtuoso";
import type { ReferenceDocument } from "../../../../../types/api";

interface DocumentsTabProps {
  readonly documents: readonly ReferenceDocument[];
}

export function DocumentsTab({ documents }: DocumentsTabProps) {
  if (documents.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-gray-500">
        No reference documents found for this architecture.
      </div>
    );
  }

  return (
    <div className="h-full">
      <Virtuoso
        data={documents}
        itemContent={(_index, doc) => (
          <div className="px-4 py-1">
            <div
              key={doc.id}
              className="flex items-start gap-2 p-3 bg-white rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => { 
                if (doc.url !== undefined) {
                  window.open(doc.url, "_blank"); 
                }
              }}
            >
              <File className="h-4 w-4 text-gray-600 shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-900 truncate">
                  {doc.title}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  <span className="capitalize">{doc.category}</span>
                  {doc.accessedAt !== undefined && (
                    <>
                      {" • "}
                      {new Date(doc.accessedAt).toLocaleDateString()}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
        style={{ height: "100%" }}
      />
    </div>
  );
}
