import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  File,
  Save,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { Virtuoso } from "react-virtuoso";
import { featureFlags } from "../../../../../config/featureFlags";
import type {
  AnalysisSummary,
  ReferenceDocument,
  UploadSummary,
} from "../../../../../types/api";
import { useProjectContext } from "../../../context/useProjectContext";

interface DocumentsTabProps {
  readonly documents: readonly ReferenceDocument[];
  readonly onOpenDocument?: (documentId: string) => void;
}

export function DocumentsTab({ documents, onOpenDocument }: DocumentsTabProps) {
  const {
    projectState,
    selectedProject,
    textRequirements,
    setTextRequirements,
    files,
    setFiles,
    handleSaveTextRequirements,
    handleUploadDocuments,
    handleAnalyzeDocuments,
    isUploadingDocuments,
    isAnalyzingDocuments,
    inputWorkflow,
  } = useProjectContext();
  const busy = isUploadingDocuments || isAnalyzingDocuments;
  const setupFlowEnabled = featureFlags.enableUnifiedProjectInitialization;

  const hasTextInput = textRequirements.trim() !== "";
  const hasUploadedDocuments = documents.length > 0;
  const hasPendingFiles = files !== null && files.length > 0;
  const hasInputs = hasTextInput || hasUploadedDocuments || hasPendingFiles;
  const uploadSummary =
    inputWorkflow.uploadSummary ?? projectState?.projectDocumentStats ?? null;
  const analysisSummary =
    projectState?.analysisSummary ?? inputWorkflow.analysisSummary;
  const setupCompleted =
    inputWorkflow.setupCompleted || analysisSummary?.status === "success";

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 space-y-4 border-b border-border bg-card">
        {setupFlowEnabled && (
          <InitializationSetupPanel
            hasInputs={hasInputs}
            uploadSummary={uploadSummary}
            analysisSummary={analysisSummary}
            setupCompleted={setupCompleted}
            isAnalyzing={isAnalyzingDocuments}
          />
        )}
        <TextRequirementsSection
          textRequirements={textRequirements}
          onChange={setTextRequirements}
          onSave={handleSaveTextRequirements}
          loading={busy}
          hasProject={selectedProject !== null}
        />
        <UploadDocumentsSection
          files={files}
          onFilesChange={setFiles}
          onUpload={handleUploadDocuments}
          onAnalyze={handleAnalyzeDocuments}
          loading={busy}
          isUploading={isUploadingDocuments}
          isAnalyzing={isAnalyzingDocuments}
          loadingMessage={inputWorkflow.message}
          uploadSummary={uploadSummary}
          analysisSummary={analysisSummary}
          setupFlowEnabled={setupFlowEnabled}
        />
      </div>

      <DocumentsList documents={documents} onOpenDocument={onOpenDocument} />
    </div>
  );
}

interface InitializationSetupPanelProps {
  readonly hasInputs: boolean;
  readonly uploadSummary: UploadSummary | null;
  readonly analysisSummary: AnalysisSummary | null | undefined;
  readonly setupCompleted: boolean;
  readonly isAnalyzing: boolean;
}

function InitializationSetupPanel({
  hasInputs,
  uploadSummary,
  analysisSummary,
  setupCompleted,
  isAnalyzing,
}: InitializationSetupPanelProps) {
  const uploadStepComplete =
    uploadSummary !== null && uploadSummary.attemptedDocuments > 0;
  const analysisStepComplete = analysisSummary?.status === "success";

  return (
    <div className="rounded-lg border border-border bg-surface p-3 space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-secondary uppercase tracking-wide">
            Initialization Setup
          </p>
          <p className="text-xs text-dim">
            Chat stays available while you complete setup.
          </p>
        </div>
        <span
          className={
            setupCompleted
              ? "rounded-full border border-success-line bg-success-soft px-2 py-1 text-xs text-success"
              : "rounded-full border border-border bg-card px-2 py-1 text-xs text-secondary"
          }
        >
          {setupCompleted ? "Ready" : "In progress"}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2">
        <SetupStepRow
          title="Step A - Add Inputs"
          description="Add requirement text or select files for upload."
          complete={hasInputs}
          inProgress={false}
        />
        <SetupStepRow
          title="Step B - Upload Results"
          description="Confirm parsed vs failed files after upload."
          complete={uploadStepComplete}
          inProgress={false}
        />
        <SetupStepRow
          title="Step C - Analyze"
          description="Run analysis to build baseline artifacts."
          complete={analysisStepComplete}
          inProgress={isAnalyzing}
        />
        <SetupStepRow
          title="Step D - Setup Complete"
          description="Initialization is complete after first successful analysis."
          complete={setupCompleted}
          inProgress={false}
        />
      </div>
    </div>
  );
}

interface SetupStepRowProps {
  readonly title: string;
  readonly description: string;
  readonly complete: boolean;
  readonly inProgress: boolean;
}

function SetupStepRow({
  title,
  description,
  complete,
  inProgress,
}: SetupStepRowProps) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border bg-card px-2 py-2">
      {complete ? (
        <CheckCircle2 className="h-4 w-4 text-success mt-0.5 shrink-0" />
      ) : inProgress ? (
        <Circle className="h-4 w-4 text-brand mt-0.5 shrink-0 animate-pulse" />
      ) : (
        <Circle className="h-4 w-4 text-dim mt-0.5 shrink-0" />
      )}
      <div>
        <p className="text-xs font-semibold text-foreground">{title}</p>
        <p className="text-xs text-dim">{description}</p>
      </div>
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
  readonly isUploading: boolean;
  readonly isAnalyzing: boolean;
  readonly loadingMessage: string;
  readonly uploadSummary: UploadSummary | null;
  readonly analysisSummary: AnalysisSummary | null | undefined;
  readonly setupFlowEnabled: boolean;
}

function UploadDocumentsSection({
  files,
  onFilesChange,
  onUpload,
  onAnalyze,
  loading,
  isUploading,
  isAnalyzing,
  loadingMessage,
  uploadSummary,
  analysisSummary,
  setupFlowEnabled,
}: UploadDocumentsSectionProps) {
  return (
    <form
      onSubmit={(e) => {
        void onUpload(e);
      }}
      data-upload-area
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
          {isUploading ? "Uploading..." : "Upload"}
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
          {isAnalyzing ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {setupFlowEnabled && uploadSummary !== null && (
        <UploadSummaryPanel summary={uploadSummary} />
      )}

      {setupFlowEnabled && analysisSummary !== null && analysisSummary !== undefined && (
        <AnalysisSummaryPanel summary={analysisSummary} />
      )}

      {loadingMessage !== "" && (
        <p className="text-xs text-dim">{loadingMessage}</p>
      )}
    </form>
  );
}

function UploadSummaryPanel({ summary }: { readonly summary: UploadSummary }) {
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2 space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-foreground">Upload Summary</span>
        <span className="text-secondary">
          {summary.parsedDocuments}/{summary.attemptedDocuments} parsed
        </span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="rounded border border-border bg-card px-2 py-1 text-secondary">
          Attempted: {summary.attemptedDocuments}
        </div>
        <div className="rounded border border-success-line bg-success-soft px-2 py-1 text-success">
          Parsed: {summary.parsedDocuments}
        </div>
        <div className="rounded border border-danger-line bg-danger-soft px-2 py-1 text-danger-strong">
          Failed: {summary.failedDocuments}
        </div>
      </div>
      {summary.failures.length > 0 && (
        <div className="space-y-1">
          {summary.failures.map((failure) => (
            <div
              key={`${failure.documentId ?? failure.fileName}-${failure.reason}`}
              className="flex items-start gap-1.5 text-xs text-danger-strong"
            >
              <AlertTriangle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span>
                {failure.fileName}: {failure.reason}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AnalysisSummaryPanel({ summary }: { readonly summary: AnalysisSummary }) {
  return (
    <div className="rounded-md border border-border bg-surface px-3 py-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-foreground">Analysis Summary</span>
        <span
          className={
            summary.status === "success"
              ? "text-success"
              : "text-danger-strong"
          }
        >
          {summary.status}
        </span>
      </div>
      <p className="text-xs text-secondary mt-1">
        Analyzed: {summary.analyzedDocuments} | Skipped: {summary.skippedDocuments}
      </p>
      <p className="text-xs text-dim mt-1">
        Completed: {new Date(summary.completedAt).toLocaleString()}
      </p>
    </div>
  );
}

function DocumentsList({
  documents,
  onOpenDocument,
}: {
  readonly documents: readonly ReferenceDocument[];
  readonly onOpenDocument?: (documentId: string) => void;
}) {
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
                if (onOpenDocument !== undefined) {
                  onOpenDocument(doc.id);
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
                {featureFlags.enableDocumentStatusTrace && (
                  <div className="text-xs text-secondary mt-1">
                    Parse: {doc.parseStatus ?? "unknown"} | Analysis:{" "}
                    {doc.analysisStatus ?? "unknown"}
                  </div>
                )}
                {featureFlags.enableDocumentStatusTrace &&
                  doc.parseError !== undefined &&
                  doc.parseError !== null &&
                  doc.parseError !== "" && (
                    <div className="text-xs text-danger-strong mt-1">
                      {doc.parseError}
                    </div>
                  )}
              </div>
            </div>
          </div>
        )}
        style={{ height: "100%" }}
      />
    </div>
  );
}
