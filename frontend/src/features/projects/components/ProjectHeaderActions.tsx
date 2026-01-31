import { Upload, Zap, FileText, Download } from "lucide-react";

interface ProjectHeaderActionsProps {
  onUploadClick?: () => void;
  onGenerateClick?: () => void;
  onAdrClick?: () => void;
  onExportClick?: () => void;
  exportDisabled?: boolean;
}

export function ProjectHeaderActions({
  onUploadClick,
  onGenerateClick,
  onAdrClick,
  onExportClick,
  exportDisabled = false,
}: ProjectHeaderActionsProps) {
  return (
    <>
      {onUploadClick !== undefined && (
        <button
          onClick={onUploadClick}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
          title="Upload documents (⌘U)"
        >
          <Upload className="h-4 w-4" />
          <span className="hidden sm:inline">Upload</span>
        </button>
      )}

      {onGenerateClick !== undefined && (
        <button
          onClick={onGenerateClick}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
          title="Generate analysis (⌘G)"
        >
          <Zap className="h-4 w-4" />
          <span className="hidden sm:inline">Generate Analysis</span>
        </button>
      )}

      {onAdrClick !== undefined && (
        <button
          onClick={onAdrClick}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm"
          title="Create ADR"
        >
          <FileText className="h-4 w-4" />
          <span className="hidden sm:inline">ADR</span>
        </button>
      )}

      {onExportClick !== undefined && (
        <button
          onClick={onExportClick}
          disabled={exportDisabled}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
          title={exportDisabled ? "Export (coming soon)" : "Export"}
        >
          <Download className="h-4 w-4" />
          <span className="hidden sm:inline">Export</span>
        </button>
      )}
    </>
  );
}
