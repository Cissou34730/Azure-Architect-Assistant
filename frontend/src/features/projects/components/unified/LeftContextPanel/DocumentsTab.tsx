import { File, UploadCloud, Save, Sparkles } from "lucide-react";
import { Virtuoso } from "react-virtuoso";
import type { ReferenceDocument } from "../../../../../types/api";
import { useProjectContext } from "../../../context/useProjectContext";

interface DocumentsTabProps {
  readonly documents: readonly ReferenceDocument[];
}

export function DocumentsTab({ documents }: DocumentsTabProps) {
  const {
    selectedProject,
    textRequirements,
    setTextRequirements,
    files,
    setFiles,
    handleSaveTextRequirements,
    handleUploadDocuments,
    handleAnalyzeDocuments,
    loading,
    loadingMessage,
  } = useProjectContext();

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 space-y-4 border-b border-gray-200 bg-white">
        <div>
          <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            Text Requirements
          </label>
          <textarea
            value={textRequirements}
            onChange={(e) => {
              setTextRequirements(e.target.value);
            }}
            rows={5}
            placeholder="Add business context, constraints, and requirements..."
            className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              Saved to the project before analysis.
            </span>
            <button
              type="button"
              onClick={() => {
                void handleSaveTextRequirements();
              }}
              disabled={loading || selectedProject === null}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Save className="h-3.5 w-3.5" />
              Save
            </button>
          </div>
        </div>

        <form
          onSubmit={(e) => {
            void handleUploadDocuments(e);
          }}
          className="space-y-2"
        >
          <label className="text-xs font-semibold text-gray-700 uppercase tracking-wide">
            Upload Documents
          </label>
          <input
            id="file-input"
            type="file"
            multiple
            onChange={(e) => {
              setFiles(e.target.files);
            }}
            className="block w-full text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-blue-50 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-blue-700 hover:file:bg-blue-100"
          />
          {files !== null && files.length > 0 && (
            <p className="text-xs text-gray-500">
              {files.length} file{files.length === 1 ? "" : "s"} selected
            </p>
          )}
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={loading || files === null || files.length === 0}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
            >
              <UploadCloud className="h-3.5 w-3.5" />
              Upload
            </button>
            <button
              type="button"
              onClick={() => {
                void handleAnalyzeDocuments();
              }}
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Analyze
            </button>
          </div>
          {loadingMessage !== "" && (
            <p className="text-xs text-gray-500">{loadingMessage}</p>
          )}
        </form>
      </div>

      {documents.length === 0 ? (
        <div className="p-4 text-center text-sm text-gray-500">
          No reference documents found for this architecture.
        </div>
      ) : (
        <div className="flex-1">
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
      )}
    </div>
  );
}
