import {
  Save,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { featureFlags } from "../../../../../config/featureFlags";
import type {
  AnalysisSummary,
  ReferenceDocument,
  UploadSummary,
} from "../../../../../types/api";
import { useProjectContext } from "../../../context/useProjectContext";
import {
  InitializationSetupPanel,
  UploadSummaryPanel,
  AnalysisSummaryPanel,
  DocumentsList,
} from "./DocumentsTabParts";

interface DocumentsTabProps {
  readonly documents: readonly ReferenceDocument[];
  readonly onOpenDocument?: (documentId: string) => void;
}

function useDocumentsTabDerivedState(documents: readonly ReferenceDocument[]) {
  const ctx = useProjectContext();
  const busy = ctx.isUploadingDocuments || ctx.isAnalyzingDocuments;
  const hasTextInput = ctx.textRequirements.trim() !== "";
  const hasUploadedDocuments = documents.length > 0;
  const hasPendingFiles = ctx.files !== null && ctx.files.length > 0;
  const hasInputs = hasTextInput || hasUploadedDocuments || hasPendingFiles;
  const uploadSummary =
    ctx.inputWorkflow.uploadSummary ?? ctx.projectState?.projectDocumentStats ?? null;
  const analysisSummary =
    ctx.projectState?.analysisSummary ?? ctx.inputWorkflow.analysisSummary;
  const setupCompleted =
    ctx.inputWorkflow.setupCompleted || analysisSummary?.status === "success";
  return { ...ctx, busy, hasInputs, uploadSummary, analysisSummary, setupCompleted };
}

export function DocumentsTab({ documents, onOpenDocument }: DocumentsTabProps) {
  const {
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
    busy,
    hasInputs,
    uploadSummary,
    analysisSummary,
    setupCompleted,
  } = useDocumentsTabDerivedState(documents);
  const setupFlowEnabled = featureFlags.enableUnifiedProjectInitialization;

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

interface UploadResultsSectionProps {
  readonly setupFlowEnabled: boolean;
  readonly uploadSummary: UploadSummary | null;
  readonly analysisSummary: AnalysisSummary | null | undefined;
  readonly loadingMessage: string;
}

function UploadResultsSection({
  setupFlowEnabled,
  uploadSummary,
  analysisSummary,
  loadingMessage,
}: UploadResultsSectionProps) {
  return (
    <>
      {setupFlowEnabled && uploadSummary !== null && (
        <UploadSummaryPanel summary={uploadSummary} />
      )}
      {setupFlowEnabled && analysisSummary !== null && analysisSummary !== undefined && (
        <AnalysisSummaryPanel summary={analysisSummary} />
      )}
      {loadingMessage !== "" && (
        <p className="text-xs text-dim">{loadingMessage}</p>
      )}
    </>
  );
}

interface UploadDocumentsSectionProps {
  readonly files: FileList | null;
  readonly onFilesChange: (files: FileList | null) => void;
  readonly onUpload: (event: React.SyntheticEvent) => Promise<void>;
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
      <UploadResultsSection
        setupFlowEnabled={setupFlowEnabled}
        uploadSummary={uploadSummary}
        analysisSummary={analysisSummary}
        loadingMessage={loadingMessage}
      />
    </form>
  );
}

