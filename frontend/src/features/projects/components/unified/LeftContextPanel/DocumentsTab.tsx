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
      <div className="p-4 space-y-4 border-b border-border bg-card">
        <TextRequirementsSection
          textRequirements={textRequirements}
          onChange={setTextRequirements}
          onSave={handleSaveTextRequirements}
          loading={loading}
          hasProject={selectedProject !== null}
        />
        <UploadDocumentsSection
          files={files}
          onFilesChange={setFiles}
          onUpload={handleUploadDocuments}
          onAnalyze={handleAnalyzeDocuments}
          loading={loading}
          loadingMessage={loadingMessage}
        />
      </div>

      <DocumentsList documents={documents} />
    </div>
  );
}

interface TextRequirementsSectionProps {
  readonly textRequirements: string;
  readonly onChange: (value: string) => void;
  readonly onSave: () => Promise<void>;
  readonly loading: boolean;
  readonly hasProject: boolean;
}

function TextRequirementsSection({
  textRequirements,
  onChange,
  onSave,
  loading,
  hasProject,
}: TextRequirementsSectionProps) {
  return (
    <div>
      <label className="text-xs font-semibold text-secondary uppercase tracking-wide">
        Text Requirements
      </label>
      <textarea
        value={textRequirements}
        onChange={(e) => {
          onChange(e.target.value);
        }}
        rows={5}
        placeholder="Add business context, constraints, and requirements..."
        className="mt-2 w-full rounded-lg border border-border-stronger px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
      />
      <div className="mt-2 flex items-center justify-between">
        <span className="text-xs text-dim">
          Saved to the project before analysis.
        </span>
        <button
          type="button"
          onClick={() => {
            void onSave();
          }}
          disabled={loading || !hasProject}
          className="inline-flex items-center gap-2 rounded-md border border-border-stronger bg-card px-3 py-1.5 text-xs font-semibold text-secondary hover:bg-surface disabled:opacity-50"
        >
          <Save className="h-3.5 w-3.5" />
          Save
        </button>
      </div>
    </div>
  );
}

interface UploadDocumentsSectionProps {
  readonly files: FileList | null;
  readonly onFilesChange: (files: FileList | null) => void;
  readonly onUpload: (event: React.FormEvent) => Promise<void>;
  readonly onAnalyze: () => Promise<void>;
  readonly loading: boolean;
  readonly loadingMessage: string;
}

function UploadDocumentsSection({
  files,
  onFilesChange,
  onUpload,
  onAnalyze,
  loading,
  loadingMessage,
}: UploadDocumentsSectionProps) {
  return (
    <form
      onSubmit={(e) => {
        void onUpload(e);
      }}
      className="space-y-2"
    >
      <label className="text-xs font-semibold text-secondary uppercase tracking-wide">
        Upload Documents
      </label>
      <input
        id="file-input"
        type="file"
        multiple
        onChange={(e) => {
          onFilesChange(e.target.files);
        }}
        className="block w-full text-sm text-secondary file:mr-3 file:rounded-md file:border-0 file:bg-brand-soft file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-brand-strong hover:file:bg-brand-soft"
      />
      {files !== null && files.length > 0 && (
        <p className="text-xs text-dim">
          {files.length} file{files.length === 1 ? "" : "s"} selected
        </p>
      )}
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={loading || files === null || files.length === 0}
          className="inline-flex items-center gap-2 rounded-md bg-brand px-3 py-1.5 text-xs font-semibold text-inverse hover:bg-brand-strong disabled:opacity-50"
        >
          <UploadCloud className="h-3.5 w-3.5" />
          Upload
        </button>
        <button
          type="button"
          onClick={() => {
            void onAnalyze();
          }}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-md border border-border-stronger bg-card px-3 py-1.5 text-xs font-semibold text-secondary hover:bg-surface disabled:opacity-50"
        >
          <Sparkles className="h-3.5 w-3.5" />
          Analyze
        </button>
      </div>
      {loadingMessage !== "" && (
        <p className="text-xs text-dim">{loadingMessage}</p>
      )}
    </form>
  );
}

function DocumentsList({ documents }: DocumentsTabProps) {
  if (documents.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-dim">
        No reference documents found for this architecture.
      </div>
    );
  }

  return (
    <div className="flex-1">
      <Virtuoso
        data={documents}
        className="panel-scroll"
        itemContent={(_index, doc) => (
          <div className="px-4 py-1">
            <div
              key={doc.id}
              className="flex items-start gap-2 p-3 bg-card rounded-lg border border-border hover:bg-surface transition-colors cursor-pointer"
              onClick={() => {
                if (doc.url !== undefined) {
                  window.open(doc.url, "_blank");
                }
              }}
            >
              <File className="h-4 w-4 text-secondary shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-foreground truncate">
                  {doc.title}
                </div>
                <div className="text-xs text-dim mt-1">
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



